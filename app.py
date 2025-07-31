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
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "your-default-key")  # Optional: set via env var

app = Flask(__name__)

# 🌍 CORS Setup
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:3000",
    "https://possessher-ai-frontend.vercel.app"
]}}, supports_credentials=True)

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
    if not data or not isinstance(data, list) or len(data) == 0:
        return False
    return data[0].get("is_pro", False)

# 📊 Check if usage limit reached
def check_usage_limit(user_id, usage_type, max_limit=3):
    current_month = datetime.utcnow().strftime("%Y-%m")
    table = "image_logs" if usage_type == "image" else "chat_logs"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Accept": "application/json"
    }
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}?user_id=eq.{user_id}",
        headers=headers
    )
    try:
        data = r.json()
        if not isinstance(data, list):
            return False
        monthly_count = sum(1 for record in data if record.get("timestamp", "").startswith(current_month))
        return monthly_count < max_limit
    except:
        return False

# 🔢 Count usage
def count_usage(user_id, usage_type):
    current_month = datetime.utcnow().strftime("%Y-%m")
    table = "image_logs" if usage_type == "image" else "chat_logs"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Accept": "application/json"
    }
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}?user_id=eq.{user_id}",
        headers=headers
    )
    try:
        data = r.json()
        if not isinstance(data, list):
            return 0
        return sum(1 for record in data if record.get("timestamp", "").startswith(current_month))
    except:
        return 0

# 📝 Record usage
def record_usage(user_id, usage_type):
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    table = "image_logs" if usage_type == "image" else "chat_logs"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "user_id": user_id,
        "timestamp": timestamp
    }
    requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=headers, json=payload)

# 💬 Chat endpoint
@app.route("/chat", methods=["POST"])
def chat():
    user_messages = request.json.get("messages", [])
    if not user_messages or not isinstance(user_messages, list):
        return jsonify({ "reply": "Invalid message input." }), 400

    user_prompt = user_messages[-1].get("content", "").strip()
    email = request.json.get("email")
    user_id = request.json.get("user_id", email)

    if not email:
        return jsonify({ "reply": "Login required." }), 401

    is_pro = check_is_pro(email)
    if not is_pro and not check_usage_limit(user_id, "chat"):
        return jsonify({ "reply": "⚠️ Monthly chat limit reached. Upgrade to Pro 💖" })

    ai_reply = generate_yandere_reply(user_prompt)

    trigger_keywords = ["show me", "picture", "photo", "image", "see you", "selfie"]
    if any(keyword in user_prompt.lower() for keyword in trigger_keywords):
        prompt = f"{persona['base_prompt']}, scene: {user_prompt}"
        if not is_pro:
            if not check_usage_limit(user_id, "image"):
                return jsonify({ "reply": "⚠️ Monthly image limit reached. Upgrade to Pro 💖" })
            prompt = prompt.replace("large boobs", "modest figure").replace("large butt", "").replace("seductive pose", "cute pose")

        image_path = generate_image(user_id, prompt)

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            if not is_pro:
                record_usage(user_id, "image")

            return jsonify({
                "reply": ai_reply,
                "image_base64": image_base64
            })

        return jsonify({ "reply": ai_reply + "\n\n⚠️ But I couldn't find the photo... try again?" })

    if not is_pro:
        record_usage(user_id, "chat")

    return jsonify({ "reply": ai_reply })

# 🎨 Generate image endpoint
@app.route("/generate", methods=["POST"])
def generate():
    email = request.json.get("email")
    user_id = request.json.get("user_id", email)

    if not email:
        return jsonify({ "error": "Login required." }), 401

    is_pro = check_is_pro(email)
    if not is_pro and not check_usage_limit(user_id, "image"):
        return jsonify({ "error": "⚠️ Monthly image limit reached. Upgrade to Pro 💖" }), 403

    prompt = f"{persona['base_prompt']}, {get_random_prompt()}"
    if not is_pro:
        prompt = prompt.replace("large boobs", "modest figure").replace("large butt", "").replace("seductive pose", "cute pose")

    image_path = generate_image(user_id, prompt)

    if not is_pro:
        record_usage(user_id, "image")

    return send_file(image_path, mimetype='image/png')

# 💳 Gumroad Webhook
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

# 📊 Scarcity info endpoint
@app.route("/usage", methods=["POST"])
def usage():
    email = request.json.get("email")
    user_id = request.json.get("user_id", email)

    if not email:
        return jsonify({ "error": "Login required." }), 401

    is_pro = check_is_pro(email)
    image_limit = 9999 if is_pro else 3
    chat_limit = 9999 if is_pro else 5

    image_used = count_usage(user_id, "image")
    chat_used = count_usage(user_id, "chat")

    return jsonify({
        "is_pro": is_pro,
        "image_limit": image_limit,
        "chat_limit": chat_limit,
        "image_used": image_used,
        "chat_used": chat_used,
        "image_remaining": max(image_limit - image_used, 0),
        "chat_remaining": max(chat_limit - chat_used, 0)
    })

# 🚀 Start app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)