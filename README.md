# XAUUSD AI Trading Agent

A Flask dashboard for monitoring XAUUSD (Gold/USD), calculating technical indicators from free `yfinance` data, and generating Claude AI trading signals.

## English setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd AI-Trading-Bot
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Add your Anthropic key to `.env`:
   ```env
   ANTHROPIC_API_KEY=your_api_key_here
   ```
4. Start the dashboard:
   ```bash
   python dashboard.py
   ```
5. Open http://localhost:5000 in your browser.

The app uses `yfinance` symbol `XAUUSD=X` with 5-minute candles for the last 5 days. Price data refreshes every 30 seconds, and Claude AI signal analysis refreshes every 5 minutes to reduce API costs.

## คำแนะนำการติดตั้งภาษาไทย

1. โคลนโปรเจกต์:
   ```bash
   git clone <repository-url>
   cd AI-Trading-Bot
   ```
2. ติดตั้งไลบรารีที่จำเป็น:
   ```bash
   pip install -r requirements.txt
   ```
3. เพิ่ม Anthropic API key ในไฟล์ `.env`:
   ```env
   ANTHROPIC_API_KEY=your_api_key_here
   ```
4. เปิดใช้งานแดชบอร์ด:
   ```bash
   python dashboard.py
   ```
5. เปิดเว็บเบราว์เซอร์ที่ http://localhost:5000

ระบบดึงข้อมูล XAUUSD ฟรีผ่าน `yfinance` ไม่ต้องใช้ paid data feed และยังสามารถเปิด Flask ได้แม้ยังไม่ได้ใส่ API key จริง โดย AI signal จะแสดงสถานะ WAIT พร้อมข้อความแจ้งเตือน

## Files

- `price_feed.py` - Fetches XAUUSD data and calculates RSI, MACD, Bollinger Bands, SMA 50/200, 24h price change, support, and resistance.
- `trading_agent.py` - Sends formatted market context to Claude and parses BUY / SELL / WAIT signals.
- `dashboard.py` - Flask app with `/`, `/api/price`, and `/api/signal` routes.
- `templates/index.html` and `static/style.css` - Dark responsive trading dashboard UI.

## Notes

This project is for educational and research purposes. Trading gold involves significant risk; always validate signals with your own risk management process.
