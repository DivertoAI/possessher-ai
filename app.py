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
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZmZWppcXBpb3htcWt1bnBxZ3FzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzQ0OTQ2MywiZXhwIjoyMDY5MDI1NDYzfQ.dtVFob_t-wLF_NxEiRMKKNcTJbUH08qmtc1iREpElok"

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "https://possessher-ai-frontend.vercel.app", "https://possessher-ai.vercel.app"], supports_credentials=True)

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin in ["http://localhost:3000", "https://possessher-ai-frontend.vercel.app"]:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

def handle_referral(referred_id, referred_email, referred_by):
    if not referred_by or referred_id == referred_by:
        return

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }

    # Check if already referred
    check = requests.get(
        f"{SUPABASE_URL}/rest/v1/referrals?referred_id=eq.{referred_id}",
        headers=headers
    )
    if check.ok and check.json():
        return  # already referred

    # Save referral
    requests.post(
        f"{SUPABASE_URL}/rest/v1/referrals",
        headers=headers,
        json={ "referrer_id": referred_by, "referred_id": referred_id }
    )

    # Reward: add 5 to referrer's bonus
    reward_sql = f"""
    update profiles
    set referral_bonus = coalesce(referral_bonus, 0) + 5
    where id = '{referred_by}';
    """
    requests.post(
        f"{SUPABASE_URL}/rest/v1/rpc/execute_sql",
        headers=headers,
        json={ "sql": reward_sql }
    )

    # Reward: add 2 to referred user's bonus
    reward_sql_referred = f"""
    update profiles
    set referral_bonus = coalesce(referral_bonus, 0) + 2
    where id = '{referred_id}';
    """
    requests.post(
        f"{SUPABASE_URL}/rest/v1/rpc/execute_sql",
        headers=headers,
        json={ "sql": reward_sql_referred }
    )

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
        print(f"[WARN] No profile found for {email}")
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
            print(f"[ERROR] Invalid {table} response: {data}")
            return False
        monthly_count = sum(1 for record in data if record.get("timestamp", "").startswith(current_month))
        return monthly_count < max_limit
    except Exception as e:
        print(f"[ERROR] Failed to parse {table} data: {e}")
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
@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return '', 200

    user_messages = request.json.get("messages", [])
    if not user_messages or not isinstance(user_messages, list):
        return jsonify({ "reply": "Invalid message input." }), 400

    user_prompt = user_messages[-1].get("content", "").strip()
    email = request.json.get("email")
    user_id = request.json.get("user_id", email)

    if not email:
        return jsonify({ "reply": "Login required." }), 401

    is_pro = check_is_pro(email)
    
    # Check chat quota if not pro
    if not is_pro and not check_usage_limit(user_id, "chat"):
        return jsonify({ "reply": "⚠️ Monthly chat limit reached. Upgrade to Pro 💖" })

    ai_reply = generate_yandere_reply(user_prompt)

    # Check if the prompt should trigger image generation
    trigger_keywords = ["show me", "picture", "photo", "image", "see you", "selfie"]
    wants_image = any(keyword in user_prompt.lower() for keyword in trigger_keywords)

    if wants_image:
        prompt = f"{persona['base_prompt']}, scene: {user_prompt}"

        # Check image quota if not pro
        if not is_pro:
            if not check_usage_limit(user_id, "image"):
                return jsonify({ "reply": "⚠️ Monthly image limit reached. Upgrade to Pro 💖" })

            # Sanitize prompt for non-pro users
            prompt = (
                prompt.replace("large boobs", "modest figure")
                      .replace("large butt", "")
                      .replace("seductive pose", "cute pose")
            )

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

    # Record chat usage for non-pro users
    if not is_pro:
        record_usage(user_id, "chat")

    return jsonify({ "reply": ai_reply })

# 🎨 Generate endpoint
@app.route("/generate", methods=["POST", "OPTIONS"])
def generate():
    if request.method == "OPTIONS":
        return '', 200

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


# 📊 Scarcity endpoint
@app.route("/usage", methods=["POST", "OPTIONS"])
def usage():
    if request.method == "OPTIONS":
        return '', 200

    try:
        data = request.get_json(force=True)
        email = data.get("email")
        user_id = data.get("user_id", email)
        referred_by = data.get("referred_by")
        handle_referral(user_id, email, referred_by)
    except Exception as e:
        return jsonify({ "error": f"Invalid JSON: {str(e)}" }), 400

    if not email:
        return jsonify({ "error": "Login required." }), 401

    is_pro = check_is_pro(email)
    bonus_count = 0
    try:
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
        }
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles?select=referral_bonus&email=eq.{email}",
            headers=headers
        )
        profile_data = r.json()
        if profile_data and isinstance(profile_data, list):
            bonus_count = profile_data[0].get("referral_bonus", 0)
    except:
        pass

    image_limit = 9999 if is_pro else 3 + bonus_count
    chat_limit = 9999 if is_pro else 5 + bonus_count

    image_used = count_usage(user_id, "image")
    chat_used = count_usage(user_id, "chat")

    return jsonify({
        "is_pro": is_pro,
        "image_limit": image_limit,
        "chat_limit": chat_limit,
        "image_used": image_used,
        "chat_used": chat_used,
        "image_remaining": max(image_limit - image_used, 0),
        "chat_remaining": max(chat_limit - chat_used, 0),
        "referral_bonus": bonus_count
    })

# 💳 Gumroad Webhook
from datetime import datetime, timedelta

@app.route("/gumroad-webhook", methods=["POST"])
def gumroad_webhook():
    GUMROAD_SELLER_ID = "OvnNGbU5aHwrQvsUdZIksw=="

    payload = request.form
    email = payload.get("email")
    sale_id = payload.get("sale_id")
    product_name = payload.get("product_name")
    seller_id = payload.get("seller_id")

    if seller_id != GUMROAD_SELLER_ID:
        return "Invalid seller_id", 403

    if not email or not sale_id:
        return "Missing fields", 400

    expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }

    profile_payload = {
        "email": email,
        "is_pro": True,
        "pro_expires_at": expires_at
    }

    # UPSERT into profiles
    profile_response = requests.post(
        f"{SUPABASE_URL}/rest/v1/profiles",
        headers={**headers, "Prefer": "resolution=merge-duplicates"},
        json=profile_payload
    )

    # Log purchase
    purchase_response = requests.post(
        f"{SUPABASE_URL}/rest/v1/purchases",
        headers={**headers, "Prefer": "return=minimal"},
        json={
            "email": email,
            "sale_id": sale_id,
            "product_name": product_name or "PossessHer AI Premium"
        }
    )

    if profile_response.status_code in [200, 201, 204]:
        return "User upgraded and purchase logged", 200
    else:
        print("[ERROR] Supabase profile upsert failed:", profile_response.text)
        return "Failed to update profile", 500

# 🚀 Start server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)