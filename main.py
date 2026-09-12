import logging

from flask import Flask, jsonify, request

import agent
import config
import sheets
import whatsapp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def handle_customer_message(
    message: str,
    name: str = "",
    phone: str = "",
    save_to_sheets: bool = True,
    send_whatsapp: bool = False,
) -> dict:
    agent_response = agent.process_message(
        customer_message=message,
        customer_name=name,
        customer_phone=phone,
    )

    result = {
        "reply": agent_response["reply"],
        "intent": agent_response["intent"],
        "lead_data": agent_response["lead_data"],
        "whatsapp_sent": False,
        "sheets": None,
    }

    if save_to_sheets:
        result["sheets"] = sheets.safe_record_agent_result(
            agent_response,
            sender_phone=phone,
            sender_name=name,
        )
        if result["sheets"] and "lead_saved" in result["sheets"]:
            logger.info(
                "GTM_METRIC: Lead captured | Phone: %s | Intent: %s",
                phone,
                agent_response["intent"]
            )

    if send_whatsapp and phone:
        if config.whatsapp_configured():
            whatsapp.send_message(to=phone, body=agent_response["reply"])
            result["whatsapp_sent"] = True
        else:
            result["whatsapp_error"] = "Meta WhatsApp credentials are not configured"

    return result


@app.route("/webhook/whatsapp", methods=["GET", "POST"])
def whatsapp_webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode", "")
        token = request.args.get("hub.verify_token", "")
        challenge = request.args.get("hub.challenge", "")
        body, status = whatsapp.verify_webhook(mode, token, challenge)
        return body, status

    payload = request.get_json(silent=True) or {}
    incoming_messages = whatsapp.parse_incoming_messages(payload)

    if not incoming_messages:
        return jsonify({"status": "ignored"}), 200

    processed = []
    for incoming in incoming_messages:
        try:
            outcome = handle_customer_message(
                message=incoming["body"],
                name=incoming["profile_name"],
                phone=incoming["from"],
                save_to_sheets=True,
                send_whatsapp=True,
            )
            processed.append(
                {
                    "from": incoming["from"],
                    "message_id": incoming["message_id"],
                    "intent": outcome["intent"],
                }
            )
        except Exception:
            logger.exception("Failed to process WhatsApp message from %s", incoming["from"])
            processed.append(
                {
                    "from": incoming["from"],
                    "message_id": incoming["message_id"],
                    "error": "processing_failed",
                }
            )

    return jsonify({"status": "ok", "processed": processed}), 200


@app.route("/test", methods=["POST"])
def test_agent():
    data = request.get_json(silent=True) or {}

    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Missing required field: message"}), 400

    name = data.get("name", "Test Customer").strip()
    phone = data.get("phone", "919999999999").strip()
    save_to_sheets = data.get("save_to_sheets", False)
    send_whatsapp = data.get("send_whatsapp", False)

    if not config.groq_configured():
        return jsonify(
            {
                "error": "GROQ_API_KEY is not configured",
                "hint": "Get a free key at https://console.groq.com and add it to .env",
            }
        ), 503

    try:
        outcome = handle_customer_message(
            message=message,
            name=name,
            phone=phone,
            save_to_sheets=save_to_sheets,
            send_whatsapp=send_whatsapp,
        )
        return jsonify(
            {
                "status": "ok",
                "input": {"message": message, "name": name, "phone": phone},
                **outcome,
            }
        ), 200
    except Exception as exc:
        logger.exception("Test endpoint failed")
        return jsonify({"error": str(exc)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "groq_configured": config.groq_configured(),
            "whatsapp_configured": config.whatsapp_configured(),
            "sheets_configured": config.sheets_configured(),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
