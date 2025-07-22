from flask import Flask, request, jsonify, send_file
from chat import generate_yandere_reply
from generate import generate_image
from prompts import get_random_prompt

app = Flask(__name__)

@app.route("/chat", methods=["POST"])
def chat():
    user_messages = request.json.get("messages")
    prompt = user_messages[-1]["content"]
    ai_reply = generate_yandere_reply(prompt)
    return jsonify({"reply": ai_reply})

@app.route("/generate", methods=["POST"])
def generate():
    user_id = request.json.get("user_id", "anon")
    prompt = get_random_prompt()
    image_path = generate_image(user_id, prompt)
    return send_file(image_path, mimetype='image/png')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)