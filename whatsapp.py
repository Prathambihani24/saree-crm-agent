import logging
from typing import Any, Dict, List, Tuple

import requests

import config

logger = logging.getLogger(__name__)


def verify_webhook(mode: str, token: str, challenge: str) -> Tuple[str, int]:
    if mode == "subscribe" and token == config.META_VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


def send_message(to: str, body: str) -> Dict[str, Any]:
    if not config.whatsapp_configured():
        raise ValueError("Meta WhatsApp credentials are not configured")

    url = config.META_MESSAGES_URL.format(
        phone_number_id=config.META_PHONE_NUMBER_ID
    )
    headers = {
        "Authorization": f"Bearer {config.META_WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def parse_incoming_messages(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []

    if payload.get("object") != "whatsapp_business_account":
        return messages

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = {
                contact.get("wa_id", ""): contact.get("profile", {}).get("name", "")
                for contact in value.get("contacts", [])
            }

            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue

                text_body = message.get("text", {}).get("body", "")
                sender = message.get("from", "")
                messages.append(
                    {
                        "from": sender,
                        "body": text_body,
                        "profile_name": contacts.get(sender, ""),
                        "message_id": message.get("id", ""),
                    }
                )

    return messages
