from datetime import datetime
from fastapi import FastAPI
import pytz
import requests

app = FastAPI()

# ==================== [CONFIGURATIONS] ====================
BOT_TOKEN = "8871134392:AAFU4CAjCd380AqopflGw88JqfvdrvW_ooU"
FOOTBALL_API_KEY = "4f31e3c49b6b4d30a630068bd0545209"

# আপডেট করা চ্যানেল ইউজারনেম
CHANNEL_BDSTREAM = "@bdstreamhub00"
CHANNEL_DLSPORTS = "@DLSports"

STREAM_BASE_URL = "https://www.footem.co.uk"

# হাই-ভোল্টেজ বড় দলগুলোর তালিকা
TOP_TEAMS = [
    "Real Madrid",
    "Barcelona",
    "Manchester City",
    "Liverpool",
    "Arsenal",
    "Manchester United",
    "Chelsea",
    "Bayern Munich",
    "Paris Saint-Germain",
    "PSG",
    "Inter Milan",
    "AC Milan",
    "Juventus",
    "Atlético Madrid",
    "Al Nassr",
    "Al Hilal",
    "Borussia Dortmund",
    "Tottenham Hotspur",
]


# ==================== [MATCH FETCHING] ====================
def fetch_top_football_matches():
  headers = {"X-Auth-Token": FOOTBALL_API_KEY}
  today_str = datetime.now(pytz.utc).strftime("%Y-%m-%d")
  url = f"https://api.football-data.org/v4/matches?dateFrom={today_str}&dateTo={today_str}"

  matches = []
  try:
    res = requests.get(url, headers=headers, timeout=10)
    data = res.json()

    if "matches" in data:
      for m in data["matches"]:
        t1 = m["homeTeam"]["name"]
        t2 = m["awayTeam"]["name"]
        comp = m["competition"]["name"]

        # হাই-ভোল্টেজ ম্যাচ ফিল্টারিং
        is_top_match = any(
            team.lower() in t1.lower() or team.lower() in t2.lower()
            for team in TOP_TEAMS
        )
        if comp in ["UEFA Champions League"] or is_top_match:
          utc_time = datetime.fromisoformat(
              m["utcDate"].replace("Z", "+00:00")
          )
          ind_time = utc_time.astimezone(
              pytz.timezone("Asia/Kolkata")
          ).strftime("%I:%M %p")
          bst_time = utc_time.astimezone(pytz.timezone("Asia/Dhaka")).strftime(
              "%I:%M %p"
          )

          matches.append({
              "team1": t1,
              "team2": t2,
              "league": comp,
              "time_ind": ind_time,
              "time_bst": bst_time,
              "link": STREAM_BASE_URL,
          })
  except Exception as e:
    print(f"Error fetching matches: {e}")

  return matches


# ==================== [MESSAGE TEMPLATE] ====================
def build_message(brand_name, brand_handle):
  matches = fetch_top_football_matches()

  if not matches:
    return None

  msg = "🔥 <b>MATCH DAY | LIVE</b> ✨\n\n"

  current_league = ""
  for m in matches:
    if m["league"] != current_league:
      current_league = m["league"]
      msg += f"🏆 <b>{current_league}</b>\n\n"

    msg += f"Ⓜ️ <b>{m['team1']}</b> 🆚 <b>{m['team2']}</b>\n"
    msg += "📅 Tonight\n"
    msg += f"🇧🇩 BST | {m['time_bst']}\n"
    msg += f"🇮🇳 IND | {m['time_ind']}\n"
    msg += "📺 Live Link\n"
    msg += f"👉 {m['link']}\n\n"

  # শুধু নির্দিষ্ট চ্যানেলের ব্র্যান্ডিং
  msg += f"🔰 <b>{brand_name}</b> ✨\n"
  msg += f"📢 {brand_handle}"

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


# ==================== [API ENDPOINTS] ====================
@app.get("/")
def home():
  return {"status": "Bot server is running"}


@app.get("/trigger-schedule")
def trigger_daily_notice():
  # BDStreamHub নোটিশ
  msg_bd = build_message("BDStreamHub", "@bdstreamhub00")
  res_bd = None
  res_dl = None

  if not msg_bd:
    # আজ কোনো হাই-ভোল্টেজ ম্যাচ না পেলে একটি টেস্ট নোটিশ পাঠাবে
    test_msg_bd = (
        "🔥 <b>TODAY'S FIXTURE UPDATE</b> ✨\n\n"
        "No high-voltage match scheduled for today.\n\n"
        "🔰 <b>BDStreamHub</b> ✨\n📢 @bdstreamhub00"
    )
    test_msg_dl = (
        "🔥 <b>TODAY'S FIXTURE UPDATE</b> ✨\n\n"
        "No high-voltage match scheduled for today.\n\n"
        "🔰 <b>DLSports</b> ✨\n📢 @DLSports"
    )
    res_bd = send_telegram(CHANNEL_BDSTREAM, test_msg_bd).json()
    res_dl = send_telegram(CHANNEL_DLSPORTS, test_msg_dl).json()
  else:
    msg_dl = build_message("DLSports", "@DLSports")
    res_bd = send_telegram(CHANNEL_BDSTREAM, msg_bd).json()
    res_dl = send_telegram(CHANNEL_DLSPORTS, msg_dl).json()

  return {"BDStreamHub_Result": res_bd, "DLSports_Result": res_dl}
