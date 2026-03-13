from twilio.rest import Client
from config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_API_KEY,
    TWILIO_API_SECRET,
    TWILIO_WHATSAPP_NUMBER
)

if TWILIO_ACCOUNT_SID and TWILIO_API_KEY and TWILIO_API_SECRET and TWILIO_WHATSAPP_NUMBER:
    client = Client(TWILIO_API_KEY, TWILIO_API_SECRET, TWILIO_ACCOUNT_SID)
else:
    client = None

def send_whatsapp_message(phone, message):
    if client is None:
        print("Twilio is not configured. Please check environment variables.")
        return None

    try:
        msg = client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{phone}"
        )
        return msg.sid
    except Exception as e:
        print(f"Failed to send WhatsApp message to {phone}: {e}")
        return None
