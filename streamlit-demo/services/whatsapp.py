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
    load_dotenv(whatsapp_env_path)
else:
    load_dotenv()

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

    # Ensure phone has a leading '+' or format it appropriately if needed,
    # though Twilio expects the format "whatsapp:+1234567890"
    if not phone.startswith('+'):
        # For this demo, assuming US numbers if no + is provided, but best practice is to require +
        # if not starting with +, just add it assuming country code is there
        pass # Twilio is usually forgiving or the user should supply it. We'll pass it as is.

    clean_phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not clean_phone.startswith('+'):
        clean_phone = '+' + clean_phone

    try:
        msg = client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{clean_phone}"
        )
        print(f"[{msg.status}] WhatsApp message sent to {clean_phone}: {msg.sid}")
        return msg.sid
    except Exception as e:
        print(f"Failed to send WhatsApp message to {clean_phone}: {e}")
        return None
