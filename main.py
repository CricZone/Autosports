from datetime import datetime, timedelta
import os
from fastapi import FastAPI
import pytz
import requests

app = FastAPI()

# ==================== [CONFIGURATIONS & HIDDEN SECRETS] ====================
# Render-এর গোপন ভেরিয়েবল থেকে ডেটা নেওয়া হবে
BOT_TOKEN = os.getenv("BOT_TOKEN", "8871134392:AAFU4CAjCd380AqopflGw88JqfvdrvW_ooU")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "4f31e3c49b6b4d30a630068bd0545209")
CUSTOM_SECRET_API = os.getenv("CUSTOM_SECRET_API", "")

# চ্যানেল ইউজারনেম
CHANNEL_BDSTREAM = "@bdstreamhub00"
CHANNEL_DLSPORTS = "@DlSportsTv"

STREAM_BASE_URL = "https://www.footem.co.uk"

# জনপ্রিয় ক্লাব তালিকা
POPULAR_TEAMS = [
    "Real Madrid", "Barcelona", "Manchester City", "Liverpool", "Arsenal",
    "Manchester United", "Chelsea", "Bayern Munich", "PSG", "Paris Saint-Germain",
    "Inter", "Milan", "Juventus", "Atlético Madrid", "Al Nassr", "Al Hilal",
    "Dortmund", "Tottenham", "Feyenoord", "Napoli", "Leeds"
]


# ==================== [MATCH FETCHING] ====================
def fetch_top_football_matches():
    matches = []
    
    # ১. আপনার কাস্টম গোপন API থাকলে সেখান থেকে ডেটা আনা
    if CUSTOM_SECRET_API:
        try:
            res = requests.get(CUSTOM_SECRET_API, timeout=10)
            custom_data = res.json()
            # কাস্টম ডেটা থেকে সরাসরি ম্যাচ লিস্ট পাওয়া গেলে
            if isinstance(custom_data, list):
                return custom_data
        except Exception as e:
            print(f"Custom API Error: {e}")

    # ২. Football-Data API ব্যাকআপ
    headers = {'X-Auth-Token': FOOTBALL_API_KEY}
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
                
                is_top_comp = comp in ["UEFA Champions League", "Premier League", "Primera Division", "Serie A"]
                is_top_team = any(team.lower() in t1.lower() or team.lower() in t2.lower() for team in POPULAR_TEAMS)
                
                if is_top_comp or is_top_team:
                    utc_time = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
                    bst_time = utc_time.astimezone(pytz.timezone("Asia/Dhaka")).strftime("%I:%M %p")
                    ind_time = utc_time.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%I:%M %p")
                    uae_time = utc_time.astimezone(pytz.timezone("Asia/Dubai")).strftime("%I:%M %p")
                    
                    match_slug = f"{t1.lower().replace(' ', '-')}-vs-{t2.lower().replace(' ', '-')}"
                    stream_link = f"https://em.scoreium.com/2026/09/{match_slug}.html"
                    
                    matches.append({
                        "team1": t1,
                        "team2": t2,
                        "league": comp,
                        "time_bst": bst_time,
                        "time_ind": ind_time,
                        "time_uae": uae_time,
                        "link": stream_link
                    })
    except Exception as e:
        print(f"Error: {e}")
        
    return matches


# ==================== [MESSAGE TEMPLATE] ====================
def build_message(brand_name, brand_handle):
    matches = fetch_top_football_matches()
    
    if not matches:
        return None
        
    msg = "🔥 <b>MATCH DAY | LIVE</b> ✨\n\n"
    
    current_league = ""
    for m in matches:
        league_name = m.get("league", "Top Fixture")
        if league_name != current_league:
            current_league = league_name
            msg += f"🏆 <b>{current_league}</b>\n\n"
            
        msg += f"Ⓜ️ <b>{m['team1']} 🆚 {m['team2']}</b>\n"
        msg += f"📅 Tonight\n"
        msg += f"🇧🇩 BST | {m.get('time_bst', 'TBA')}\n"
        msg += f"🇮🇳 IND | {m.get('time_ind', 'TBA')}\n"
        if 'time_uae' in m:
            msg += f"🇦🇪 UAE | {m['time_uae']}\n"
        msg += f"📺 Live Link\n"
        msg += f"👉 {m.get('link', STREAM_BASE_URL)}\n"
        msg += f"👉 {STREAM_BASE_URL}\n\n"
        
    msg += f"🔰 <b>{brand_name}</b> ✨\n"
    msg += f"📢 {brand_handle}"
    
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
    return {"status": "Bot server is running"}


@app.get("/trigger-schedule")
def trigger_daily_notice():
    msg_bd = build_message("BDSTREAMHUB", "@bdstreamhub00")
    msg_dl = build_message("DLSPORTS", "@DlSportsTv")
    
    res_bd = None
    res_dl = None
    
    if msg_bd:
        res_bd = send_telegram(CHANNEL_BDSTREAM, msg_bd).json()
    if msg_dl:
        res_dl = send_telegram(CHANNEL_DLSPORTS, msg_dl).json()
        
    return {
        "found_matches": True if (msg_bd or msg_dl) else False,
        "BDStreamHub_Result": res_bd,
        "DLSports_Result": res_dl
    }
