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
        print(f"WhatsApp message sent to {to_number}: {msg.sid}")
        return msg.sid
    except Exception as e:
        print(f"Failed to send WhatsApp message to {to_number}: {e}")
        return None
