from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from chat import generate_yandere_reply
from generate import generate_image
from prompts import get_random_prompt
import os
import base64
import requests
from datetime import datetime

# ✅ Persona Prompt
persona = {
    "name": "Miyume",
    "base_prompt": (
        "anime girl, pink twin-tail hair, violet eyes, curvy body, large boobs, large butt, beautiful body, "
        "intense yandere expression, seductive pose, ultra detailed, high quality, sharp lines"
    )
}

# 🔐 Supabase Setup
SUPABASE_URL = "https://vfejiqpioxmqkunpqgqs.supabase.co"
SUPABASE_SERVICE_KEY = "YOUR_SUPABASE_SERVICE_KEY"  # Replace this securely

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])

# 🔎 Check if user is Pro
def check_is_pro(email):
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/profiles?email=eq.{email}",
        headers=headers
    )
    data = r.json()
    return data[0]["is_pro"] if data else False

# 📊 Check if usage limit reached (for free users)
def check_usage_limit(email, usage_type):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/usage_limits?email=eq.{email}&type=eq.{usage_type}&date=eq.{today}",
        headers=headers
    )
    return len(r.json()) == 0

# 📝 Record usage (for free users)
def record_usage(email, usage_type):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "type": usage_type,
        "date": today
    }
    requests.post(f"{SUPABASE_URL}/rest/v1/usage_limits", headers=headers, json=payload)

# 💬 Chat endpoint with image check and filtering
@app.route("/chat", methods=["POST"])
def chat():
    user_messages = request.json.get("messages", [])
    user_prompt = user_messages[-1]["content"]
    email = request.json.get("email")

    if not email:
        return jsonify({ "reply": "Login required." }), 401

    is_pro = check_is_pro(email)
    if not is_pro and not check_usage_limit(email, "chat"):
        return jsonify({ "reply": "⚠️ Daily chat limit reached. Upgrade to Pro 💖" })

    ai_reply = generate_yandere_reply(user_prompt)

    trigger_keywords = ["show me", "picture", "photo", "image", "see you", "selfie"]
    if any(keyword in user_prompt.lower() for keyword in trigger_keywords):
        prompt = f"{persona['base_prompt']}, scene: {user_prompt}"
        if not is_pro:
            if not check_usage_limit(email, "image"):
                return jsonify({ "reply": "⚠️ Daily image limit reached. Upgrade to Pro 💖" })
            prompt = prompt.replace("large boobs", "modest figure").replace("large butt", "").replace("seductive pose", "cute pose")

        image_path = generate_image("user1", prompt)

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            if not is_pro:
                record_usage(email, "image")
            return jsonify({
                "reply": ai_reply,
                "image_base64": image_base64
            })

        return jsonify({ "reply": ai_reply + "\n\n⚠️ But I couldn't find the photo... try again?" })

    if not is_pro:
        record_usage(email, "chat")

    return jsonify({ "reply": ai_reply })

# 🎨 Generate image endpoint (random prompt version)
@app.route("/generate", methods=["POST"])
def generate():
    email = request.json.get("email")
    user_id = request.json.get("user_id", "anon")

    if not email:
        return jsonify({ "error": "Login required." }), 401

    is_pro = check_is_pro(email)
    if not is_pro and not check_usage_limit(email, "image"):
        return jsonify({ "error": "⚠️ Daily image limit reached. Upgrade to Pro 💖" }), 403

    prompt = f"{persona['base_prompt']}, {get_random_prompt()}"
    if not is_pro:
        prompt = prompt.replace("large boobs", "modest figure").replace("large butt", "").replace("seductive pose", "cute pose")

    image_path = generate_image(user_id, prompt)

    if not is_pro:
        record_usage(email, "image")

    return send_file(image_path, mimetype='image/png')

# 💳 Gumroad Webhook to auto-upgrade users
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

    profile_payload = {
        "email": email,
        "is_pro": True
    }
    upsert_profile = requests.post(
        f"{SUPABASE_URL}/rest/v1/profiles",
        headers={**headers, "Prefer": "resolution=merge-duplicates"},
        json=profile_payload
    )

    purchase_payload = {
        "email": email,
        "sale_id": sale_id,
        "product_name": product_name or "PossessHer AI Premium"
    }
    requests.post(
        f"{SUPABASE_URL}/rest/v1/purchases",
        headers=headers,
        json=purchase_payload
    )

    if upsert_profile.status_code in [200, 201, 204]:
        return "User updated and purchase logged", 200
    else:
        return "Error updating profile", 500

# 🚀 Start app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)