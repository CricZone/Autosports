from datetime import datetime, timedelta
import os
from fastapi import FastAPI
import pytz
import requests

app = FastAPI()

# ==================== [CONFIGURATIONS & SECRETS] ====================
BOT_TOKEN = os.getenv(
    "BOT_TOKEN", "8871134392:AAFU4CAjCd380AqopflGw88JqfvdrvW_ooU"
)
FOOTBALL_API_KEY = os.getenv(
    "FOOTBALL_API_KEY", "4f31e3c49b6b4d30a630068bd0545209"
)
CUSTOM_SECRET_API = os.getenv("CUSTOM_SECRET_API", "")

CHANNEL_BDSTREAM = "@bdstreamhub00"
CHANNEL_DLSPORTS = "@DlSportsTv"

# অ্যাপ ডাউনলোড লিংক (মেসেজে হাইপারলিংক আকারে লুকানো থাকবে)
APK_BDSTREAM = "https://bdstreamhub-api.hasanvaibd009.workers.dev/"
APK_DLSPORTS = (
    "https://github.com/dlspapk/dlsportstv/raw/refs/heads/main/dlsportstv2.0.apk"
)

# হাই-ভোল্টেজ বড় ক্লাব ও দেশের তালিকা (ফুটবল, ক্রিকেট, বেসবল)
HIGH_VOLTAGE_ENTITIES = [
    # Football
    "Real Madrid",
    "Barcelona",
    "Manchester City",
    "Liverpool",
    "Arsenal",
    "Manchester United",
    "Chelsea",
    "Bayern Munich",
    "PSG",
    "Paris Saint-Germain",
    "Inter",
    "AC Milan",
    "Juventus",
    "Atlético Madrid",
    "Al Nassr",
    "Al Hilal",
    "Dortmund",
    "Tottenham",
    "Napoli",
    # Cricket Countries
    "Bangladesh",
    "India",
    "Pakistan",
    "Australia",
    "England",
    "South Africa",
    "New Zealand",
    # Baseball Top Franchises
    "Yankees",
    "Dodgers",
    "Red Sox",
    "Astros",
]


# ==================== [MATCH FETCHER] ====================
def fetch_high_voltage_matches():
  matches = []

  # ১. কাস্টম API চেক (যদি Render Environment-এ থাকে)
  if CUSTOM_SECRET_API:
    try:
      res = requests.get(CUSTOM_SECRET_API, timeout=10)
      custom_data = res.json()
      # যদি API সরাসরি লিস্ট দেয় বা matches কি-তে থাকে
      raw_list = (
          custom_data
          if isinstance(custom_data, list)
          else custom_data.get("matches", [])
      )

      for item in raw_list:
        t1 = item.get("team1") or item.get("home_team") or item.get("home")
        t2 = item.get("team2") or item.get("away_team") or item.get("away")
        sport = item.get("sport", "Sports").capitalize()
        time_bst = item.get("time_bst") or item.get("time", "Tonight")

        # হাই ভোল্টেজ ফিল্টার
        if any(
            h.lower() in str(t1).lower() or h.lower() in str(t2).lower()
            for h in HIGH_VOLTAGE_ENTITIES
        ):
          matches.append({
              "sport": sport,
              "league": item.get("league", sport),
              "team1": t1,
              "team2": t2,
              "time_bst": time_bst,
          })
      if matches:
        return matches[:8]  # মেসেজ ছোট ও ১ পেজে রাখার জন্য সেরা ৮টি ম্যাচ
    except Exception as e:
      print(f"Custom API Error: {e}")

  # ২. ব্যাকআপ Football-Data API (ফুটবল ম্যাচ)
  headers = {"X-Auth-Token": FOOTBALL_API_KEY}
  today = datetime.now(pytz.utc).date()
  tomorrow = today + timedelta(days=1)
  url = f"https://api.football-data.org/v4/matches?dateFrom={today}&dateTo={tomorrow}"

  try:
    res = requests.get(url, headers=headers, timeout=10)
    data = res.json()

    if "matches" in data:
      for m in data["matches"]:
        t1 = m["homeTeam"]["name"]
        t2 = m["awayTeam"]["name"]
        comp = m["competition"]["name"]

        is_top_team = any(
            team.lower() in t1.lower() or team.lower() in t2.lower()
            for team in HIGH_VOLTAGE_ENTITIES
        )
        is_top_comp = comp in ["UEFA Champions League", "Premier League"]

        if is_top_team or is_top_comp:
          utc_time = datetime.fromisoformat(
              m["utcDate"].replace("Z", "+00:00")
          )
          bst_time = utc_time.astimezone(pytz.timezone("Asia/Dhaka")).strftime(
              "%I:%M %p"
          )

          matches.append({
              "sport": "Football",
              "league": comp,
              "team1": t1,
              "team2": t2,
              "time_bst": bst_time,
          })
  except Exception as e:
    print(f"Football-Data API Error: {e}")

  return matches[:7]  # সর্বোচ্চ ৭-৮ টি বড় ম্যাচ


# ==================== [CLEAN & COMPACT MESSAGE BUILDER] ====================
def build_compact_message(brand_name, brand_handle, download_url):
  matches = fetch_high_voltage_matches()

  if not matches:
    return None

  # ১ পেজের কম্প্যাক্ট ও প্রিমিয়াম ডিজাইন
  msg = "🔥 <b>TODAY'S BLOCKBUSTER MATCHES</b> ✨\n"
  msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"

  current_cat = ""
  for m in matches:
    cat_title = m.get("league", m.get("sport", "Sports"))
    if cat_title != current_cat:
      current_cat = cat_title
      msg += f"🏆 <b>{current_cat.upper()}</b>\n"

    msg += f"Ⓜ️ <b>{m['team1']} 🆚 {m['team2']}</b>\n"
    msg += f"⏰ <b>Time:</b> {m['time_bst']} (BD Time)\n\n"

  msg += "━━━━━━━━━━━━━━━━━━━━━\n"
  msg += "📺 <b>Watch Live on App:</b>\n"
  msg += f"👉 <b><a href='{download_url}'>Click Here To Download App</a></b>\n\n"
  msg += f"🔰 <b>{brand_name}</b> ✨\n"
  msg += f"📢 Channel: {brand_handle}"

  return msg


def send_telegram(chat_id, text):
  url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
  payload = {
      "chat_id": chat_id,
      "text": text,
      "parse_mode": "HTML",
      "disable_web_page_preview": True,
  }
  return requests.post(url, json=payload, timeout=10)


# ==================== [ENDPOINTS] ====================
@app.get("/")
def home():
  return {"status": "Sports Notice Bot Running Smoothly"}


@app.get("/trigger-schedule")
def trigger_daily_notice():
  # ১. BDStreamHub নোটিশ
  msg_bd = build_compact_message("BDSTREAMHUB", "@bdstreamhub00", APK_BDSTREAM)
  res_bd = None
  if msg_bd:
    res_bd = send_telegram(CHANNEL_BDSTREAM, msg_bd).json()

  # ২. DLSports নোটিশ
  msg_dl = build_compact_message("DLSPORTS", "@DlSportsTv", APK_DLSPORTS)
  res_dl = None
  if msg_dl:
    res_dl = send_telegram(CHANNEL_DLSPORTS, msg_dl).json()

  return {
      "success": True if (msg_bd or msg_dl) else False,
      "BDStreamHub_Status": res_bd,
      "DLSports_Status": res_dl,
  }
