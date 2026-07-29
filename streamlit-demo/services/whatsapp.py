import os
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables from whatsapp_bot/.env or current env
# We'll try to explicitly load from whatsapp_bot/.env if it exists
whatsapp_env_path = Path(__file__).resolve().parent.parent.parent / "whatsapp_bot" / ".env"
if whatsapp_env_path.exists():
    load_dotenv(whatsapp_env_path, override=True)
else:
    load_dotenv(override=True)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_API_KEY = os.getenv("TWILIO_API_KEY")
TWILIO_API_SECRET = os.getenv("TWILIO_API_SECRET")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

if TWILIO_ACCOUNT_SID and TWILIO_API_KEY and TWILIO_API_SECRET and TWILIO_WHATSAPP_NUMBER:
    client = Client(TWILIO_API_KEY, TWILIO_API_SECRET, TWILIO_ACCOUNT_SID)
else:
    client = None

def send_whatsapp_message(phone: str, message: str) -> Optional[str]:
    """
    Sends a WhatsApp message using Twilio.
    Returns the message SID if successful, None otherwise.
    """
    if client is None:
        print("Twilio is not configured. Please check environment variables.")
        return None

    # Clean the recipient phone number
    clean_phone = str(phone).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if clean_phone.startswith('whatsapp:'):
        to_number = clean_phone
    else:
        if not clean_phone.startswith('+'):
            clean_phone = '+' + clean_phone
        to_number = f"whatsapp:{clean_phone}"

    # Clean the sender phone number (from_)
    from_number = TWILIO_WHATSAPP_NUMBER
    if not from_number.startswith('whatsapp:'):
        from_number = f"whatsapp:{from_number}"

    try:
        msg = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number
        )
        print(f"[{msg.status}] WhatsApp message sent to {to_number}: {msg.sid}")
        return msg.sid
    except Exception as e:
        print(f"Failed to send WhatsApp message to {to_number}: {e}")
        return None
