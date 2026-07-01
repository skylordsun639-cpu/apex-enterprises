import os
import time
import logging
import stripe
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REQUIRED = ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "STRIPE_WEBHOOK_SECRET", "PRICE_ID", "WEBHOOK_URL", "FLASK_SECRET_KEY"]
for v in REQUIRED:
    if not os.getenv(v):
        raise RuntimeError(f"Missing {v}")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
PRICE_ID = os.getenv("PRICE_ID")
order_store = {}
rate_limit = {}

def is_rate_limited():
    ip = request.remote_addr
    now = time.time()
    if ip not in rate_limit:
        rate_limit[ip] = {"count": 0, "timestamp": now}
    data = rate_limit[ip]
    if now - data["timestamp"] > 60:
        data["count"] = 0
        data["timestamp"] = now
    if data["count"] >= 10:
        return True
    data["count"] += 1
    return False

@app.route("/")
def home():
    return render_template("index.html", price_id=PRICE_ID)

@app.route("/create-checkout", methods=["POST"])
def create_checkout():
    if is_rate_limited():
        return jsonify({"error": "Too many requests"}), 429
    data = request.get_json() or {}
    topic = data.get("topic", "").strip()
    length = data.get("length", "").strip()
    tone = data.get("tone", "").strip()
    if not all([topic, length, tone]):
        return jsonify({"error": "All fields required"}), 400
    try:
        length = int(length)
        if length <= 0: raise ValueError
    except:
        return jsonify({"error": "Length must be positive number"}), 400

    session = stripe.checkout.sessions.create(
        payment_method_types=["card"],
        line_items=[{"price": PRICE_ID, "quantity": 1}],
        mode="payment",
        success_url=os.getenv("WEBHOOK_URL") + "/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=os.getenv("WEBHOOK_URL") + "/cancel",
        metadata={"topic": topic, "length": str(length), "tone": tone}
    )
    order_store[session.id] = {"topic": topic, "length": length, "tone": tone}
    return jsonify({"url": session.url})

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        event = stripe.Webhook.construct_event(request.data, request.headers.get("Stripe-Signature"), os.getenv("STRIPE_WEBHOOK_SECRET"))
    except:
        return "Invalid", 400
    if event["type"] == "checkout.session.completed":
        sid = event["data"]["object"].id
        order = order_store.get(sid)
        if order:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat = os.getenv("TELEGRAM_CHAT_ID")
            msg = f"New order!\nTopic: {order['topic']}\nLength: {order['length']}\nTone: {order['tone']}"
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat, "text": msg})
    return "", 200

@app.route("/success")
def success():
    return render_template("success.html", order=order_store.get(request.args.get("session_id"), {}))

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
