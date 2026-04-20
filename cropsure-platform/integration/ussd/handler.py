import os
import requests
from flask import Flask, request

app = Flask(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

def calculate_premium(acres, crop, risk_zone="medium"):
    base_rates = {"maize": 300, "beans": 250, "tea": 400, "cassava": 200}
    multipliers = {"low": 0.8, "medium": 1.2, "high": 1.8}
    base = base_rates.get(crop, 300)
    multiplier = multipliers.get(risk_zone, 1.2)
    return round(acres * base * multiplier)

@app.route("/ussd", methods=["POST", "GET"])
def ussd():
    session_id = request.values.get("sessionId")
    phone = request.values.get("phoneNumber", "")
    text = request.values.get("text", "")

    # Split text into steps — each * separates a menu level
    steps = text.split("*") if text else []
    level = len(steps)

    # -------------------------------------------------------
    # LEVEL 0 — Main menu
    # -------------------------------------------------------
    if text == "":
        response = (
            "CON Welcome to CropSure\n"
            "Tunalinda shamba lako kutoka angani\n\n"
            "1. Enroll my farm\n"
            "2. Check my policy\n"
            "3. Check payout status\n"
            "4. Help"
        )

    # -------------------------------------------------------
    # OPTION 1 — Enroll my farm
    # -------------------------------------------------------
    elif steps[0] == "1":
        if level == 1:
            response = "CON Enter your full name:"

        elif level == 2:
            response = "CON Enter your M-Pesa phone number:"

        elif level == 3:
            response = "CON Enter your village or town name:"

        elif level == 4:
            response = (
                "CON Select your main crop:\n"
                "1. Maize\n"
                "2. Beans\n"
                "3. Tea\n"
                "4. Cassava"
            )

        elif level == 5:
            crop_choice = steps[4]
            if crop_choice not in ["1", "2", "3", "4"]:
                response = (
                    "CON Invalid choice. Select your main crop:\n"
                    "1. Maize\n"
                    "2. Beans\n"
                    "3. Tea\n"
                    "4. Cassava"
                )
            else:
                response = (
                    "CON Do you grow one crop or multiple crops?\n"
                    "1. One crop only\n"
                    "2. Multiple crops"
                )

        elif level == 6:
            farming_choice = steps[5]
            if farming_choice not in ["1", "2"]:
                response = (
                    "CON Invalid choice.\n"
                    "1. One crop only\n"
                    "2. Multiple crops"
                )
            else:
                response = "CON Enter your farm size in acres e.g. 2 or 2.5:"

        elif level == 7:
            # All data collected — calculate premium and confirm
            name = steps[1]
            mpesa_phone = steps[2]
            village = steps[3]
            crop_map = {"1": "maize", "2": "beans", "3": "tea", "4": "cassava"}
            crop = crop_map.get(steps[4], "maize")
            farming_type = "monocrop" if steps[5] == "1" else "intercrop"

            try:
                acres = float(steps[6])
            except ValueError:
                response = "CON Invalid farm size. Enter acres as a number e.g. 2 or 2.5:"
                return response

            premium = calculate_premium(acres, crop)

            response = (
                f"CON Confirm enrollment:\n\n"
                f"Name: {name}\n"
                f"Phone: {mpesa_phone}\n"
                f"Village: {village}\n"
                f"Crop: {crop.capitalize()}\n"
                f"Type: {farming_type.capitalize()}\n"
                f"Size: {acres} acres\n"
                f"Premium: KES {premium}\n\n"
                f"1. Confirm and pay via M-Pesa\n"
                f"2. Cancel"
            )

        elif level == 8:
            confirm = steps[7]
            if confirm == "1":
                # Call backend to enroll
                name = steps[1]
                mpesa_phone = steps[2]
                village = steps[3]
                crop_map = {"1": "maize", "2": "beans", "3": "tea", "4": "cassava"}
                crop = crop_map.get(steps[4], "maize")
                farming_type = "monocrop" if steps[5] == "1" else "intercrop"
                try:
                    acres = float(steps[6])
                except ValueError:
                    acres = 1.0
                premium = calculate_premium(acres, crop)

                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/api/farms/enroll",
                        json={
                            "name": name,
                            "mpesa_phone": mpesa_phone,
                            "village": village,
                            "crop": crop,
                            "farming_type": farming_type,
                            "acres": acres,
                            "premium": premium,
                            "enrollment_channel": "ussd"
                        },
                        timeout=10
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        policy = result.get("policy_number", "CS001")
                        response = (
                            f"END Hongera! Enrolled successfully.\n\n"
                            f"Policy: {policy}\n"
                            f"M-Pesa request of KES {premium} sent to {mpesa_phone}.\n\n"
                            f"Your farm is now monitored from space every 5 days.\n"
                            f"Welcome to CropSure!"
                        )
                    else:
                        response = "END Enrollment failed. Please try again or contact your agent."
                except Exception:
                    response = "END Could not connect. Please try again shortly."

            elif confirm == "2":
                response = "END Enrollment cancelled. Dial *384# anytime to try again."
            else:
                response = "END Invalid input. Dial *384# to try again."

        else:
            response = "END Something went wrong. Dial *384# to start again."

    # -------------------------------------------------------
    # OPTION 2 — Check my policy
    # -------------------------------------------------------
    elif steps[0] == "2":
        if level == 1:
            response = "CON Enter your phone number to check your policy:"
        elif level == 2:
            check_phone = steps[1]
            try:
                resp = requests.get(
                    f"{BACKEND_URL}/api/farms",
                    params={"phone": check_phone},
                    timeout=10
                )
                if resp.status_code == 200:
                    farms = resp.json()
                    if farms:
                        farm = farms[0]
                        response = (
                            f"END Policy: {farm.get('policy_number', 'N/A')}\n"
                            f"Farm: {farm.get('village', 'N/A')}\n"
                            f"Crop: {farm.get('crop', 'N/A').capitalize()}\n"
                            f"Size: {farm.get('acres', 'N/A')} acres\n"
                            f"Status: {farm.get('status', 'Active')}\n"
                            f"NDVI Health: {farm.get('ndvi_health', 'Good')}"
                        )
                    else:
                        response = "END No policy found for that number.\nDial *384# to enroll."
                else:
                    response = "END Could not retrieve policy. Try again later."
            except Exception:
                response = "END Could not connect. Try again shortly."
        else:
            response = "END Invalid input."

    # -------------------------------------------------------
    # OPTION 3 — Check payout status
    # -------------------------------------------------------
    elif steps[0] == "3":
        if level == 1:
            response = "CON Enter your phone number to check payouts:"
        elif level == 2:
            check_phone = steps[1]
            try:
                resp = requests.get(
                    f"{BACKEND_URL}/api/farms/payouts",
                    params={"phone": check_phone},
                    timeout=10
                )
                if resp.status_code == 200:
                    payouts = resp.json()
                    if payouts:
                        latest = payouts[0]
                        response = (
                            f"END Latest payout:\n"
                            f"Amount: KES {latest.get('amount', 'N/A')}\n"
                            f"Reason: {latest.get('reason', 'N/A')}\n"
                            f"Date: {latest.get('date', 'N/A')}\n"
                            f"Status: {latest.get('status', 'N/A')}"
                        )
                    else:
                        response = "END No payouts found for that number.\nYour farm is being monitored."
                else:
                    response = "END Could not retrieve payout data."
            except Exception:
                response = "END Could not connect. Try again shortly."
        else:
            response = "END Invalid input."

    # -------------------------------------------------------
    # OPTION 4 — Help
    # -------------------------------------------------------
    elif steps[0] == "4":
        response = (
            "END CropSure Help:\n\n"
            "CropSure protects your farm using\n"
            "satellite monitoring from space.\n\n"
            "When your crops are stressed,\n"
            "we automatically send money\n"
            "to your M-Pesa within 24 hours.\n\n"
            "For help call: 0800 720 000\n"
            "Or WhatsApp: +254 700 000 000"
        )

    else:
        response = "END Invalid option. Dial *384# to try again."

    return response

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "cropsure-ussd"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
