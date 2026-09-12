# Saree CRM Agent

AI-powered WhatsApp automation for a D2C saree and kurti business — built for reliability and growth.

## 🚀 GTM Engineering Highlights
This project isn't just a wrapper; it's designed as a GTM tool to maximize lead conversion and operational efficiency:

- **API Resilience**: Implements a custom retry mechanism for transient failures in WhatsApp and Google Sheets APIs, ensuring no lead is lost due to network blips.
- **Structured Intent Classification**: Uses Llama 3 (70B) with strict JSON mode to classify customer intent in real-time, enabling precise CRM routing.
- **Zero-Latency CRM Automation**: Direct integration with Google Sheets as a lightweight CRM, providing instant visibility into "Hot" leads for the sales team.
- **Growth Observability**: Integrated `GTM_METRIC` logging to track lead capture rates and intent distribution directly from the server logs.

| Service | Purpose | Cost |
|---------|---------|------|
| [Groq](https://console.groq.com) | AI replies (Llama 3 70B) | Free tier |
| [Meta WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api) | Send/receive WhatsApp messages | Free tier (1,000 conversations/month) |
| [Google Sheets](https://sheets.google.com) + service account | Leads, orders, follow-ups | Free |

## Project structure

```
saree-crm-agent/
├── main.py        # Flask server — webhooks, /test, /health
├── agent.py       # Groq AI — Hinglish replies + intent detection
├── whatsapp.py    # Meta WhatsApp Cloud API
├── sheets.py      # Google Sheets CRM logging
├── config.py      # Environment configuration
├── .env           # Secrets (not committed)
└── requirements.txt
```

## Quick start (test without WhatsApp or Sheets)

You only need a free Groq API key to test the agent locally.

```bash
cd ~/Projects/saree-crm-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add your Groq key to `.env`:

```
GROQ_API_KEY=gsk_your_key_here
```

Start the server:

```bash
python main.py
```

Send a test message:

```bash
curl -X POST http://localhost:5000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Red silk saree ka price kya hai?", "name": "Priya"}'
```

Example response:

```json
{
  "status": "ok",
  "reply": "Namaste Priya! Red silk saree ₹1,499 se start hoti hai...",
  "intent": "price_inquiry",
  "lead_data": {
    "name": "Priya",
    "phone": "919999999999",
    "interest": "red silk saree",
    "budget": ""
  },
  "whatsapp_sent": false,
  "sheets": null
}
```

---

## Step 1 — Groq API (free AI)

1. Go to [console.groq.com](https://console.groq.com) and create a free account.
2. Open **API Keys** → **Create API Key**.
3. Copy the key into `.env`:

   ```
   GROQ_API_KEY=gsk_xxxxxxxx
   ```

The agent uses `llama-3.3-70b-versatile` and replies in Hinglish. It classifies every message into one of:

- `price_inquiry`
- `availability`
- `order_placement`
- `cod_question`
- `shipping_question`
- `general`

---

## Step 2 — Meta WhatsApp Cloud API (free messaging)

### 2a. Create a Meta app

1. Go to [developers.facebook.com](https://developers.facebook.com) → **My Apps** → **Create App**.
2. Choose **Other** → **Business** → name it (e.g. `Saree CRM`).
3. Add the **WhatsApp** product to your app.

### 2b. Get test credentials

In the WhatsApp setup panel you will see:

- **Temporary access token** (valid 24h; generate a permanent token later)
- **Phone number ID**
- **WhatsApp Business Account ID**

Add them to `.env`:

```
META_WHATSAPP_TOKEN=EAAxxxxx
META_PHONE_NUMBER_ID=123456789012345
META_VERIFY_TOKEN=showup123
```

`META_VERIFY_TOKEN` is a secret string you choose — Meta sends it back during webhook verification. The default in this project is `showup123`.

### 2c. Expose your local server

Meta needs a public HTTPS URL. Use [ngrok](https://ngrok.com):

```bash
ngrok http 5000
```

Copy the HTTPS URL (e.g. `https://abc123.ngrok-free.app`).

### 2d. Configure the webhook

1. In Meta Developer Console → **WhatsApp** → **Configuration**.
2. Click **Edit** on the webhook callback URL.
3. Set:
   - **Callback URL:** `https://abc123.ngrok-free.app/webhook/whatsapp`
   - **Verify token:** `showup123` (must match `META_VERIFY_TOKEN` in `.env`)
4. Click **Verify and Save**.
5. Subscribe to the **messages** webhook field.

### 2e. Add a test recipient

In **WhatsApp** → **API Setup**, add your phone number as a test recipient and send the join code from your phone.

### 2f. Permanent token (optional, for production)

1. Create a [System User](https://business.facebook.com/settings/system-users) in Meta Business Manager.
2. Generate a token with `whatsapp_business_messaging` and `whatsapp_business_management` permissions.
3. Replace `META_WHATSAPP_TOKEN` in `.env` with the permanent token.

---

## Step 3 — Google Sheets (free CRM)

### 3a. Create the spreadsheet

Create a Google Sheet with three tabs and these headers in row 1:

**Leads**

| Timestamp | Name | Phone | Interest | Budget | Intent | Status |

**Orders**

| Timestamp | Name | Phone | Item | Amount | COD | Address | Status |

**Follow-ups**

| Timestamp | Name | Phone | Last_Contact | Follow_up_date | Notes |

Copy the Sheet ID from the URL:

```
https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
```

Add to `.env`:

```
GOOGLE_SHEET_ID=your_sheet_id_here
GOOGLE_CREDENTIALS_PATH=credentials.json
```

### 3b. Create a service account

1. Go to [Google Cloud Console](https://console.cloud.google.com).
2. Create a project (or use an existing one).
3. Enable the **Google Sheets API** and **Google Drive API**.
4. Go to **IAM & Admin** → **Service Accounts** → **Create Service Account**.
5. Open the service account → **Keys** → **Add Key** → **JSON**.
6. Save the downloaded file as `credentials.json` in the project root.

### 3c. Share the sheet

Open the JSON file and copy the `client_email` (e.g. `saree-crm@project.iam.gserviceaccount.com`).

Share your Google Sheet with that email as **Editor**.

---

## Step 4 — Run the server

```bash
source .venv/bin/activate
python main.py
```

Server runs on `http://0.0.0.0:5000`.

Check configuration status:

```bash
curl http://localhost:5000/health
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service status and config flags |
| POST | `/test` | Test the agent locally (no WhatsApp/Sheets required) |
| GET | `/webhook/whatsapp` | Meta webhook verification |
| POST | `/webhook/whatsapp` | Receive incoming WhatsApp messages |

### POST /test

Test the AI agent without sending WhatsApp messages or writing to Sheets.

```bash
curl -X POST http://localhost:5000/test \
  -H "Content-Type: application/json" \
  -d '{
    "message": "COD available hai kya?",
    "name": "Anita",
    "phone": "919876543210"
  }'
```

Optional fields:

| Field | Default | Description |
|-------|---------|-------------|
| `save_to_sheets` | `false` | Write lead/order/follow-up to Google Sheets |
| `send_whatsapp` | `false` | Send the reply via Meta WhatsApp API |

---

## How messages flow
```
Customer WhatsApp message
        │
        ▼
Meta Cloud API webhook  →  POST /webhook/whatsapp
        │
        ▼
Groq (Llama 3 70B)  →  { reply, intent, lead_data }
        │
        ├──► Google Sheets (CRM: Leads / Orders / Follow-ups)
        │    └─ Triggered based on intent classification
        │
        └──► Meta API sends Hinglish reply to customer
```

---

## Technical Decisions
- **Hinglish AI**: Chose Llama 3 via Groq for low-latency, high-reasoning capabilities in regional Indian dialects.
- **JSON-First API**: Enforced `response_format={"type": "json_object"}` to ensure the AI output can be programmatically routed to the CRM without fragile regex parsing.
- **Stateless Webhook**: Designed the Flask server to be stateless, allowing for easy horizontal scaling as lead volume grows.
- **Safe Writes**: Wrapped Google Sheets operations in `safe_record_agent_result` to ensure a CRM failure doesn't crash the customer's chat experience.

---

## Environment variables

| Variable | Required for | Description |
|----------|--------------|-------------|
| `GROQ_API_KEY` | AI replies | Free Groq API key |
| `META_WHATSAPP_TOKEN` | WhatsApp send/receive | Meta permanent or temp token |
| `META_PHONE_NUMBER_ID` | WhatsApp send/receive | From Meta WhatsApp API Setup |
| `META_VERIFY_TOKEN` | Webhook verification | Your chosen secret (default: `showup123`) |
| `GOOGLE_SHEET_ID` | Sheets logging | Spreadsheet ID from URL |
| `GOOGLE_CREDENTIALS_PATH` | Sheets logging | Path to service account JSON |
| `FLASK_PORT` | Server | Port (default: `5000`) |
| `FLASK_DEBUG` | Server | Debug mode (default: `true`) |

---

## Troubleshooting

**Webhook verification fails**
- Confirm `META_VERIFY_TOKEN` in `.env` matches the token entered in Meta Console.
- Ensure ngrok is running and the callback URL is HTTPS.

**Groq returns an error**
- Check `GROQ_API_KEY` is valid at [console.groq.com](https://console.groq.com).
- Free tier has rate limits; wait a moment and retry.

**Google Sheets write fails**
- Confirm the sheet is shared with the service account email.
- Verify tab names are exactly `Leads`, `Orders`, and `Follow-ups`.
- Check `GOOGLE_SHEET_ID` and `credentials.json` path.

**WhatsApp message not received**
- Your phone must be added as a test recipient in Meta Console.
- Check the webhook is subscribed to the `messages` field.

---

## License

Private — internal use for the saree/kurti business.
