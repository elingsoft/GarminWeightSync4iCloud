#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mac watcher: iCloud Drive -> FIT -> Garmin Connect, delete source on success.

One-shot scan (run every 60 s by launchd, see com.user.weighin.plist):
  1. Scan WATCH_DIR for *.json or *.txt files (default:
     ~/Library/Mobile Documents/com~apple~CloudDocs/WeightIn).
  2. Skip files still syncing: names ending .icloud, or mtime less than 60 s old.
  3. Validate {date, weight_kg, measured_at}; dedupe by date (same date and
     |dWeight| < 0.05 kg -> skip, and delete the duplicate file).
  4. Build a FIT weight file with fit_weight.py (already verified: parses back
     correctly, byte-identical to the reference writer).
  5. Upload to Garmin Connect via the garminconnect library (cached DI tokens
     from login_once.py; auto-refresh handled by the library).
  6. ONLY on confirmed upload success: delete the source file from the folder
     (the deletion syncs back to iCloud, so it disappears from the phone too)
     and record the date in uploaded.json.
  On any failure the file is KEPT for the next round and the error is logged
  to weighin.log (surfaced in the 19:00 brief).

Upload path note: the FIT upload endpoint and token handling are verified
live on the first real weigh-in. If Connect ever rejects the FIT, the
fallback is the JSON weight API (same data, different carrier).
"""
import datetime
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fit_weight import build_weight_fit  # noqa: E402

WATCH_DIR = os.path.expanduser(os.environ.get(
    "WEIGHIN_DIR",
    "~/Library/Mobile Documents/com~apple~CloudDocs/WeightIn"))
# 运行期文件（日志、去重账本）放在项目级 Logs/ 子目录，不和代码混放。
LOG_DIR = os.path.join(os.path.dirname(HERE), "Logs")
STATE_FILE = os.path.join(LOG_DIR, "uploaded.json")
LOG_FILE = os.path.join(LOG_DIR, "weighin.log")
MIN_AGE_S = 60
DEDUP_TOL = 0.05
# 只在这些时间段内处理文件；改回 None 则全天运行。
# 每个窗口为 (开始时, 开始分, 结束时, 结束分)，按 Mac 本地时间判断，
# 结束时刻不含在内；跨午夜的窗口也支持，例如 (22, 0, 6, 0)。
# 当前为用户定的窗口：早上 5:00-8:00、晚上 20:00-22:00。
ACTIVE_WINDOWS = [(5, 0, 9, 0), (20, 0, 22, 0)]


def log(msg):
    line = f"{datetime.datetime.now().isoformat(timespec='seconds')} {msg}"
    print(line, flush=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def upload_fit(fit_bytes):
    """Upload FIT bytes to Garmin Connect. Returns a short result string.

    Uses the garminconnect library's cached tokens (seeded by login_once.py),
    loaded via an explicit tokenstore path: without it the library loads
    nothing and login() fails with "Username and password are required".
    If the cached tokens are dead, raises so the file is kept for retry and
    the user can re-run login_once.py.
    """
    from garminconnect import Garmin
    email = os.environ.get("GARMIN_EMAIL", "")
    password = os.environ.get("GARMIN_PASSWORD", "") or None
    try:
        client = Garmin(email, password)
    except TypeError:
        # Constructor signature differs across versions.
        client = Garmin(email)
    # Same lesson as login_widget.py: on this account the mobile strategies
    # 401 and kill the chain before widget is tried, so skip them outright.
    # (Garmin object .client is the SSO client.)
    client.client.skip_strategies = {"mobile+cffi", "mobile+requests"}
    client.login(tokenstore="~/.garminconnect/garmin_tokens.json")
    # Prefer the library's own upload when available; otherwise POST the FIT
    # to the upload-service with the client's DI access token.
    if hasattr(client, "upload_activity"):
        # 0.3.x upload_activity takes a FILE PATH (not bytes) and requires
        # a FIT/TCX/GPX extension, so stage the bytes in a temp .fit file.
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
            f.write(fit_bytes)
            tmp_path = f.name
        try:
            return str(client.upload_activity(tmp_path))
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    token = None
    for attr in ("access_token", "accessToken"):
        token = getattr(client, attr, None)
        if token:
            break
    if not token:
        token_file = os.path.expanduser("~/.garminconnect/garmin_tokens.json")
        try:
            with open(token_file, encoding="utf-8") as f:
                data = json.load(f)
            token = data.get("access_token") or data.get("accessToken")
        except (OSError, ValueError):
            token = None
    if not token:
        raise RuntimeError("no access token available after login")
    import urllib.request
    boundary = "----weighin-boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="weight.fit"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + fit_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        "https://connect.garmin.com/modern/proxy/upload-service/upload/.fit",
        data=body, method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return f"HTTP {resp.status}"


def parse_weight(raw):
    """Accept a number or a string with a unit suffix ('55.6 kg', '55.6千克').

    Shortcuts renders a Health quantity with its unit when dropped into text,
    so the JSON may carry the unit along. Extract the first number.
    """
    if isinstance(raw, (int, float)):
        return float(raw)
    m = re.search(r"\d+(?:\.\d+)?", str(raw))
    if not m:
        raise ValueError(f"no number in weight value: {raw!r}")
    return float(m.group(0))


def process_file(path, state):
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    date = payload.get("date", "")
    weight = parse_weight(payload.get("weight_kg", 0))
    if not (isinstance(date, str) and len(date) == 10 and date[4] == "-"
            and 20 <= weight <= 300):
        raise ValueError(f"bad payload in {os.path.basename(path)}: {payload!r}")
    prev = state.get(date)
    if prev and abs(prev["weight_kg"] - weight) < DEDUP_TOL:
        log(f"deduped {date} {weight} kg (already uploaded)")
        os.remove(path)
        return
    measured = payload.get("measured_at")
    if measured:
        when = datetime.datetime.fromisoformat(measured)
    else:
        when = datetime.datetime.fromisoformat(f"{date}T07:00:00+08:00")
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    fit = build_weight_fit(when.astimezone(datetime.timezone.utc), weight)
    result = upload_fit(fit)
    state[date] = {"weight_kg": weight,
                   "uploaded_at": datetime.datetime.now().isoformat(timespec="seconds"),
                   "result": str(result)}
    save_state(state)
    os.remove(path)  # ONLY after confirmed success
    log(f"uploaded {date} {weight} kg -> {result}; source file deleted")


def _in_active_window(now):
    """ACTIVE_WINDOWS 为 None 时全天运行；否则只在窗口内返回 True。"""
    if ACTIVE_WINDOWS is None:
        return True
    hm = (now.hour, now.minute)
    for sh, sm, eh, em in ACTIVE_WINDOWS:
        start, end = (sh, sm), (eh, em)
        if start <= end:
            if start <= hm < end:
                return True
        elif hm >= start or hm < end:  # 跨午夜窗口
            return True
    return False


def main():
    if not _in_active_window(datetime.datetime.now()):
        return 0  # 窗口外：什么都不做，下一轮 60 秒后再判断
    if not os.path.isdir(WATCH_DIR):
        log(f"watch dir not found (is iCloud Drive enabled?): {WATCH_DIR}")
        return 0
    state = load_state()
    now = time.time()
    for name in sorted(os.listdir(WATCH_DIR)):
        # iOS 27.2's Save File forces a .txt extension on text input even
        # when the subpath ends with .json, so accept both suffixes.
        if not (name.endswith(".json") or name.endswith(".txt")):
            continue
        path = os.path.join(WATCH_DIR, name)
        if name.endswith(".icloud.json"):
            continue
        try:
            st = os.stat(path)
        except OSError:
            continue
        if now - st.st_mtime < MIN_AGE_S:
            continue  # still syncing; next round
        try:
            process_file(path, state)
        except Exception as e:  # keep the file for retry
            log(f"FAILED {name}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
