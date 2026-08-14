"""Direct Rainbow Six .rec parser bridge.

Uses the upstream r6-dissect CLI when the binary is present. The worker keeps a
fallback for the existing video path, but .rec is now the preferred source.
"""
import json, os, shutil, subprocess, tempfile

R6_DISSECT = os.getenv("R6_DISSECT_BIN", "/usr/local/bin/r6-dissect")


def _binary():
    return R6_DISSECT if os.path.exists(R6_DISSECT) else shutil.which("r6-dissect")


def parse_rec(path):
    """Return normalized replay JSON from an R6 .rec file.

    r6-dissect emits match feedback including kills, headshots, objectives,
    players and round information. Unknown fields are preserved in `raw`.
    """
    binary = _binary()
    if not binary:
        raise RuntimeError("r6-dissect is not installed in the worker image")
    proc = subprocess.run([binary, path], capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "r6-dissect failed")[-4000:])
    text = proc.stdout.strip()
    # CLI logging can precede JSON. Find the first complete JSON object.
    start = text.find("{")
    if start < 0:
        raise RuntimeError("r6-dissect returned no JSON")
    raw = json.loads(text[start:])
    return normalize(raw)


def normalize(raw):
    players = {}
    for p in raw.get("players", []) or []:
        name = p.get("username") or p.get("name")
        if not name:
            continue
        players[name] = {
            "name": name,
            "teamIndex": p.get("teamIndex"),
            "operator": (p.get("operator") or {}).get("name") or p.get("operatorName", ""),
            "kills": 0, "deaths": 0, "assists": 0, "headshots": 0,
            "plants": 0, "defusals": 0, "rounds": 0, "clutches": 0,
            "entryKills": 0, "entryDeaths": 0, "reinforcements": 0,
            "abilityImpact": 0, "gadgetUses": 0, "supportActions": 0,
            "gameWinningMoves": 0,
        }

    feedback = raw.get("matchFeedback", []) or []
    rounds = raw.get("rounds", []) or []
    for r in rounds:
        winner = r.get("winner") if isinstance(r, dict) else None
        if winner is not None:
            for p in players.values(): p["rounds"] += 1

    for e in feedback:
        typ = str(e.get("type", "")).lower()
        user = e.get("username") or e.get("player")
        target = e.get("target") or e.get("victim")
        if typ == "kill" and user in players:
            players[user]["kills"] += 1
            if e.get("headshot"):
                players[user]["headshots"] += 1
            if target in players:
                players[target]["deaths"] += 1
        elif "plant" in typ and user in players:
            players[user]["plants"] += 1
        elif ("disable" in typ or "defus" in typ) and user in players:
            players[user]["defusals"] += 1

    # Some parser versions expose explicit death feedback rather than deriving
    # it from kills. Use it when present, but never double-count a kill target.
    for e in feedback:
        typ = str(e.get("type", "")).lower()
        user = e.get("username") or e.get("player")
        if typ == "death" and user in players and not e.get("target"):
            players[user]["deaths"] = max(players[user]["deaths"], players[user]["deaths"] + 1)

    # Derived stats are deliberately transparent and conservative. They are not
    # claimed as raw replay facts when the replay format does not expose them.
    for p in players.values():
        p["headshotPct"] = round((p["headshots"] / p["kills"] * 100.0), 1) if p["kills"] else 0.0
        p["kd"] = round(p["kills"] / max(p["deaths"], 1), 2)
        # Assist estimate: a trade/kill without ownership data cannot be proven,
        # so leave raw assists at zero unless the parser supplies them.
        p["estimatedAssist"] = False

    return {
        "gameVersion": raw.get("gameVersion"),
        "map": (raw.get("map") or {}).get("name") if isinstance(raw.get("map"), dict) else raw.get("map"),
        "gamemode": (raw.get("gamemode") or {}).get("name") if isinstance(raw.get("gamemode"), dict) else raw.get("gamemode"),
        "players": list(players.values()),
        "matchFeedback": feedback,
        "rounds": rounds,
        "raw": raw,
    }
