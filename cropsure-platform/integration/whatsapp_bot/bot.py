import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

sessions = {}

CROP_OPTIONS = ["maize", "beans", "tea", "cassava"]

def calculate_premium(acres, crop, risk_zone="medium"):
    base_rates = {"maize": 300, "beans": 250, "tea": 400, "cassava": 200}
    multipliers = {"low": 0.8, "medium": 1.2, "high": 1.8}
    base = base_rates.get(crop, 300)
    multiplier = multipliers.get(risk_zone, 1.2)
    return round(acres * base * multiplier)

def send_reply(msg):
    resp = MessagingResponse()
    resp.message(msg)
    return str(resp)

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming = request.form.get("Body", "").strip()
    phone = request.form.get("From", "").replace("whatsapp:", "")

    if incoming.upper() in ["TOKA", "LEAVE", "STOP"]:
        sessions.pop(phone, None)
        return send_reply("Umesimama. You have opted out of CropSure.\nContact your agent to process a formal opt-out request.")

    if incoming.upper() in ["JIUNGE", "JOIN"] or phone not in sessions:
        sessions[phone] = {"state": "GET_NAME", "data": {}}
        return send_reply("Karibu CropSure! Welcome to CropSure!\nTunalinda shamba lako kutoka angani.\nWe protect your farm from space.\n\nWhat is your full name?")

    session = sessions[phone]
    state = session["state"]
    data = session["data"]

    if state == "GET_NAME":
        if len(incoming) < 3:
            return send_reply("Please enter your full name.")
        data["name"] = incoming
        session["state"] = "GET_PHONE"
        return send_reply(f"Thank you {data['name']}. What is your M-Pesa phone number?")

    elif state == "GET_PHONE":
        phone_clean = incoming.replace(" ", "").replace("-", "")
        if not phone_clean.startswith(("07", "01", "+254")):
            return send_reply("Please enter a valid Kenyan phone number e.g. 0712345678")
        data["mpesa_phone"] = phone_clean
        session["state"] = "GET_VILLAGE"
        return send_reply("Which village or town is your farm near?")

    elif state == "GET_VILLAGE":
        data["village"] = incoming
        session["state"] = "GET_CROP"
        return send_reply("What is your main crop?\n1. Maize\n2. Beans\n3. Tea\n4. Cassava\nReply with the number or crop name.")

    elif state == "GET_CROP":
        crop_map = {"1": "maize", "2": "beans", "3": "tea", "4": "cassava"}
        crop = crop_map.get(incoming, incoming.lower())
        if crop not in CROP_OPTIONS:
            return send_reply("Please choose:\n1. Maize\n2. Beans\n3. Tea\n4. Cassava")
        data["crop"] = crop
        session["state"] = "GET_FARMING_TYPE"
        return send_reply("Do you grow one crop or multiple crops?\n1. One crop only\n2. Multiple crops")

    elif state == "GET_FARMING_TYPE":
        if incoming in ["1", "one"]:
            data["farming_type"] = "monocrop"
        elif incoming in ["2", "multiple"]:
            data["farming_type"] = "intercrop"
        else:
            return send_reply("Please reply 1 for one crop or 2 for multiple crops.")
        session["state"] = "GET_ACRES"
        return send_reply("How many acres is your farm? e.g. 2 or 2.5")

    elif state == "GET_ACRES":
        try:
            acres = float(incoming)
            if acres <= 0 or acres > 100:
                return send_reply("Please enter a valid farm size between 0.5 and 100 acres.")
        except ValueError:
            return send_reply("Please enter a number e.g. 2 or 2.5")
        data["acres"] = acres
        premium = calculate_premium(acres, data["crop"])
        data["premium"] = premium
        session["state"] = "CONFIRM"
        return send_reply(
            f"Please confirm:\n\n"
            f"Name: {data['name']}\n"
            f"Village: {data['village']}\n"
            f"Crop: {data['crop'].capitalize()}\n"
            f"Type: {data['farming_type'].capitalize()}\n"
            f"Size: {data['acres']} acres\n"
            f"Premium: KES {data['premium']}\n\n"
            f"Reply YES to enroll and pay via M-Pesa.\n"
            f"Reply NO to cancel."
        )

    elif state == "CONFIRM":
        if incoming.upper() == "YES":
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/farms/enroll",
                    json={
                        "name": data["name"],
                        "mpesa_phone": data["mpesa_phone"],
                        "village": data["village"],
                        "crop": data["crop"],
                        "farming_type": data["farming_type"],
                        "acres": data["acres"],
                        "premium": data["premium"],
                        "enrollment_channel": "whatsapp"
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    result = response.json()
                    policy_number = result.get("policy_number", "CS001")
                    sessions.pop(phone, None)
                    return send_reply(
                        f"Hongera! Congratulations!\n\n"
                        f"Policy number: {policy_number}\n"
                        f"M-Pesa payment request of KES {data['premium']} sent to {data['mpesa_phone']}.\n\n"
                        f"Your farm is now monitored from space every 5 days."
                    )
                else:
                    return send_reply("Enrollment failed. Please try again or contact your agent.")
            except Exception:
                return send_reply("Could not connect to server. Please try again shortly.")

        elif incoming.upper() == "NO":
            sessions.pop(phone, None)
            return send_reply("Enrollment cancelled. Text JIUNGE anytime to start again.")
        else:
            return send_reply("Please reply YES to confirm or NO to cancel.")

    return send_reply("Sorry, something went wrong. Text JIUNGE to start again.")

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "cropsure-whatsapp-bot"}

@app.route("/notify-payout", methods=["POST"])
def notify_payout():
    data = request.json
    phone = data.get("phone")
    amount = data.get("amount")
    reason = data.get("reason")
    ndvi_drop = data.get("ndvi_drop")
    policy = data.get("policy_number")

    from twilio.rest import Client
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    client.messages.create(
        from_=os.getenv("TWILIO_WHATSAPP_FROM"),
        to=f"whatsapp:{phone}",
        body=(
            f"CropSure Alert - Payout Triggered\n\n"
            f"Policy: {policy}\n"
            f"Reason: {reason}\n"
            f"NDVI dropped {ndvi_drop}% below your seasonal baseline.\n"
            f"KES {amount} sent to your M-Pesa."
        )
    )
    return {"status": "sent"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
