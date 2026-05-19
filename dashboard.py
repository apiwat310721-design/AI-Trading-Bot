"""Flask dashboard entry point for the XAUUSD AI Trading Agent."""

from __future__ import annotations

from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template

from price_feed import get_market_data
from trading_agent import XAUUSDAgent, get_signal_history

load_dotenv()

app = Flask(__name__)
agent = XAUUSDAgent()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/price")
def api_price():
    data = get_market_data()
    data["server_time"] = datetime.now(timezone.utc).isoformat()
    return jsonify(data)


@app.get("/api/signal")
def api_signal():
    market_data = get_market_data()
    signal = agent.analyze(market_data)
    signal["history"] = get_signal_history()
    return jsonify(signal)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
