#!/usr/bin/env python3
"""
Kagura / AirdropsQuest - Auto Mission & Daily Claim (Multi-Account)
Reads cookies from cookies.txt (one per line)
Automatically claims daily login and completes all available tasks.
Skips/hides finished missions.
Features: Accept Friends, Free Gacha Spin

Fix Log:
- accept_all_friends  : removed invalid meta wrapper from POST payload
- get_daily_free_spin_status : split dari batch 4 jadi standalone call
- spin_gacha          : hapus costPoints:0 yang menyebabkan server reject
- semua fungsi        : tambah HTTP status code check
"""

import requests
import json
import time
import sys
import os
import urllib.parse
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

def log_ok(msg):   log(f"✅ {msg}", G)
def log_err(msg):  log(f"❌ {msg}", R)
def log_info(msg): log(f"ℹ️  {msg}", C)
def log_warn(msg): log(f"⚠️  {msg}", Y)
def log_task(msg): log(f"🎯 {msg}", M)
def log_dbg(msg):  log(f"🔍 [DBG] {msg}", Y)  # debug — aktifkan manual jika perlu


def printCredit():
    print(f"\n{B}{M}╔══════════════════════════════════════════════╗")
    print(f"║        🤖  Kagura Bot by Noya-xen            ║")
    print(f"║   github.com/Noya-xen  |  @xinomixo         ║")
    print(f"╚══════════════════════════════════════════════╝{X}\n")


# ============================================================
# Helpers
# ============================================================
def _safe_post(url, headers, payload, timeout=15):
    """POST wrapper dengan HTTP status check."""
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if resp.status_code not in (200, 201):
            return None, f"HTTP {resp.status_code}"
        return resp.json(), ""
    except Exception as e:
        return None, str(e)


def _safe_get(url, headers, timeout=15):
    """GET wrapper dengan HTTP status check."""
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}"
        return resp.json(), ""
    except Exception as e:
        return None, str(e)


# ============================================================
# API Functions
# ============================================================
def check_auth(headers):
    url = f"{BASE_URL}/auth.me?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%7D%7D"
    data, err = _safe_get(url, headers)
    if not data:
        return None
    try:
        result = data[0]
        if "result" in result:
            user = result["result"]["data"]["json"]
            if user:
                return user
    except Exception:
        pass
    return None


def get_participant(headers):
    input_data = json.dumps({"0": {"json": None, "meta": {"values": ["undefined"]}}})
    encoded = urllib.parse.quote(input_data)
    url = f"{BASE_URL}/quest.getMyParticipant?batch=1&input={encoded}"
    data, err = _safe_get(url, headers)
    if not data:
        log_warn(f"getMyParticipant: {err}")
        return None
    try:
        result = data[0]
        if "result" in result:
            return result["result"]["data"]["json"]
        elif "error" in result:
            log_warn(f"getMyParticipant error: {result['error']['json'].get('message','?')}")
    except Exception as e:
        log_warn(f"getMyParticipant parse error: {e}")
    return None


def claim_daily(headers, participant_id):
    url = f"{BASE_URL}/quest.claimDailyLoginBonus?batch=1"
    payload = {"0": {"json": {"participantId": participant_id}}}
    data, err = _safe_post(url, headers, payload)
    if not data:
        return False, 0, err
    try:
        result = data[0]
        if "result" in result:
            res_data = result["result"]["data"]["json"]
            pts = res_data.get("scoreValue", 10) if isinstance(res_data, dict) else 10
            return True, pts, ""
        elif "error" in result:
            return False, 0, result["error"]["json"]["message"]
    except Exception as e:
        return False, 0, str(e)


def get_tasks(headers):
    url = f"{BASE_URL}/quest.getTasks?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%7D%7D"
    data, err = _safe_get(url, headers)
    if not data:
        return []
    try:
        result = data[0]
        if "result" in result:
            return result["result"]["data"]["json"]
    except Exception:
        pass
    return []


def complete_task(headers, participant_id, task_id):
    url = f"{BASE_URL}/quest.completeTask?batch=1"
    payload = {"0": {"json": {"participantId": participant_id, "taskId": task_id}}}
    data, err = _safe_post(url, headers, payload)
    if not data:
        return False, 0, err
    try:
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
# FIX #1: Accept All Friends
# ============================================================
def accept_all_friends(headers):
    """
    Accept all pending friend requests.

    BUG LAMA: POST payload pakai meta: {"values": ["undefined"]} — format ini
    hanya relevan untuk GET tRPC (supaya server decode query param sebagai undefined).
    Pada POST body, meta wrapper ini justru menyebabkan server menolak atau
    mengembalikan unexpected response.

    FIX: Kirim {"0": {"json": null}} saja (standar tRPC POST tanpa argumen).
    Kalau null juga gagal, fallback ke {"0": {"json": {}}} (empty object).
    """
    url = f"{BASE_URL}/quest.acceptAllFriendRequests?batch=1"

    # Coba dengan null dulu (tRPC standard no-arg POST)
    payload = {"0": {"json": None}}
    data, err = _safe_post(url, headers, payload)

    # Fallback: coba empty object jika null ditolak
    if not data or (isinstance(data, list) and data and "error" in data[0]):
        err_preview = ""
        if data and isinstance(data, list) and "error" in data[0]:
            err_preview = data[0]["error"]["json"].get("message", "")
        if "invalid" in err_preview.lower() or "expected" in err_preview.lower():
            payload = {"0": {"json": {}}}
            data, err = _safe_post(url, headers, payload)

    if not data:
        return False, 0, err

    try:
        result = data[0]
        if "result" in result:
            res_data = result["result"]["data"]["json"]
            if isinstance(res_data, dict):
                # Platform bisa return berbagai field name
                count = (
                    res_data.get("count") or
                    res_data.get("accepted") or
                    res_data.get("friendsAccepted") or
                    0
                )
            elif isinstance(res_data, int):
                count = res_data
            else:
                count = 0
            return True, count, ""
        elif "error" in result:
            msg = result["error"]["json"].get("message", "Unknown error")
            return False, 0, msg
    except Exception as e:
        return False, 0, str(e)


# ============================================================
# FIX #2: Daily Free Gacha Spin
# ============================================================
def get_daily_free_spin_status(headers, participant_id):
    """
    Check if daily free spin is available.

    BUG LAMA: Fungsi ini melakukan batch 4 endpoint sekaligus:
    getMyParticipant + getGachaHistory + getGachaSpinStatus + getDailyFreeSpinStatus
    Masalahnya:
    1. Jika SATU saja dari 4 endpoint error, seluruh batch bisa gagal atau
       menggeser index response → data[3] jadi salah.
    2. Input untuk index 0 masih pakai meta wrapper → bisa conflict.
    3. Tidak perlu data dari 3 endpoint lain hanya untuk cek spin status.

    FIX: Panggil getDailyFreeSpinStatus secara standalone (batch=1, 1 endpoint).
    Jika endpoint tidak tersedia, fallback ke getGachaSpinStatus.
    """
    # ── Coba getDailyFreeSpinStatus dulu ────────────────────
    input_data = json.dumps({"0": {"json": {"participantId": participant_id}}})
    encoded = urllib.parse.quote(input_data)
    url = f"{BASE_URL}/quest.getDailyFreeSpinStatus?batch=1&input={encoded}"

    data, err = _safe_get(url, headers)

    if data and isinstance(data, list) and len(data) > 0:
        result = data[0]
        if "result" in result:
            status = result["result"]["data"]["json"]
            is_available = (
                status.get("isAvailable", False)
                if isinstance(status, dict) else bool(status)
            )
            return is_available, status
        elif "error" in result:
            err_msg = result["error"]["json"].get("message", "")
            # Endpoint tidak ada → fallback ke getGachaSpinStatus
            if "no procedure" in err_msg.lower() or "not found" in err_msg.lower():
                return _get_spin_status_fallback(headers, participant_id)
            log_warn(f"getDailyFreeSpinStatus: {err_msg[:80]}")

    # Jika HTTP error atau parse error → fallback
    if err:
        return _get_spin_status_fallback(headers, participant_id)

    return False, {}


def _get_spin_status_fallback(headers, participant_id):
    """Fallback: getGachaSpinStatus jika getDailyFreeSpinStatus tidak tersedia."""
    input_data = json.dumps({"0": {"json": {"participantId": participant_id}}})
    encoded = urllib.parse.quote(input_data)
    url = f"{BASE_URL}/quest.getGachaSpinStatus?batch=1&input={encoded}"

    data, err = _safe_get(url, headers)
    if not data:
        log_warn(f"getGachaSpinStatus fallback: {err}")
        return False, {}
    try:
        result = data[0]
        if "result" in result:
            status = result["result"]["data"]["json"]
            # getGachaSpinStatus biasanya return: {freeSpinsAvailable: N, ...}
            if isinstance(status, dict):
                free_count = (
                    status.get("freeSpinsAvailable") or
                    status.get("freeSpin") or
                    status.get("dailyFreeSpin") or
                    0
                )
                is_available = int(free_count) > 0
                return is_available, status
        elif "error" in result:
            log_warn(f"getGachaSpinStatus: {result['error']['json'].get('message','?')[:60]}")
    except Exception as e:
        log_warn(f"getGachaSpinStatus parse: {e}")
    return False, {}


def spin_gacha(headers, participant_id):
    """
    Perform one free gacha spin.

    BUG LAMA: Payload menyertakan costPoints: 0.
    Platform bisa menginterpretasi field ini sebagai "bayar 0 poin" yang
    berbeda dengan "free spin" → server menolak request karena
    konflik antara costPoints dan isFreeSpin flag.

    FIX: Hapus costPoints dari payload. Kirim hanya participantId + isFreeSpin.
    """
    url = f"{BASE_URL}/quest.spinGacha?batch=1"
    payload = {
        "0": {
            "json": {
                "participantId": participant_id,
                "isFreeSpin": True
                # costPoints dihapus — konflik dengan isFreeSpin flag
            }
        }
    }
    data, err = _safe_post(url, headers, payload)
    if not data:
        return False, 0, "", err
    try:
        result = data[0]
        if "result" in result:
            res_data = result["result"]["data"]["json"]
            reward = 0
            rarity = "?"
            if isinstance(res_data, dict):
                reward = (
                    res_data.get("rewardValue") or
                    res_data.get("scoreValue") or
                    res_data.get("points") or
                    0
                )
                rarity = (
                    res_data.get("rarity") or
                    res_data.get("type") or
                    res_data.get("grade") or
                    "?"
                )
            return True, reward, rarity, ""
        elif "error" in result:
            msg = result["error"]["json"].get("message", "Unknown error")
            return False, 0, "", msg
    except Exception as e:
        return False, 0, "", str(e)


# ============================================================
# Main Logic
# ============================================================
def process_account(cookie_idx, cookie_val):
    acc_num = cookie_idx + 1
    print(f"\n{B}{C}" + "="*50)
    print(f"  ACCOUNT {acc_num}/{len(COOKIES)}")
    print("="*50 + X)

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

    # ── Daily Claim ──────────────────────────────────────────
    log_info("Attempting Daily Login Claim...")
    success, pts, err_msg = claim_daily(headers, pid)
    if success:
        log_ok(f"Daily Claimed! +{pts}pts")
        score_before += pts
    else:
        if "already" in err_msg.lower():
            log_warn("Daily already claimed.")
        elif "no procedure found" in err_msg.lower():
            log_warn("API Error: Daily claim endpoint no longer exists.")
        else:
            log_err(f"Daily Claim failed: {err_msg[:80]}")
    time.sleep(1)

    # ── Accept All Friends ───────────────────────────────────
    log_info("Checking pending friend requests...")
    ok, count, err = accept_all_friends(headers)
    if ok:
        if count and int(count) > 0:
            log_ok(f"Accepted {count} friend request(s)!")
        else:
            log_warn("No pending friend requests.")
    else:
        low = err.lower()
        if any(k in low for k in ("no pending", "not found", "empty", "no friend")):
            log_warn("No pending friend requests.")
        elif "http 4" in low:
            log_err(f"Accept Friends auth/API error: {err}")
        else:
            log_err(f"Accept Friends failed: {err[:80]}")
    time.sleep(1)

    # ── Daily Free Gacha Spin ────────────────────────────────
    log_info("Checking daily free gacha spin...")
    spin_available, spin_status = get_daily_free_spin_status(headers, pid)
    if spin_available:
        log_info("Free spin available! Spinning...")
        spin_ok, reward, rarity, spin_err = spin_gacha(headers, pid)
        if spin_ok:
            log_ok(f"🎰 Gacha Result: [{rarity.upper()}] → +{reward}pts")
            score_before += int(reward)
        else:
            low = spin_err.lower()
            if "already" in low or "no free" in low or "used" in low:
                log_warn("Free spin already used today.")
            elif "http 4" in low:
                log_err(f"Gacha spin auth/API error: {spin_err}")
            else:
                log_err(f"Gacha Spin failed: {spin_err[:80]}")
    else:
        log_warn("No free spin available today.")
    time.sleep(1)

    # ── Tasks ────────────────────────────────────────────────
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
            log_ok(f"Task Completed: {name} ({ttype}) → +{pts}pts")
        else:
            if err_msg and "already" not in err_msg.lower() and "完了" not in err_msg:
                log_err(f"Task Failed: {name} ({ttype}) → {err_msg[:80]}")

        time.sleep(1)

    if new_completed == 0:
        log_warn("No new missions available to complete.")
    else:
        log_ok(f"New Points gained: +{new_points}")
        log_ok(f"Estimated Total Score: {score_before + new_points}")

    print(f"{B}{C}" + "="*50 + X)


def run_all():
    printCredit()
    for idx, cookie in enumerate(COOKIES):
        process_account(idx, cookie)
        if idx < len(COOKIES) - 1:
            log_info("Waiting 5 seconds before next account...")
            time.sleep(5)


def run_loop():
    CHECK_INTERVAL = 86400  # 24 hours
    hrs = CHECK_INTERVAL // 3600
    print(f"\n{B}{Y}[LOOP MODE] Auto-scan every {hrs} hours.{X}\n")

    while True:
        try:
            run_all()

            print()
            log_info("All accounts processed. Waiting for the next execution...")
            for remaining in range(CHECK_INTERVAL, 0, -1):
                hours, remainder = divmod(remaining, 3600)
                minutes, seconds = divmod(remainder, 60)
                timer_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                print(f"\r{B}{C}⏳ Next run in: {timer_str}{X}", end="", flush=True)
                time.sleep(1)
            print("\r" + " " * 50 + "\r", end="")

        except KeyboardInterrupt:
            log_warn("\n[!] Script stopped by user.")
            break
        except Exception as e:
            log_err(f"\nUnexpected Error: {e}")
            time.sleep(30)


if __name__ == "__main__":
    run_loop()
