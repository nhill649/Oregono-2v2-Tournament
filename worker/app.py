import os, json, time, threading, tempfile, re, subprocess
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import requests
from fastapi import FastAPI, Header, HTTPException
import firebase_admin
from firebase_admin import credentials, firestore

from processor.r6_detector import detect

app = FastAPI(title="R6 Replay Stats Worker")
TOKEN = os.getenv("WORKER_TOKEN", "change-me")
SERVICE_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
if not firebase_admin._apps:
    if SERVICE_JSON:
        firebase_admin.initialize_app(credentials.Certificate(json.loads(SERVICE_JSON)))
    else:
        firebase_admin.initialize_app()
db = firestore.client()

stop_event = threading.Event()
worker_thread = None

# Impact-first scoring. Reinforcements are intentionally tiny (3%).
# Unique-ability impact contributes 10%.
MVP_WEIGHTS = {
    "kills": 1.00,
    "assists": 0.45,
    "deaths": -0.55,
    "headshots": 0.15,
    "plants": 1.25,
    "defusals": 1.50,
    "entryKills": 0.75,
    "entryDeaths": -0.35,
    "clutches": 2.00,
    "impact": 1.00,
    "reinforcements": 0.03,
    "abilityImpact": 0.10,
}


def auth(authorization):
    if authorization != f"Bearer {TOKEN}":
        raise HTTPException(401, "Unauthorized")


def clamp100(value):
    return round(max(0.0, min(100.0, float(value or 0))), 1)


def normalize_scores(players, raw_key):
    values = [float(p.get(raw_key, 0) or 0) for p in players]
    if not values:
        return
    lo, hi = min(values), max(values)
    if hi <= lo:
        for p in players:
            p["mvpScore"] = 0.0
        return
    for p in players:
        p["mvpScore"] = clamp100((float(p.get(raw_key, 0) or 0) - lo) / (hi - lo) * 100.0)


def raw_mvp_score(p):
    score = sum(float(p.get(k, 0) or 0) * w for k, w in MVP_WEIGHTS.items())
    rounds = max(int(p.get("rounds", 0) or 0), 1)
    score += max(0.0, (rounds - int(p.get("deaths", 0) or 0)) / rounds) * 2.0
    return score


def award_score(p, kind):
    if kind == "topFragger":
        return (
            float(p.get("kills", 0) or 0) * 0.45
            + (float(p.get("kills", 0) or 0) / max(float(p.get("deaths", 0) or 0), 1.0)) * 0.25
            + float(p.get("assists", 0) or 0) * 0.15
            + float(p.get("headshots", 0) or 0) * 0.15
        )
    if kind == "bestTeammate":
        return (
            float(p.get("assists", 0) or 0) * 0.45
            + float(p.get("abilityImpact", 0) or 0) * 0.25
            + float(p.get("gadgetUses", 0) or 0) * 0.20
            + float(p.get("supportActions", 0) or 0) * 0.10
        )
    return (
        float(p.get("gameWinningMoves", 0) or 0) * 0.55
        + float(p.get("clutches", 0) or 0) * 0.35
        + float(p.get("roundWins", 0) or 0) * 0.10
    )


def update_awards(data):
    players = list((data.get("players") or {}).values())
    if not players:
        data["currentMVP"] = None
        data["tournamentMVP"] = None
        data["tournamentAwards"] = {}
        return

    for p in players:
        p["impactRaw"] = round(raw_mvp_score(p), 4)

    normalize_scores(players, "impactRaw")
    players_by_name = {p["name"]: p for p in players}

    def normalized_award(kind):
        raw = {p["name"]: award_score(p, kind) for p in players}
        hi = max(raw.values(), default=0.0)
        lo = min(raw.values(), default=0.0)
        result = []
        for p in players:
            score = 0.0 if hi <= lo else (raw[p["name"]] - lo) / (hi - lo) * 100.0
            result.append((p, clamp100(score)))
        result.sort(key=lambda x: (-x[1], x[0]["name"].lower()))
        return result[0] if result else (None, 0.0)

    mvp = max(players, key=lambda p: (float(p.get("mvpScore", 0) or 0), p["name"].lower()))
    fragger, fragger_score = normalized_award("topFragger")
    teammate, teammate_score = normalized_award("bestTeammate")
    clutch, clutch_score = normalized_award("mostClutch")

    data["currentMVP"] = {**mvp, "score": clamp100(mvp.get("mvpScore", 0))}
    data["tournamentMVP"] = data["currentMVP"]
    data["tournamentAwards"] = {
        "topFragger": {"name": fragger["name"], "score": fragger_score} if fragger else None,
        "bestTeammate": {"name": teammate["name"], "score": teammate_score} if teammate else None,
        "mostClutch": {"name": clutch["name"], "score": clutch_score} if clutch else None,
    }
    data["players"] = players_by_name


def roster_from(data, match=None):
    names = []
    if match:
        for field in ("teamA", "teamB"):
            raw = str(match.get(field, "") or "")
            names.extend(re.split(r"\s*(?:,|&|\+|/|\|)\s*", raw))
    names = [n.strip() for n in names if n.strip()]
    if len(names) < 2:
        names = [x.get("name") for x in data.get("playerList", []) if x.get("name")]
    return names


def download_replay(url, destination):
    with requests.get(url, stream=True, timeout=(20, 120)) as response:
        response.raise_for_status()
        with open(destination, "wb") as out:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    out.write(chunk)


def analyze_replay(path, players, max_seconds=None):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError("The uploaded replay could not be opened as a video.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    duration = frame_count / fps if frame_count else 0.0
    if max_seconds:
        duration = min(duration, max_seconds)

    # Scoreboard totals are cumulative, so sampling every two seconds and keeping
    # the largest observed value gives the final visible total without double-counting.
    step = max(int(fps * 2.0), 1)
    observations = []
    frame_index = 0
    try:
        while frame_index < frame_count and (not max_seconds or frame_index / fps <= max_seconds):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = cap.read()
            if not ok:
                break
            observations.extend(detect(frame, players, frame_index / fps))
            frame_index += step
    finally:
        cap.release()

    per_player = {}
    for obs in observations:
        name = obs["player"]
        current = per_player.setdefault(name, {
            "name": name, "kills": 0, "deaths": 0, "assists": 0,
            "headshots": 0, "plants": 0, "defusals": 0,
            "reinforcements": 0, "abilityImpact": 0,
            "entryKills": 0, "entryDeaths": 0, "clutches": 0,
            "impact": 0, "rounds": 0,
        })
        for key in ("kills", "deaths", "assists", "headshots", "plants", "defusals",
                    "reinforcements", "abilityImpact", "entryKills", "entryDeaths",
                    "clutches", "impact", "rounds"):
            if key in obs:
                current[key] = max(float(current.get(key, 0) or 0), float(obs[key] or 0))

    return {"duration": duration, "observations": len(observations), "players": list(per_player.values())}


def process_match(match_index, data, match):
    replay_url = match.get("replayUrl")
    if not replay_url or not match.get("statsEnabled", True):
        return data

    matches = list(data.get("matches") or [])
    while len(matches) < 7:
        matches.append({})
    match = dict(matches[match_index])
    match["status"] = "Processing replay..."
    matches[match_index] = match
    db.collection("tournaments").document("oregano-stats").set({"matches": matches}, merge=True)

    players = roster_from(data, match)
    if not players:
        raise RuntimeError("No player gamer tags were found for this match.")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        temp_path = tmp.name

    try:
        download_replay(replay_url, temp_path)
        result = analyze_replay(temp_path, players)

        if not result["players"]:
            match["status"] = "Replay processed — no scoreboard data detected"
            match["processingError"] = "The video opened successfully, but no readable R6 scoreboard rows containing the entered gamer tags were found."
            match["processedAt"] = time.time()
            matches[match_index] = match
            data["matches"] = matches
            db.collection("tournaments").document("oregano-stats").set(
                {"matches": matches, "workerStatus": "waiting_for_replay_data"}, merge=True
            )
            return data

        old_match_stats = (data.get("matchStats") or {}).get(str(match_index))
        totals = data.setdefault("players", {})
        if old_match_stats:
            for name, old in old_match_stats.items():
                if name in totals:
                    for key, value in old.items():
                        if key != "name":
                            totals[name][key] = max(0, float(totals[name].get(key, 0) or 0) - float(value or 0))

        match_stats = {}
        for p in result["players"]:
            name = p["name"]
            target = totals.setdefault(name, {
                "name": name, "team": "", "kills": 0, "deaths": 0, "assists": 0,
                "headshots": 0, "plants": 0, "defusals": 0, "entryKills": 0,
                "entryDeaths": 0, "clutches": 0, "impact": 0, "reinforcements": 0,
                "abilityImpact": 0, "gadgetUses": 0, "supportActions": 0,
                "gameWinningMoves": 0, "roundWins": 0, "matches": 0,
            })
            contribution = {k: p.get(k, 0) for k in (
                "kills", "deaths", "assists", "headshots", "plants", "defusals",
                "entryKills", "entryDeaths", "clutches", "impact", "reinforcements",
                "abilityImpact", "rounds")}
            match_stats[name] = contribution
            for key, value in contribution.items():
                target[key] = float(target.get(key, 0) or 0) + float(value or 0)

        data.setdefault("matchStats", {})[str(match_index)] = match_stats
        for p in totals.values():
            p["matches"] = len([x for x in (data.get("matchStats") or {}).values() if p["name"] in x])

        update_awards(data)
        match["status"] = f"Processed • {result['observations']} scoreboard observations"
        match["processedAt"] = time.time()
        match["processingError"] = ""
        matches[match_index] = match
        data["matches"] = matches
        data["workerLastEventAt"] = time.time()
        data["workerStatus"] = "ready"
        db.collection("tournaments").document("oregano-stats").set(data, merge=True)
        return data
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def process_pending_replays():
    ref = db.collection("tournaments").document("oregano-stats")
    snap = ref.get()
    data = snap.to_dict() or {}
    matches = data.get("matches") or []

    for i, match in enumerate(matches[:7]):
        if not match.get("statsEnabled", True) or not match.get("replayUrl"):
            continue
        uploaded = str(match.get("uploadedAt") or "")
        processed = str(match.get("processedAt") or "")
        if processed and uploaded and processed >= uploaded:
            continue
        try:
            process_match(i, data, match)
            data = ref.get().to_dict() or data
        except Exception as exc:
            latest = ref.get().to_dict() or {}
            latest_matches = list(latest.get("matches") or matches)
            while len(latest_matches) < 7:
                latest_matches.append({})
            latest_matches[i] = {**latest_matches[i], "status": "Processing error", "processingError": str(exc)}
            ref.set({"matches": latest_matches, "workerError": str(exc), "workerStatus": "error"}, merge=True)


def frame_stream(stream):
    # Backward-compatible Twitch path. Replays are the primary tournament input.
    url = stream.get("url", "").strip()
    if not url:
        return
    proc = subprocess.Popen(["streamlink", "--stdout", url, "best"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "image2pipe", "-vcodec", "mjpeg", "-vf", "fps=1", "-"], stdin=proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    buf = b""
    started = time.time()
    ref = db.collection("tournaments").document("oregano-stats")
    try:
        while not stop_event.is_set():
            chunk = ff.stdout.read(65536)
            if not chunk:
                break
            buf += chunk
            a = buf.find(b"\xff\xd8")
            b = buf.find(b"\xff\xd9", a + 2)
            if a < 0 or b < 0:
                if len(buf) > 2000000:
                    buf = buf[-500000:]
                continue
            jpg = buf[a:b + 2]
            buf = buf[b + 2:]
            frame = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                continue
            data = ref.get().to_dict() or {}
            observations = detect(frame, roster_from(data), time.time() - started)
            if observations:
                data["workerLastEventAt"] = time.time()
                data["workerStatus"] = "processing"
                ref.set(data, merge=True)
    finally:
        for p in (ff, proc):
            try:
                p.kill()
            except Exception:
                pass


def worker_loop():
    while not stop_event.is_set():
        try:
            process_pending_replays()
            data = db.collection("tournaments").document("oregano-stats").get().to_dict() or {}
            streams = [s for s in data.get("streams", []) if s.get("enabled", True) and s.get("url")]
            if streams:
                with ThreadPoolExecutor(max_workers=min(8, len(streams))) as pool:
                    futures = [pool.submit(frame_stream, s) for s in streams]
                    while not stop_event.is_set() and any(not f.done() for f in futures):
                        process_pending_replays()
                        time.sleep(2)
            else:
                time.sleep(5)
        except Exception as exc:
            db.collection("tournaments").document("oregano-stats").set({"workerError": str(exc), "workerStatus": "error"}, merge=True)
        time.sleep(2)


@app.get("/health")
def health():
    return {"ok": True, "running": bool(worker_thread and worker_thread.is_alive())}


@app.get("/start")
def start(authorization: str | None = Header(default=None)):
    global worker_thread
    auth(authorization)
    if worker_thread is None or not worker_thread.is_alive():
        stop_event.clear()
        worker_thread = threading.Thread(target=worker_loop, daemon=True)
        worker_thread.start()
    return {"ok": True, "running": True, "mode": "replay-and-stream", "maxStreams": 8}


@app.get("/stop")
def stop(authorization: str | None = Header(default=None)):
    auth(authorization)
    stop_event.set()
    return {"ok": True, "running": False}
