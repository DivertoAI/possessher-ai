from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from chat import generate_yandere_reply
from generate import generate_image
from prompts import get_random_prompt
import os
import base64

# ✅ Stronger identity prompt for consistent visuals
persona = {
    "name": "Miyume",
    "base_prompt": (
        "anime girl, pink twin-tail hair, violet eyes, curvy body, large boobs, large butt, beautiful body"
        "intense yandere expression, seductive pose, ultra detailed, high quality, sharp lines"
    )
}

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])

@app.route("/chat", methods=["POST"])
def chat():
    user_messages = request.json.get("messages", [])
    user_prompt = user_messages[-1]["content"]

    ai_reply = generate_yandere_reply(user_prompt)

    # ✅ Check for photo-related triggers in input
    trigger_keywords = ["show me", "picture", "photo", "image", "see you", "selfie"]
    if any(keyword in user_prompt.lower() for keyword in trigger_keywords):
        # ✅ Combine locked persona traits + user context
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

        return jsonify({
            "reply": ai_reply + "\n\n⚠️ But I couldn't find the photo... try again?"
        })

    return jsonify({ "reply": ai_reply })

@app.route("/generate", methods=["POST"])
def generate():
    user_id = request.json.get("user_id", "anon")
    prompt = f"{persona['base_prompt']}, {get_random_prompt()}"
    image_path = generate_image(user_id, prompt)
    return send_file(image_path, mimetype='image/png')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)