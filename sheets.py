import logging
from datetime import datetime, timedelta
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

import config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

LEADS_SHEET = "Leads"
ORDERS_SHEET = "Orders"
FOLLOWUPS_SHEET = "Follow-ups"

LEADS_HEADERS = [
    "Timestamp",
    "Name",
    "Phone",
    "Interest",
    "Budget",
    "Intent",
    "Status",
]
ORDERS_HEADERS = [
    "Timestamp",
    "Name",
    "Phone",
    "Item",
    "Amount",
    "COD",
    "Address",
    "Status",
]
FOLLOWUPS_HEADERS = [
    "Timestamp",
    "Name",
    "Phone",
    "Last_Contact",
    "Follow_up_date",
    "Notes",
]

_spreadsheet_cache = None


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_client() -> gspread.Client:
    creds = Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_PATH,
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


def get_spreadsheet():
    global _spreadsheet_cache
    if _spreadsheet_cache is None:
        client = get_client()
        _spreadsheet_cache = client.open_by_key(config.GOOGLE_SHEET_ID)
    return _spreadsheet_cache


def _ensure_headers(worksheet, headers: list) -> None:
    existing = worksheet.row_values(1)
    if existing != headers:
        worksheet.update([headers], range_name="A1")


def _get_worksheet(name: str, headers: list):
    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=name, rows=1000, cols=len(headers))
    _ensure_headers(worksheet, headers)
    return worksheet


def append_lead(
    name: str,
    phone: str,
    interest: str,
    budget: str,
    intent: str,
    status: str = "new",
) -> None:
    sheet = _get_worksheet(LEADS_SHEET, LEADS_HEADERS)
    sheet.append_row(
        [_now(), name, phone, interest, budget, intent, status],
        value_input_option="USER_ENTERED",
    )


def append_order(
    name: str,
    phone: str,
    item: str,
    amount: str,
    cod: str,
    address: str,
    status: str = "pending",
) -> None:
    sheet = _get_worksheet(ORDERS_SHEET, ORDERS_HEADERS)
    sheet.append_row(
        [_now(), name, phone, item, amount, cod, address, status],
        value_input_option="USER_ENTERED",
    )


def append_followup(
    name: str,
    phone: str,
    last_contact: str,
    follow_up_date: str,
    notes: str,
) -> None:
    sheet = _get_worksheet(FOLLOWUPS_SHEET, FOLLOWUPS_HEADERS)
    sheet.append_row(
        [_now(), name, phone, last_contact, follow_up_date, notes],
        value_input_option="USER_ENTERED",
    )


def _follow_up_date(days: int = 2) -> str:
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


def record_agent_result(
    agent_response: dict,
    sender_phone: str,
    sender_name: str,
) -> dict:
    intent = agent_response.get("intent", "general")
    lead_data = agent_response.get("lead_data", {})

    name = lead_data.get("name") or sender_name or "Unknown"
    phone = lead_data.get("phone") or sender_phone
    interest = lead_data.get("interest", "")
    budget = lead_data.get("budget", "")

    actions = {"lead_saved": False, "order_saved": False, "followup_saved": False}

    if intent in {
        "price_inquiry",
        "availability",
        "order_placement",
        "cod_question",
        "shipping_question",
    }:
        append_lead(
            name=name,
            phone=phone,
            interest=interest,
            budget=budget,
            intent=intent,
            status="interested" if intent != "order_placement" else "hot",
        )
        actions["lead_saved"] = True

    if intent == "order_placement":
        append_order(
            name=name,
            phone=phone,
            item=interest or "Not specified",
            amount=budget or "Not specified",
            cod="Pending confirmation",
            address="Pending",
            status="pending",
        )
        actions["order_saved"] = True

    if intent in {"price_inquiry", "availability", "cod_question", "shipping_question"}:
        append_followup(
            name=name,
            phone=phone,
            last_contact=_now(),
            follow_up_date=_follow_up_date(),
            notes=f"Intent: {intent}. Interest: {interest or 'N/A'}",
        )
        actions["followup_saved"] = True

    return actions


def safe_record_agent_result(
    agent_response: dict,
    sender_phone: str,
    sender_name: str,
) -> Optional[dict]:
    if not config.sheets_configured():
        return None

    try:
        return record_agent_result(agent_response, sender_phone, sender_name)
    except Exception:
        logger.exception("Failed to write to Google Sheets")
        return {"error": "Failed to write to Google Sheets"}
