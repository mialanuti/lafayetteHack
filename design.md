# Event Desk: Design Spec (Might As Well theme)

Use this file as the build brief. It describes an internal staff tool for Might As Well Bar & Grill, Chapel Hill, that borrows the feel of the bar's public website (chapelhill.mightaswellbarandgrill.com) but is more orderly and professional.

## Source labels

- **Observed:** read from the live website's text and structure on Oct 8, 2026.
- **Proposed:** a design choice made here. Colors and fonts are Proposed because the site's CSS was not readable. Before the pitch, open the site, sample its real colors and fonts with browser dev tools, and swap them into the tokens below.
- **From code:** taken from `main.py` or the existing `index.html`.

## What this is

An internal tool used only by employees. It triages the bar's inbound event inquiries (party and group bookings, DJ submissions, charity and organization events) and shows what each one needs. It is not public, has no marketing content, and does not sell anything.

It is an unofficial prototype. Do not use the bar's logo or photos, and do not imply the business endorses it. Put "Unofficial prototype" in the footer.

## The public site's character (Observed)

- Brand line: "sports.food.fun". Section headings in all caps: "DELICIOUS FOOD", "ENORMOUS BEER SELECTION", "HUGE BURGERS".
- Hero slides are short and punchy: "Burgers. Beer. Pizza. Wings", "great selection of beers", "our daily specials", "we host, you party".
- Tone: loud, friendly, college sports bar. Photo-heavy, with calls to action such as Book now, Our menu, Order.
- Top nav: Merchandise, Menu (Food, Drinks, Specials), Catering, Parties, Gift Cards, Jobs, Order, Reserve, Events.
- Blocks, in order: slideshow, intro, three feature photos, Specials, Private Parties, Order online, gallery, Reviews, Location, Hours, Contact.
- Hours block: Mon-Thu, Fri, Sat, Sun, each with times. Contact: phone and email.

## What carries over, and what changes

| Carry over | Change for staff use |
|---|---|
| All-caps, short section labels | No photos, no slideshow, no popups |
| Bold, game-day energy in headings | Calm, dense layout; the work comes first |
| Sports-bar palette: dark base, warm accent | Lighter working surface so long text is readable |
| Plain-spoken copy ("we host, you party") | Operational copy: what to do, and why |
| Hours and contact block | Moved to a small "Bar info" panel |
| Parties, Catering, Events as nav | Become filters on the inbox |

## Palette (Proposed)

A dark charcoal header and footer (the bar at night) around a light working surface, with one warm accent and one team-blue accent.

| Token | Value | Use |
|---|---|---|
| `--night` | `#14181c` | header, footer, nav |
| `--night-2` | `#1f252b` | header hover, dividers on dark |
| `--paper` | `#f5f4f0` | page background |
| `--surface` | `#ffffff` | panels |
| `--ink` | `#1c2024` | text |
| `--muted` | `#6b7178` | secondary text |
| `--line` | `#dcdad3` | borders |
| `--gold` | `#e0a422` | brand accent, active nav, key labels |
| `--carolina` | `#4b9cd3` | links, focus ring, selected row bar |
| `--ok` | `#2f7a4f` / soft `#e2f1e8` | Draft for owner |
| `--warn` | `#9a6a12` / soft `#f7edd3` | Ask customer |
| `--stop` | `#b3372a` / soft `#f7e1dd` | Escalate to owner |
| `--idle` | `#5f656b` / soft `#e8e8e5` | Ignore |

Decision colors keep the meaning already in the app (green, amber, red, gray). Each badge also carries its text label, so color is never the only signal.

## Type (Proposed)

- Display (header wordmark, page title, section labels): a heavy condensed sans, all caps, 0.04em tracking. Use "Oswald" (Google Fonts), weights 500 and 600, with `Impact, "Arial Narrow", sans-serif` as fallback.
- Body and UI: the system font stack (`system-ui, -apple-system, "Segoe UI", sans-serif`). Do not use Inter; it is the default look of generated interfaces.
- Scale: page title 32px, panel title 13px caps, body 14px, secondary 12px, labels 11px caps with 0.08em tracking.

## Layout

Desktop (max width 1280px, centered):

1. **Top bar** (dark): wordmark "EVENT DESK" in gold, small line "Might As Well · Chapel Hill · Staff only", nav links, and a "Today" chip with today's date and a "Game day" tag when `game_days.csv` matches.
2. **Count line:** one line of plain text, not cards, built from the live counts, in this format: "N messages · N draft for owner · N ask customer · N escalate · N ignore". Each count is a text link in its decision color and filters the inbox. No big-number stat tiles.
3. **Composer:** "New inquiry" with a message box, a "Received" date, and a "Triage inquiry" button. Gold left border.
4. **Workspace:** two panes.
   - Left: inbox list with filter tabs (All, Parties, DJs, Charity, Other). Each row shows category, received date, snippet, decision badge, and a "Game day" tag.
   - Right: the selected inquiry (see Detail).
5. **Footer** (dark): "Unofficial prototype · internal use only", plus a "Bar info" link that opens a panel with hours and contact.

Mobile: nav collapses to a menu button; count line wraps; workspace stacks, list capped at about 270px tall.

## Detail pane

In order of weight:

1. Decision badge and category (large)
2. "Why this decision": the one-line reason
3. Reply draft, with **Copy draft** and **Mark handled** buttons
4. Pulled details: Date, Headcount, Ask, and a "HIGH-DEMAND DATE" tag when flagged
5. Original message

Use an explicit "Needs a person" banner on Escalate to owner: red left border, with the reason in it. For the invalid-model-output case (reason "model output invalid"), show a distinct gray banner: "The agent could not read this one. Handle it by hand."

Never display a price, date availability, capacity, deposit, minimum, or DJ pay as fact. Those are in the UNKNOWN list in `business.md` and always go to a person.

## Bar info panel (Observed)

- Address: 206 West Franklin Street, Chapel Hill, NC 27516
- Phone: (984) 234-3333
- Hours: Mon-Thu 4:00 PM - 2:00 AM, Fri 12:00 PM - 2:00 AM, Sat 10:00 AM - 2:00 AM, Sun 12:00 PM - 2:00 AM

Note: the owner's email shown on the public site is a business address. Do not copy it into the repo unless the owner asks.

## Copy

Keep the existing app copy where it works, and apply the bar's all-caps label style to section labels.

- Wordmark: EVENT DESK
- Drop the tagline "Inbound, in good order." and the page title "The doorbell." from the earlier prototype. They read as clever filler. The page title is the plain working label: "INBOX".
- Section labels: INBOX, NEW INQUIRY, WHY THIS DECISION, REPLY DRAFT, PULLED DETAILS, ORIGINAL MESSAGE
- Decision labels: Draft for owner, Ask customer, Escalate to owner, Ignore (From code)
- Category labels: Party / group, DJ submission, Charity event, Other (From code)
- Empty list: "Nothing in the inbox yet. New inquiries will land here after triage."
- Empty detail: "Select an inquiry to see its triage and reply draft."
- Buttons: "Triage inquiry", "Copy draft", "Mark handled"

## Components

- **Badges:** 10px bold, 3px radius, soft background with matching text.
- **Rows:** active row has a 3px carolina bar on the left and a very light blue tint.
- **Panels:** white, 1px `--line` border, 2px radius, no shadow. Separate areas with rules (lines), not floating cards. Never nest a card inside a card.
- **Primary button:** gold background, `--night` text, bold, 4px radius. Secondary: white with a 1px border.
- **Focus:** 2px carolina ring on every interactive element.
- **Loading:** the button text becomes "Working…" and pulses.
- **Errors:** inline in a notice line under the composer, in `--stop`. No dialogs.

## Behavior and data (From code)

- `GET /inbox` returns records, newest first. `POST /triage` takes `message` and `received_date`.
- Record fields: `id`, `message`, `received_date`, `category`, `details` (`date`, `headcount`, `ask`), `decision`, `reason`, `draft_reply`, `high_demand_date`, `created_at`.
- Escape all model text before rendering.
- "Mark handled" and the summary filters can live in browser memory for the demo (no storage API in the page). If they must persist, add a `handled` field to `inbox.json` through a new endpoint.

## Accessibility and polish

- Text contrast at least 4.5:1 on every surface; check gold on charcoal, and never put gold text on white.
- All controls reachable by keyboard; badges are text, not images.
- No autoplay, no popups, no carousel.
- Respect `prefers-reduced-motion`.

## Out of scope

Menu, ordering, reservations, gift cards, merchandise, reviews, social links, newsletter. These exist on the public site and have no job in a staff tool.

## Must not look generated

This tool is meant to look like something a bar's staff or a small agency built for them. Treat every item as a rule.

**Layout and shape**
- No row of four equal stat tiles with big numbers. No grid of identical rounded cards. The inbox is a dense table-like list; the detail is a document, read top to bottom.
- Corners are square or 2px. No pill buttons, no 12px to 24px rounding, no drop shadows on panels, no glassmorphism, no blurred blobs, no gradients (gold is a flat fill).
- Asymmetric and left-aligned. No centered hero, no centered section titles, no "feature" trio with icons.
- Unequal column widths and real borders. Spacing follows a 4px grid; do not pad everything the same 24px.

**Color and type**
- One accent does the work (gold). Carolina blue appears only on links, focus, and the selected row. No purple, no blue-to-purple gradients, no neon glows.
- Headings are plain: one display face for the wordmark and section labels, nothing decorative. No gradient text, no emoji, no icon next to every heading.
- Numbers and dates use tabular figures so columns line up.

**Copy**
- Write it the way a manager would say it: "Needs the owner," "Ask for headcount," "Game day." No "seamless," "effortless," "powerful," "leverage," "streamline," "unlock," or "supercharge."
- No exclamation points, no emoji, no "Welcome back!" greeting, no marketing subtitle under the title.
- No placeholder text such as "Lorem ipsum," "John Doe," "Acme," or round fake numbers. Every record shown comes from `inbox.json`; sample data is real-looking inquiries we wrote, labeled as test data.
- Every empty state says what is missing and what to do, in one sentence, with no illustration.
- Error messages say what failed and what to check ("Model request failed; check OPENAI_API_KEY and OPENAI_MODEL."), not "Oops, something went wrong."

**Detail and texture**
- Add the small working details staff expect: received time next to each message, the original message shown exactly as written (not prettified), keyboard shortcuts for next and previous, and a visible count of unhandled items in the tab title.
- Use real hours, address, and phone (Observed section) rather than invented ones.
- Motion is limited to a 100 to 150ms color change on hover and the loading pulse. No entrance animations, no staggered fades, no parallax.

**Final check before shipping**
Squint at the page. If it looks like a template dashboard (stat tiles, rounded white cards on gray, a gradient hero, an icon per row), remove things until it looks like a plain work screen with the bar's colors on it.
