import json
import logging
import re
from typing import Any, Dict, List, Optional

from groq import Groq

import config

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a friendly WhatsApp sales assistant for a D2C saree and kurti business in India.
Reply in Hinglish — warm, helpful, concise, like a real shop owner chatting on WhatsApp.

Your job:
- Answer questions about sarees, kurtis, fabrics, colors, sizes, pricing, COD, and delivery
- Help customers choose products and nudge them toward placing an order
- Extract lead details whenever the customer shares or implies them

Classify every customer message into exactly one intent:
- price_inquiry: asking price, rate, kitna, cost, offer, discount
- availability: asking if product is available, in stock, color/size available
- order_placement: wants to buy, order, book, confirm purchase
- cod_question: asking about Cash on Delivery, COD, payment on delivery
- shipping_question: asking about delivery, shipping, dispatch, pincode, courier, kitne din
- general: greetings, thanks, or anything that does not fit above

Respond ONLY with valid JSON. No markdown, no code fences, no extra text.
Use this exact schema:
{
  "reply": "your Hinglish reply to the customer",
  "intent": "price_inquiry|availability|order_placement|cod_question|shipping_question|general",
  "lead_data": {
    "name": "customer name if known else empty string",
    "phone": "phone if mentioned else empty string",
    "interest": "product or category they want else empty string",
    "budget": "budget or price range if mentioned else empty string"
  }
}"""


def get_client() -> Groq:
    if not config.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured")
    return Groq(api_key=config.GROQ_API_KEY)


def _empty_lead_data() -> Dict[str, str]:
    return {"name": "", "phone": "", "interest": "", "budget": ""}


def _default_response(message: str) -> Dict[str, Any]:
    return {
        "reply": (
            "Namaste! 🙏 Hum saree aur kurti bechte hain. "
            "Aapko kis type ki saree ya kurti chahiye? Price ya delivery ke baare mein bhi pooch sakte ho."
        ),
        "intent": "general",
        "lead_data": _empty_lead_data(),
    }


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


def _normalize_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    intent = str(raw.get("intent", "general")).strip().lower()
    if intent not in config.VALID_INTENTS:
        intent = "general"

    lead_data = raw.get("lead_data") or {}
    if not isinstance(lead_data, dict):
        lead_data = {}

    normalized_lead = _empty_lead_data()
    for key in normalized_lead:
        value = lead_data.get(key, "")
        normalized_lead[key] = str(value).strip() if value is not None else ""

    reply = str(raw.get("reply", "")).strip()
    if not reply:
        reply = _default_response("")["reply"]

    return {
        "reply": reply,
        "intent": intent,
        "lead_data": normalized_lead,
    }


def _merge_customer_context(
    response: Dict[str, Any],
    customer_name: str,
    customer_phone: str,
) -> Dict[str, Any]:
    lead_data = response["lead_data"]
    if customer_name and not lead_data["name"]:
        lead_data["name"] = customer_name.strip()
    if customer_phone and not lead_data["phone"]:
        lead_data["phone"] = customer_phone.strip()
    return response


def process_message(
    customer_message: str,
    customer_name: str = "",
    customer_phone: str = "",
    conversation_history: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    customer_message = customer_message.strip()
    if not customer_message:
        return _default_response("")

    messages: List[dict] = []
    for item in conversation_history or []:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": str(content)})

    context_parts = []
    if customer_name:
        context_parts.append(f"Customer WhatsApp name: {customer_name}")
    if customer_phone:
        context_parts.append(f"Customer phone: {customer_phone}")
    if context_parts:
        messages.append(
            {
                "role": "user",
                "content": "[Context] " + " | ".join(context_parts),
            }
        )

    messages.append({"role": "user", "content": customer_message})

    try:
        client = get_client()
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *messages,
            ],
            temperature=0.4,
            max_tokens=700,
            response_format={"type": "json_object"},
        )

        content = completion.choices[0].message.content or ""
        parsed = _normalize_response(_extract_json(content))
    except Exception:
        logger.exception("Agent failed to process message or parse JSON")
        parsed = _default_response(customer_message)

    return _merge_customer_context(parsed, customer_name, customer_phone)
