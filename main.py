import csv
import json
import os
import re
import threading
from datetime import date, datetime, timezone
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
    high_demand_date: bool
    created_at: datetime


app = FastAPI(title="Event Desk")


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


def dates_mentioned(message: str, default_year: int) -> set[date]:
    found: set[date] = set()
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(message):
            parsed = parse_mentioned_date(match.group(0), default_year)
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


def call_model(message: str, received_date: date, high_demand_date: bool) -> TriageResult:
    business_context = BUSINESS_PATH.read_text(encoding="utf-8")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is missing from .env")
    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Triage inbound inquiries for a bar. Return only JSON with exactly these "
                        "fields: category (party_group, dj_submission, charity_org_event, other), "
                        "details (object with date, headcount, ask; use null when unknown), "
                        "decision (draft_for_owner, ask_customer, escalate_to_owner, ignore), "
                        "reason (one line), and draft_reply (string). Do not claim a booking is "
                        "confirmed. Use the business context and the supplied high-demand flag."
                    ),
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
            ],
        )
    except OpenAIError as error:
        raise HTTPException(
            status_code=502,
            detail="Model request failed; check OPENAI_API_KEY and OPENAI_MODEL.",
        ) from error
    try:
        content = response.choices[0].message.content
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


@app.post("/triage", response_model=TriageRecord)
def triage(request: TriageRequest) -> TriageRecord:
    try:
        high_demand_date = bool(
            dates_mentioned(request.message, request.received_date.year) & game_dates()
        )
        result = call_model(request.message, request.received_date, high_demand_date)
        record = TriageRecord(
            **result.model_dump(),
            id=str(uuid4()),
            message=request.message,
            received_date=request.received_date,
            high_demand_date=high_demand_date,
            created_at=datetime.now(timezone.utc),
        )
        save_record(record)
        return record
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=503, detail="Triage service is not configured") from error