from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from chat import generate_yandere_reply
from generate import generate_image
from prompts import get_random_prompt
import os
import base64
import requests

# ✅ Persona prompt
persona = {
    "name": "Miyume",
    "base_prompt": (
        "anime girl, pink twin-tail hair, violet eyes, curvy body, large boobs, large butt, beautiful body, "
        "intense yandere expression, seductive pose, ultra detailed, high quality, sharp lines"
    )
}

# 🔐 Supabase Setup
SUPABASE_URL = "https://vfejiqpioxmqkunpqgqs.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZmZWppcXBpb3htcWt1bnBxZ3FzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzQ0OTQ2MywiZXhwIjoyMDY5MDI1NDYzfQ.dtVFob_t-wLF_NxEiRMKKNcTJbUH08qmtc1iREpElok"  # 🔁 Replace this with your actual key

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])

@app.route("/chat", methods=["POST"])
def chat():
    user_messages = request.json.get("messages", [])
    user_prompt = user_messages[-1]["content"]

    ai_reply = generate_yandere_reply(user_prompt)

    trigger_keywords = ["show me", "picture", "photo", "image", "see you", "selfie"]
    if any(keyword in user_prompt.lower() for keyword in trigger_keywords):
        image_prompt = f"{persona['base_prompt']}, scene: {user_prompt}"
        image_path = generate_image("user1", image_prompt)

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            return jsonify({
                "reply": ai_reply,
                "image_base64": image_base64
            })

        return jsonify({ "reply": ai_reply + "\n\n⚠️ But I couldn't find the photo... try again?" })

    return jsonify({ "reply": ai_reply })

@app.route("/generate", methods=["POST"])
def generate():
    user_id = request.json.get("user_id", "anon")
    prompt = f"{persona['base_prompt']}, {get_random_prompt()}"
    image_path = generate_image(user_id, prompt)
    return send_file(image_path, mimetype='image/png')


@app.route("/gumroad-webhook", methods=["POST"])
def gumroad_webhook():
    payload = request.form
    email = payload.get("email")
    sale_id = payload.get("sale_id")
    product_name = payload.get("product_name")

    if not email or not sale_id:
        return "Missing fields", 400

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    # ✅ Step 1: Upsert (create or update) user profile
    profile_payload = {
        "email": email,
        "is_pro": True
    }
    upsert_profile = requests.post(
        f"{SUPABASE_URL}/rest/v1/profiles",
        headers={**headers, "Prefer": "resolution=merge-duplicates"},
        json=profile_payload
    )

    # ✅ Step 2 (optional): Log the purchase
    purchase_payload = {
        "email": email,
        "sale_id": sale_id,
        "product_name": product_name or "PossessHer AI Premium"
    }
    log_purchase = requests.post(
        f"{SUPABASE_URL}/rest/v1/purchases",
        headers=headers,
        json=purchase_payload
    )

    if upsert_profile.status_code in [200, 201, 204]:
        return "User updated and purchase logged", 200
    else:
        print("❌ Profile error:", upsert_profile.text)
        return "Error updating profile", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)