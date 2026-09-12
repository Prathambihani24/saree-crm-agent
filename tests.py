import unittest
from unittest.mock import MagicMock, patch
import json

import agent
import whatsapp
import sheets
import main

class TestSareeCRM(unittest.TestCase):

    def setUp(self):
        # Mock config to avoid needing .env
        self.patcher_config = patch('config.GROQ_API_KEY', 'test_key')
        self.patcher_config.start()
        self.patcher_whatsapp_token = patch('config.META_WHATSAPP_TOKEN', 'test_token')
        self.patcher_whatsapp_token.start()
        self.patcher_whatsapp_id = patch('config.META_PHONE_NUMBER_ID', 'test_id')
        self.patcher_whatsapp_id.start()
        self.patcher_sheets = patch('config.GOOGLE_SHEET_ID', 'test_sheet_id')
        self.patcher_sheets.start()

    def tearDown(self):
        self.patcher_config.stop()
        self.patcher_whatsapp_token.stop()
        self.patcher_whatsapp_id.stop()
        self.patcher_sheets.stop()

    @patch('agent.Groq')
    def test_agent_process_message_success(self, mock_groq):
        # Mock Groq response
        mock_client = mock_groq.return_value
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "reply": "Namaste! Silk saree ₹2000 hai.",
                "intent": "price_inquiry",
                "lead_data": {"name": "Priya", "phone": "123", "interest": "silk saree", "budget": ""}
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_completion

        res = agent.process_message("Price kya hai?")
        self.assertEqual(res["intent"], "price_inquiry")
        self.assertIn("₹2000", res["reply"])
        self.assertEqual(res["lead_data"]["name"], "Priya")

    @patch('agent.Groq')
    def test_agent_handles_bad_json(self, mock_groq):
        mock_client = mock_groq.return_value
        mock_completion = MagicMock()
        # Return a string that is not JSON
        mock_completion.choices = [MagicMock(message=MagicMock(content="Not JSON at all"))]
        mock_client.chat.completions.create.return_value = mock_completion

        # Should fall back to default response
        res = agent.process_message("Hello")
        self.assertEqual(res["intent"], "general")
        self.assertIn("Namaste!", res["reply"])

    def test_whatsapp_parse_incoming(self):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": [{"wa_id": "12345", "profile": {"name": "Test User"}}],
                        "messages": [{
                            "from": "12345",
                            "id": "msg_1",
                            "type": "text",
                            "text": {"body": "Hi there!"}
                        }]
                    }
                }]
            }]
        }
        msgs = whatsapp.parse_incoming_messages(payload)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["body"], "Hi there!")
        self.assertEqual(msgs[0]["profile_name"], "Test User")

    @patch('sheets.get_spreadsheet')
    def test_sheets_record_lead(self, mock_get_sheet):
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_worksheet
        mock_get_sheet.return_value = mock_sheet

        agent_res = {
            "intent": "price_inquiry",
            "lead_data": {"name": "Priya", "phone": "123", "interest": "silk", "budget": "2k"}
        }

        actions = sheets.record_agent_result(agent_res, "123", "Priya")
        self.assertTrue(actions["lead_saved"])
        self.assertTrue(actions["followup_saved"])
        self.assertFalse(actions["order_saved"])
        mock_worksheet.append_row.assert_called()

    @patch('agent.process_message')
    @patch('sheets.safe_record_agent_result')
    @patch('whatsapp.send_message')
    def test_main_handle_customer_message(self, mock_send, mock_sheets, mock_agent):
        mock_agent.return_value = {
            "reply": "Hello!",
            "intent": "general",
            "lead_data": {}
        }
        mock_sheets.return_value = {"lead_saved": True}

        outcome = main.handle_customer_message(
            message="Hi",
            name="Test",
            phone="123",
            save_to_sheets=True,
            send_whatsapp=True
        )

        self.assertEqual(outcome["reply"], "Hello!")
        mock_sheets.assert_called_once()
        mock_send.assert_called_once_with(to="123", body="Hello!")

if __name__ == "__main__":
    unittest.main()
