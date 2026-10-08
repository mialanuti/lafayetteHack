import csv
import json
import os
import re
import threading
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field, ValidationError, field_validator


ROOT = Path(__file__).resolve().parent
INBOX_PATH = ROOT / "inbox.json"
BUSINESS_PATH = ROOT / "business.md"
GAME_DAYS_PATH = ROOT / "game_days.csv"
INDEX_PATH = ROOT / "index.html"
INBOX_LOCK = threading.Lock()

load_dotenv(ROOT / ".env")


class Category(str, Enum):
    party_group = "party_group"
    dj_submission = "dj_submission"
    charity_org_event = "charity_org_event"
    other = "other"


class Decision(str, Enum):
    draft_for_owner = "draft_for_owner"
    ask_customer = "ask_customer"
    escalate_to_owner = "escalate_to_owner"
    ignore = "ignore"


class TriageRequest(BaseModel):
    message: str = Field(min_length=1)
    received_date: date
    received_at: datetime | None = None

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value.strip()


class InquiryDetails(BaseModel):
    date: str | None = None
    headcount: int | str | None = None
    ask: str | None = None


class TriageResult(BaseModel):
    category: Category
    details: InquiryDetails
    decision: Decision
    reason: str = Field(min_length=1)
    draft_reply: str

    @field_validator("reason")
    @classmethod
    def reason_must_be_one_line(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("reason must be one line")
        return value.strip()


class TriageRecord(TriageResult):
    id: str
    message: str
    received_date: date
    received_at: datetime | None = None
    high_demand_date: bool
    created_at: datetime


app = FastAPI(title="Event Desk")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


SYSTEM_PROMPT = """You triage inbound inquiries for a bar.

Business facts:
- Use only business.md as the source of business-specific facts. The business_context in the user message is its contents. Do not use general knowledge, prior knowledge, or assumptions.
- Anything not explicitly stated in business.md about prices, minimums, deposits, DJ pay, availability, capacity, fees, cover waivers, or age policy is UNKNOWN. Never answer or infer an unknown fact. Use decision ask_customer or escalate_to_owner; ask_customer is only for clarification the customer can provide, otherwise escalate_to_owner.
- Never promise a date, confirm a booking, or hold a table.

Escalation rules:
- If high_demand_date is true, decision must be escalate_to_owner. The one-line reason must say that the high-demand date requires owner review.
- If the message mentions anyone under 21 or contains a complaint, decision must be escalate_to_owner.
- Draft replies must not quote prices or confirm availability. Every draft_reply must begin with "DRAFT FOR OWNER APPROVAL:".

Return only valid JSON with exactly these fields: category (party_group, dj_submission, charity_org_event, other), details (object with date, headcount, ask; use null when unknown), decision (draft_for_owner, ask_customer, escalate_to_owner, ignore), reason (one line), and draft_reply (string)."""


DATE_PATTERNS = (
    re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b"),
    re.compile(r"(?<![\d/-])\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?(?![\d/-])"),
    re.compile(
        r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{1,2}(?:st|nd|rd|th)?"
        r"(?:,?\s+\d{4})?\b",
        re.IGNORECASE,
    ),
)
WEEKDAYS = {
    name.lower(): index
    for index, name in enumerate(
        ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    )
}
RELATIVE_WEEKDAY_PATTERN = re.compile(
    r"\b(?P<relative>this|next)\s+"
    r"(?P<weekday>Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
    re.IGNORECASE,
)
DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%m/%d/%y",
    "%m-%d-%y",
    "%m/%d",
    "%m-%d",
    "%B %d, %Y",
    "%B %d %Y",
    "%b %d, %Y",
    "%b %d %Y",
    "%B %d",
    "%b %d",
)


def parse_mentioned_date(value: str, default_year: int) -> date | None:
    cleaned = re.sub(r"(?<=\d)(?:st|nd|rd|th)\b", "", value, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned.strip())
    for date_format in DATE_FORMATS:
        try:
            parsed = datetime.strptime(cleaned, date_format).date()
            if "%Y" not in date_format and "%y" not in date_format:
                parsed = parsed.replace(year=default_year)
            return parsed
        except ValueError:
            continue
    return None


def dates_mentioned(message: str, received_date: date) -> set[date]:
    found: set[date] = set()
    for match in RELATIVE_WEEKDAY_PATTERN.finditer(message):
        weekday = WEEKDAYS[match.group("weekday").lower()]
        days_ahead = (weekday - received_date.weekday()) % 7
        if match.group("relative").lower() == "next":
            days_ahead += 7
        found.add(received_date + timedelta(days=days_ahead))

    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(message):
            parsed = parse_mentioned_date(match.group(0), received_date.year)
            if parsed is not None:
                found.add(parsed)
    return found


def game_dates() -> set[date]:
    if not GAME_DAYS_PATH.exists():
        return set()
    with GAME_DAYS_PATH.open("r", encoding="utf-8-sig", newline="") as game_file:
        reader = csv.DictReader(game_file)
        date_column = next(
            (name for name in (reader.fieldnames or []) if name.strip().lower() == "date"),
            None,
        )
        if date_column is None:
            return set()
        result = set()
        for row in reader:
            raw_date = (row.get(date_column) or "").strip()
            parsed = parse_mentioned_date(raw_date, date.today().year)
            if parsed is not None:
                result.add(parsed)
        return result


def load_inbox() -> list[dict]:
    if not INBOX_PATH.exists():
        return []
    with INBOX_PATH.open("r", encoding="utf-8") as inbox_file:
        data = json.load(inbox_file)
    if not isinstance(data, list):
        raise ValueError("inbox.json must contain a JSON list")
    return data


def save_record(record: TriageRecord) -> None:
    with INBOX_LOCK:
        records = load_inbox()
        records.insert(0, json.loads(record.model_dump_json()))
        temporary_path = INBOX_PATH.with_suffix(".json.tmp")
        temporary_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        temporary_path.replace(INBOX_PATH)


def invalid_result() -> TriageResult:
    return TriageResult(
        category=Category.other,
        details=InquiryDetails(),
        decision=Decision.escalate_to_owner,
        reason="model output invalid",
        draft_reply="",
    )


def configured_model() -> tuple[OpenAI, str, str]:
    provider = os.getenv("AI_PROVIDER", "").strip().lower()
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not provider:
        provider = "gemini" if gemini_key and not openai_key else "openai"

    if provider == "gemini":
        if not gemini_key:
            raise HTTPException(status_code=503, detail="GEMINI_API_KEY is missing from .env")
        if not gemini_key.isascii():
            raise HTTPException(
                status_code=503,
                detail="GEMINI_API_KEY must be ASCII; copy it again from Google AI Studio.",
            )
        return (
            OpenAI(api_key=gemini_key, base_url=GEMINI_BASE_URL),
            os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            provider,
        )

    if provider == "openai":
        if not openai_key:
            raise HTTPException(status_code=503, detail="OPENAI_API_KEY is missing from .env")
        return OpenAI(api_key=openai_key), os.getenv("OPENAI_MODEL", "gpt-4o-mini"), provider

    raise HTTPException(status_code=503, detail="AI_PROVIDER must be 'gemini' or 'openai'")


def call_model(message: str, received_date: date, high_demand_date: bool) -> TriageResult:
    business_context = BUSINESS_PATH.read_text(encoding="utf-8")
    client, model, provider = configured_model()
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "message": message,
                    "received_date": received_date.isoformat(),
                    "business_context": business_context,
                    "high_demand_date": high_demand_date,
                }
            ),
        },
    ]
    try:
        if provider == "gemini":
            response = client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=TriageResult,
            )
        else:
            response = client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                messages=messages,
            )
    except OpenAIError as error:
        raise HTTPException(
            status_code=502,
            detail=f"{provider.title()} model request failed; check its API key and model name.",
        ) from error
    try:
        model_message = response.choices[0].message
        parsed = getattr(model_message, "parsed", None)
        if parsed is not None:
            return TriageResult.model_validate(parsed)
        content = model_message.content
        return TriageResult.model_validate_json(content or "")
    except (ValidationError, ValueError, TypeError, IndexError, AttributeError):
        return invalid_result()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(INDEX_PATH)


@app.get("/inbox")
def inbox() -> list[dict]:
    try:
        return load_inbox()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=500, detail="Could not read inbox.json") from error


@app.get("/game-days", response_model=list[str])
def list_game_days() -> list[str]:
    return sorted(game_date.isoformat() for game_date in game_dates())


@app.post("/triage", response_model=TriageRecord)
def triage(request: TriageRequest) -> TriageRecord:
    try:
        high_demand_date = bool(
            dates_mentioned(request.message, request.received_date) & game_dates()
        )
        result = call_model(request.message, request.received_date, high_demand_date)
        record = TriageRecord(
            **result.model_dump(),
            id=str(uuid4()),
            message=request.message,
            received_date=request.received_date,
            received_at=request.received_at,
            high_demand_date=high_demand_date,
            created_at=datetime.now(timezone.utc),
        )
        save_record(record)
        return record
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=503, detail="Triage service is not configured") from error