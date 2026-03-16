#!/usr/bin/env python3
"""
Kagura / AirdropsQuest - Auto Mission & Daily Claim (Multi-Account)
Reads cookies from cookies.txt (one per line)
Automatically claims daily login and completes all available tasks.
Skips/hides finished missions.
"""

import requests
import json
import time
import sys
import os
from datetime import datetime

# ============================================================
# Check file
# ============================================================
COOKIE_FILE = "cookies.txt"

if not os.path.exists(COOKIE_FILE):
    print(f"File {COOKIE_FILE} not found! Creating an empty one.")
    with open(COOKIE_FILE, "w") as f:
        f.write("# Paste your Kagura/AirdropsQuest cookies here, one per line.\n")
    print(f"Please add your cookies (JWT strings) into {COOKIE_FILE} and run again.")
    sys.exit(1)

# Read cookies, ignore empty lines and comments
with open(COOKIE_FILE, "r") as f:
    COOKIES = [line.strip() for line in f if line.strip() and not line.startswith("#")]

if not COOKIES:
    print(f"No cookies found in {COOKIE_FILE}. Please add at least one cookie.")
    sys.exit(1)

BASE_URL = "https://airdropsquest.com/api/trpc"

def get_headers(cookie_val):
    return {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.5",
        "content-type": "application/json",
        "origin": "https://airdropsquest.com",
        "referer": "https://airdropsquest.com/profile",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "cookie": f"__Host-app_session_id={cookie_val}; app_session_id={cookie_val}",
    }

# ============================================================
# Colors
# ============================================================
G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; C = "\033[96m"; M = "\033[95m"; B = "\033[1m"; X = "\033[0m"

def log(msg, color=C):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{B}[{ts}]{X} {color}{msg}{X}", flush=True)

def log_ok(msg):  log(f"✅ {msg}", G)
def log_err(msg): log(f"❌ {msg}", R)
def log_info(msg): log(f"ℹ️  {msg}", C)
def log_warn(msg): log(f"⚠️  {msg}", Y)
def log_task(msg): log(f"🎯 {msg}", M)


# ============================================================
# API Functions
# ============================================================
def check_auth(headers):
    url = f"{BASE_URL}/auth.me?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%7D%7D"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        data = resp.json()
        result = data[0]
        if "result" in result:
            user = result["result"]["data"]["json"]
            if user:
                return user
        return None
    except Exception as e:
        return None

def get_participant(headers):
    url = f"{BASE_URL}/quest.getMyParticipant?batch=1&input=%7B%220%22%3A%7B%22json%22%3A%7B%7D%7D%7D"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        data = resp.json()
        result = data[0]
        if "result" in result:
            return result["result"]["data"]["json"]
    except:
        pass
    return None

def claim_daily(headers, participant_id):
    """Claim daily login reward using quest.claimDailyLoginBonus"""
    url = f"{BASE_URL}/quest.claimDailyLoginBonus?batch=1"
    payload = {"0": {"json": {"participantId": participant_id}}}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        data = resp.json()
        result = data[0]
        if "result" in result:
            res_data = result["result"]["data"]["json"]
            if isinstance(res_data, dict) and "scoreValue" in res_data:
                return True, res_data.get("scoreValue", 10), ""
            return True, 10, ""
        elif "error" in result:
            msg = result["error"]["json"]["message"]
            return False, 0, msg
    except Exception as e:
        return False, 0, str(e)

def get_tasks(headers):
    url = f"{BASE_URL}/quest.getTasks?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%7D%7D"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        data = resp.json()
        result = data[0]
        if "result" in result:
            return result["result"]["data"]["json"]
    except:
        pass
    return []

def complete_task(headers, participant_id, task_id):
    url = f"{BASE_URL}/quest.completeTask?batch=1"
    payload = {"0": {"json": {"participantId": participant_id, "taskId": task_id}}}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        data = resp.json()
        result = data[0]
        if "result" in result:
            res_data = result["result"]["data"]["json"]
            if res_data.get("success"):
                return True, res_data.get("scoreValue", 0), ""
            return False, 0, ""
        elif "error" in result:
            return False, 0, result["error"]["json"]["message"]
    except Exception as e:
        return False, 0, str(e)


# ============================================================
# Main Logic
# ============================================================
def process_account(cookie_idx, cookie_val):
    acc_num = cookie_idx + 1
    print(f"\n{B}{C}="*50)
    print(f"  ACCOUNT {acc_num}/{len(COOKIES)}")
    print(f"{"="*50}{X}")
    
    headers = get_headers(cookie_val)
    
    user = check_auth(headers)
    if not user:
        log_err("Authentication failed! Cookie might be expired/invalid.")
        return
        
    log_ok(f"Logged in: {user.get('name', 'Unknown')} ({user.get('email', '')})")
    
    participant = get_participant(headers)
    if not participant:
        log_err("Failed to get participant data.")
        return
        
    pid = participant["id"]
    score_before = participant.get("score", 0)
    x_user = participant.get("xUsername", "unknown")
    log_info(f"X Username: {x_user} | Score: {score_before}")

    # Daily Claim
    log_info("Attempting Daily Login Claim...")
    success, pts, err_msg = claim_daily(headers, pid)
    if success:
        log_ok(f"Daily Claimed! +{pts}pts")
        score_before += pts
    else:
        if "already" in err_msg.lower() or "済み" in err_msg or "already claimed" in err_msg.lower():
            log_warn(f"Daily already claimed.")
        elif "no procedure found" in err_msg.lower():
            log_warn(f"API Error: Daily claim endpoint (quest.claimDailyLogin) no longer exists.")
        else:
            log_err(f"Daily Claim failed: {err_msg[:60]}")
    time.sleep(1)

    # Tasks
    tasks = get_tasks(headers)
    if not tasks:
        log_err("No tasks fetched.")
        return
        
    log_info(f"Scanning {len(tasks)} missions...")
    
    new_completed = 0
    new_points = 0
    
    for task in tasks:
        tid = task["id"]
        name = task.get("taskNameEn", task.get("taskName", "Unknown"))
        ttype = task.get("taskType", "unknown")
        
        success, pts, err_msg = complete_task(headers, pid, tid)
        
        if success:
            new_completed += 1
            new_points += pts
            log_ok(f"Task Completed: {name} ({ttype}) -> +{pts}pts")
        else:
            # We don't display already completed missions as requested
            if "完了" not in err_msg and "already" not in err_msg.lower():
                log_err(f"Task Failed: {name} ({ttype}) -> {err_msg[:60]}")
        
        time.sleep(1) # Small delay to avoid rate limiting
        
    if new_completed == 0:
        log_warn("No new missions available to complete.")
    else:
        log_ok(f"New Points gained: +{new_points}")
        log_ok(f"Estimated Total Score: {score_before + new_points}")
        
    print(f"{B}{C}="*50 + X)


def run_all():
    print(f"\n{B}{M}╔══════════════════════════════════════════════╗")
    print(f"║ 🌟 KAGURA AUTO: MULTI-ACCOUNT & DAILY CLAIM  ║")
    print(f"╚══════════════════════════════════════════════╝{X}\n")
    
    for idx, cookie in enumerate(COOKIES):
        process_account(idx, cookie)
        if idx < len(COOKIES) - 1:
            log_info("Waiting 5 seconds before next account...")
            time.sleep(5)

def run_loop():
    CHECK_INTERVAL = 86400  # 24 hours
    hrs = CHECK_INTERVAL // 3600
    print(f"\n{B}{Y}[LOOP MODE] Script will automatically scan for new missions every {hrs} hours.{X}\n")
    
    while True:
        try:
            run_all()
            
            print()
            log_info("All accounts processed. Waiting for the next execution...")
            for remaining in range(CHECK_INTERVAL, 0, -1):
                hours, remainder = divmod(remaining, 3600)
                minutes, seconds = divmod(remainder, 60)
                timer_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                print(f"\r{B}{C}⏳ Time until next run: {timer_str}{X}", end="", flush=True)
                time.sleep(1)
            print("\r" + " " * 50 + "\r", end="") # Clear timer line
            
        except KeyboardInterrupt:
            log_warn("\n[!] Script stopped by user.")
            break
        except Exception as e:
            log_err(f"\nUnexpected Error: {e}")
            time.sleep(30)


if __name__ == "__main__":
    run_loop()
