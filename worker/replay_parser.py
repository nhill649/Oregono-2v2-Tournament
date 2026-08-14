"""Native Rainbow Six Siege .rec parser bridge.

The worker uses the upstream r6-dissect CLI to decode the replay directly.
No video conversion or OCR is required for native .rec files.
"""
import json, os, shutil, subprocess

R6_DISSECT = os.getenv("R6_DISSECT_BIN", "/usr/local/bin/r6-dissect")


def _binary():
    return R6_DISSECT if os.path.exists(R6_DISSECT) else shutil.which("r6-dissect")


def parse_rec(path):
    binary = _binary()
    if not binary:
        raise RuntimeError("r6-dissect is not installed in the worker image")
    proc = subprocess.run([binary, path], capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "r6-dissect failed")[-4000:])
    text = proc.stdout.strip()
    start = text.find("{")
    if start < 0:
        raise RuntimeError("r6-dissect returned no JSON")
    try:
        raw = json.loads(text[start:])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Could not decode r6-dissect JSON: {exc}") from exc
    return normalize(raw)


def _player_name(event, field_names):
    for field in field_names:
        value = event.get(field)
        if isinstance(value, dict):
            value = value.get("username") or value.get("name")
        if value:
            return str(value)
    return ""


def _round_count(raw):
    rounds = raw.get("rounds") or []
    if isinstance(rounds, list):
        return len(rounds)
    return 0


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
            "kills": 0,
            "deaths": 0,
            "assists": 0,
            "headshots": 0,
            "plants": 0,
            "defusals": 0,
            "rounds": _round_count(raw),
            "clutches": 0,
            "entryKills": 0,
            "entryDeaths": 0,
            "reinforcements": 0,
            "abilityImpact": 0,
            "gadgetUses": 0,
            "supportActions": 0,
            "gameWinningMoves": 0,
            "roundWins": 0,
        }

    feedback = raw.get("matchFeedback") or []
    if not isinstance(feedback, list):
        feedback = []

    # r6-dissect currently exposes confirmed kill/headshot/objective feedback.
    # We also recognize assist/support event names when a newer parser version
    # supplies them, without treating unrelated events as assists.
    for e in feedback:
        if not isinstance(e, dict):
            continue
        typ = str(e.get("type", "")).strip().lower()
        user = _player_name(e, ("username", "player", "attacker", "actor", "source"))
        target = _player_name(e, ("target", "victim", "defender"))

        if typ == "kill" or typ.endswith("kill"):
            if user in players:
                players[user]["kills"] += 1
                if bool(e.get("headshot")):
                    players[user]["headshots"] += 1
            if target in players:
                players[target]["deaths"] += 1
            continue

        if "assist" in typ and user in players:
            players[user]["assists"] += 1
            continue

        if "plant" in typ and user in players:
            players[user]["plants"] += 1
            continue

        if ("disable" in typ or "defus" in typ) and user in players:
            players[user]["defusals"] += 1
            continue

        # Newer parser versions may expose explicit support/gadget/ability
        # events. Preserve them when available; otherwise these remain zero.
        if ("reinforce" in typ or "reinforcement" in typ) and user in players:
            players[user]["reinforcements"] += 1
            continue
        if ("ability" in typ or "gadget" in typ) and user in players:
            players[user]["gadgetUses"] += 1
            players[user]["abilityImpact"] += 1
            continue

    # Team/round winners can be derived from the round records when their
    # player/team association is explicit. Do not fabricate individual wins.
    for r in raw.get("rounds", []) or []:
        if not isinstance(r, dict):
            continue
        winning_team = r.get("winningTeamIndex")
        if winning_team is None:
            winner = r.get("winner")
            if isinstance(winner, dict):
                winning_team = winner.get("teamIndex")
        if winning_team is not None:
            for p in players.values():
                if p.get("teamIndex") == winning_team:
                    p["roundWins"] += 1

    # Transparent derived values. These are calculations from confirmed replay
    # events, not claims that the replay directly stores a K/D field.
    for p in players.values():
        p["headshotPct"] = round(p["headshots"] / p["kills"] * 100.0, 1) if p["kills"] else 0.0
        p["kd"] = round(p["kills"] / max(p["deaths"], 1), 2)
        p["estimatedAssist"] = False

    return {
        "gameVersion": raw.get("gameVersion"),
        "codeVersion": raw.get("codeVersion"),
        "timestamp": raw.get("timestamp"),
        "map": (raw.get("map") or {}).get("name") if isinstance(raw.get("map"), dict) else raw.get("map"),
        "gamemode": (raw.get("gamemode") or {}).get("name") if isinstance(raw.get("gamemode"), dict) else raw.get("gamemode"),
        "matchType": raw.get("matchType"),
        "teams": raw.get("teams") or [],
        "players": list(players.values()),
        "matchFeedback": feedback,
        "rounds": raw.get("rounds") or [],
        "raw": raw,
    }
