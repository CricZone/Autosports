import os
import traceback
from datetime import datetime, timedelta
from fastapi import FastAPI
import pytz
import requests

app = FastAPI()

# ==================== [CONFIGURATIONS & SECRETS] ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8871134392:AAFU4CAjCd380AqopflGw88JqfvdrvW_ooU")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "4f31e3c49b6b4d30a630068bd0545209")
CUSTOM_SECRET_API = os.getenv("CUSTOM_SECRET_API", "")

CHANNEL_BDSTREAM = "@bdstreamhub00"
CHANNEL_DLSPORTS = "@DlSportsTv"

APK_BDSTREAM = "https://bdstreamhub-api.hasanvaibd009.workers.dev/"
APK_DLSPORTS = "https://github.com/dlspapk/dlsportstv/raw/refs/heads/main/dlsportstv2.0.apk"

# হাই-ভোল্টেজ দল ও টুর্নামেন্ট ফিল্টার
HIGH_VOLTAGE_TEAMS = [
    # Cricket
    "Bangladesh", "India", "Pakistan", "Australia", "England", "South Africa",
    "New Zealand", "Sri Lanka", "Afghanistan", "West Indies",
    # Football
    "Real Madrid", "Barcelona", "Manchester City", "Liverpool", "Arsenal",
    "Manchester United", "Chelsea", "Bayern", "PSG", "Paris", "Inter",
    "Milan", "Juventus", "Atlético", "Al Nassr", "Al Hilal", "Dortmund",
    "Tottenham", "Napoli", "Leeds", "Feyenoord",
    # Baseball
    "Yankees", "Dodgers", "Red Sox", "Astros"
]


# ==================== [DATA FETCHERS] ====================

def fetch_custom_api_matches():
    """আপনার গোপন API থেকে সব ধরনের খেলা আনার নিরাপদ মেথড"""
    matches = []
    if not CUSTOM_SECRET_API:
        return matches

    try:
        res = requests.get(CUSTOM_SECRET_API, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        data = res.json()
        
        raw_list = []
        if isinstance(data, list):
            raw_list = data
        elif isinstance(data, dict):
            for k in ["matches", "data", "fixtures", "events", "results", "games"]:
                if k in data and isinstance(data[k], list):
                    raw_list = data[k]
                    break

        for item in raw_list:
            if not isinstance(item, dict):
                continue

            # যেকোনো নামে থাকা দলের নাম খুঁজে নেওয়া
            t1 = item.get("team1") or item.get("home_team") or item.get("home") or item.get("t1") or item.get("teamA") or ""
            t2 = item.get("team2") or item.get("away_team") or item.get("away") or item.get("t2") or item.get("teamB") or ""
            sport = str(item.get("sport") or item.get("game") or item.get("category") or "").strip().title()
            league = str(item.get("league") or item.get("tournament") or item.get("series") or sport or "Special Match").strip()
            time_val = item.get("time_bst") or item.get("time") or item.get("match_time") or "Tonight"

            if not sport:
                sport = "Cricket" if any(c in f"{t1} {t2} {league}".lower() for c in ["t20", "odi", "ipl", "bpl", "asia cup", "icc"]) else "Football"

            combined = f"{t1} {t2} {league}".lower()
            is_top = any(name.lower() in combined for name in HIGH_VOLTAGE_TEAMS)

            if is_top or len(raw_list) <= 6:
                matches.append({
                    "sport": sport,
                    "league": league,
                    "team1": str(t1),
                    "team2": str(t2),
                    "time_bst": str(time_val)
                })
    except Exception as e:
        print(f"Custom API Read Error: {e}")

    return matches


def fetch_backup_cricket_matches():
    """পাবলিক লাইভ ক্রিকেট ফিড থেকে বড় বড় ম্যাচ আনার ব্যাকআপ"""
    cricket_matches = []
    try:
        url = "https://api.cricapi.com/v1/currentMatches?apikey=sample_or_free_key" # ফ্রি পাবলিক ফিড
        res = requests.get(url, timeout=5)
        data = res.json()
        if "data" in data:
            for c in data["data"]:
                name = c.get("name", "")
                if any(team.lower() in name.lower() for team in HIGH_VOLTAGE_TEAMS):
                    teams = c.get("teams", [])
                    t1 = teams[0] if len(teams) > 0 else "Team A"
                    t2 = teams[1] if len(teams) > 1 else "Team B"
                    cricket_matches.append({
                        "sport": "Cricket",
                        "league": c.get("matchType", "International").upper(),
                        "team1": t1,
                        "team2": t2,
                        "time_bst": "Live / Today"
                    })
    except Exception:
        pass
    return cricket_matches


def fetch_backup_football_matches():
    """Football-Data API ব্যাকআপ"""
    football_matches = []
    try:
        headers = {'X-Auth-Token': FOOTBALL_API_KEY}
        today = datetime.now(pytz.utc).date()
        tomorrow = today + timedelta(days=1)
        url = f"https://api.football-data.org/v4/matches?dateFrom={today}&dateTo={tomorrow}"

        res = requests.get(url, headers=headers, timeout=8)
        data = res.json()

        if "matches" in data:
            for m in data["matches"]:
                t1 = m["homeTeam"]["name"]
                t2 = m["awayTeam"]["name"]
                comp = m["competition"]["name"]

                is_top = any(h.lower() in t1.lower() or h.lower() in t2.lower() for h in HIGH_VOLTAGE_TEAMS)
                if comp in ["UEFA Champions League", "Premier League"] or is_top:
                    utc_time = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
                    bst_time = utc_time.astimezone(pytz.timezone("Asia/Dhaka")).strftime("%I:%M %p")
                    football_matches.append({
                        "sport": "Football",
                        "league": comp,
                        "team1": t1,
                        "team2": t2,
                        "time_bst": bst_time
                    })
    except Exception as e:
        print(f"Football API Error: {e}")

    return football_matches


# ==================== [MESSAGE BUILDER] ====================
def build_compact_message(brand_name, brand_handle, download_url):
    # ১. প্রথমে কাস্টম API চেক
    all_matches = fetch_custom_api_matches()

    # ২. কাস্টম API ফাঁকা থাকলে ব্যাকআপ ক্রিকেট ও ফুটবল একসাথে যুক্ত করা
    if not all_matches:
        all_matches.extend(fetch_backup_cricket_matches())
        all_matches.extend(fetch_backup_football_matches())

    if not all_matches:
        return None

    # ১ পৃষ্ঠার কমপ্যাক্ট মেসেজ ফরম্যাট
    msg = "🔥 <b>TODAY'S BLOCKBUSTER MATCHES</b> ✨\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"

    # খেলাগুলো সাজিয়ে নেওয়া
    for m in all_matches[:7]:
        category_header = m.get("league") or m.get("sport")
        msg += f"🏆 <b>{category_header.upper()}</b>\n"
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
        "disable_web_page_preview": True
    }
    return requests.post(url, json=payload, timeout=10)


# ==================== [API ENDPOINTS] ====================
@app.get("/")
def home():
    return {"status": "Bot server is running fine"}


@app.get("/trigger-schedule")
def trigger_daily_notice():
    try:
        msg_bd = build_compact_message("BDSTREAMHUB", "@bdstreamhub00", APK_BDSTREAM)
        msg_dl = build_compact_message("DLSPORTS", "@DlSportsTv", APK_DLSPORTS)

        res_bd = None
        res_dl = None

        if msg_bd:
            res_bd = send_telegram(CHANNEL_BDSTREAM, msg_bd).json()
        if msg_dl:
            res_dl = send_telegram(CHANNEL_DLSPORTS, msg_dl).json()

        return {
            "status": "Success",
            "matches_found": True if (msg_bd or msg_dl) else False,
            "BDStreamHub_Result": res_bd,
            "DLSports_Result": res_dl
        }
    except Exception as e:
        return {
            "status": "Error Handled",
            "error_detail": str(e),
            "trace": traceback.format_exc()
        }
