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

HIGH_VOLTAGE_ENTITIES = [
    # Football Clubs
    "Real Madrid", "Barcelona", "Manchester City", "Liverpool", "Arsenal",
    "Manchester United", "Chelsea", "Bayern", "PSG", "Paris", "Inter",
    "Milan", "Juventus", "Atlético", "Al Nassr", "Al Hilal", "Dortmund",
    "Tottenham", "Napoli", "Leeds", "Feyenoord",
    # Cricket Teams
    "Bangladesh", "India", "Pakistan", "Australia", "England", "South Africa",
    "New Zealand", "Sri Lanka", "Afghanistan",
    # Baseball
    "Yankees", "Dodgers", "Red Sox", "Astros"
]


# ==================== [SAFE DATA FETCHER] ====================
def fetch_high_voltage_matches():
    matches = []

    # ১. গোপন কাস্টম API চেক (Error-proof)
    if CUSTOM_SECRET_API:
        try:
            res = requests.get(CUSTOM_SECRET_API, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            custom_data = res.json()
            
            raw_list = []
            if isinstance(custom_data, list):
                raw_list = custom_data
            elif isinstance(custom_data, dict):
                for key in ["matches", "data", "fixtures", "events", "results"]:
                    if key in custom_data and isinstance(custom_data[key], list):
                        raw_list = custom_data[key]
                        break

            for item in raw_list:
                if not isinstance(item, dict):
                    continue
                
                t1 = item.get("team1") or item.get("home_team") or item.get("home") or item.get("team_a") or item.get("t1") or ""
                t2 = item.get("team2") or item.get("away_team") or item.get("away") or item.get("team_b") or item.get("t2") or ""
                sport = item.get("sport") or item.get("game") or item.get("category") or "Match"
                time_val = item.get("time_bst") or item.get("time") or item.get("match_time") or item.get("time_ind") or "Tonight"
                league = item.get("league") or item.get("tournament") or item.get("event") or sport

                # হাই-ভোল্টেজ চেক
                combined_text = f"{t1} {t2} {league}".lower()
                is_top = any(entity.lower() in combined_text for entity in HIGH_VOLTAGE_ENTITIES)

                if is_top or len(raw_list) <= 6:
                    matches.append({
                        "league": str(league),
                        "team1": str(t1),
                        "team2": str(t2),
                        "time_bst": str(time_val)
                    })

            if matches:
                return matches[:8]
        except Exception as e:
            print(f"Custom API Fetch Failed: {e}")

    # ২. ব্যাকআপ Football-Data API
    try:
        headers = {'X-Auth-Token': FOOTBALL_API_KEY}
        today = datetime.now(pytz.utc).date()
        tomorrow = today + timedelta(days=1)
        url = f"https://api.football-data.org/v4/matches?dateFrom={today}&dateTo={tomorrow}"
        
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        
        if "matches" in data:
            for m in data["matches"]:
                t1 = m["homeTeam"]["name"]
                t2 = m["awayTeam"]["name"]
                comp = m["competition"]["name"]
                
                is_top = any(h.lower() in t1.lower() or h.lower() in t2.lower() for h in HIGH_VOLTAGE_ENTITIES)
                if comp in ["UEFA Champions League", "Premier League"] or is_top:
                    utc_time = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
                    bst_time = utc_time.astimezone(pytz.timezone("Asia/Dhaka")).strftime("%I:%M %p")
                    matches.append({
                        "league": comp,
                        "team1": t1,
                        "team2": t2,
                        "time_bst": bst_time
                    })
    except Exception as e:
        print(f"Backup API Failed: {e}")
        
    return matches[:8]


# ==================== [MESSAGE BUILDER] ====================
def build_compact_message(brand_name, brand_handle, download_url):
    matches = fetch_high_voltage_matches()
    
    if not matches:
        return None
        
    msg = "🔥 <b>TODAY'S BLOCKBUSTER MATCHES</b> ✨\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    current_cat = ""
    for m in matches:
        cat_title = m.get("league", "SPORTS")
        if cat_title != current_cat:
            current_cat = cat_title
            msg += f"🏆 <b>{current_cat.upper()}</b>\n"
            
        msg += f"Ⓜ️ <b>{m['team1']} 🆚 {m['team2']}</b>\n"
        msg += f"⏰ <b>Time:</b> {m['time_bst']} (BD Time)\n\n"
        
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📺 <b>Watch Live on App:</b>\n"
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


# ==================== [ENDPOINTS] ====================
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
