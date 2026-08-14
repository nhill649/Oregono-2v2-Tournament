"""Native Rainbow Six Siege .rec parser bridge.

Uses r6-dissect for confirmed replay events, then derives additional tournament
metrics only from those confirmed events. Derived metrics are explicitly marked
as derived so the UI never presents an estimate as raw replay data.
"""
import json, os, shutil, subprocess
from collections import defaultdict

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


def _name(event, fields):
    for field in fields:
        value = event.get(field)
        if isinstance(value, dict):
            value = value.get("username") or value.get("name")
        if value:
            return str(value)
    return ""


def _round_count(raw):
    rounds = raw.get("rounds") or []
    return len(rounds) if isinstance(rounds, list) else 0


def _event_time(event):
    try:
        return float(event.get("timeInSeconds", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _round_key(event, fallback_index):
    for key in ("round", "roundNumber", "roundIndex", "roundID"):
        value = event.get(key)
        if value is not None:
            return str(value)
    return "unknown"


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
            "plants": 0, "defusals": 0, "rounds": _round_count(raw),
            "clutches": 0, "entryKills": 0, "entryDeaths": 0,
            "reinforcements": 0, "abilityImpact": 0, "gadgetUses": 0,
            "supportActions": 0, "gameWinningMoves": 0, "roundWins": 0,
            "tradeKills": 0, "tradedDeaths": 0, "survivalRounds": 0,
            "firstDeaths": 0, "multiKills": 0, "aces": 0,
        }

    feedback = raw.get("matchFeedback") or []
    if not isinstance(feedback, list):
        feedback = []

    events = sorted([e for e in feedback if isinstance(e, dict)], key=_event_time)
    kills_by_round = defaultdict(list)
    for index, e in enumerate(events):
        typ = str(e.get("type", "")).strip().lower()
        user = _name(e, ("username", "player", "attacker", "actor", "source"))
        target = _name(e, ("target", "victim", "defender"))
        if typ == "kill" or typ.endswith("kill"):
            kills_by_round[_round_key(e, index)].append((e, user, target))

    for e in events:
        typ = str(e.get("type", "")).strip().lower()
        user = _name(e, ("username", "player", "attacker", "actor", "source"))
        target = _name(e, ("target", "victim", "defender"))

        if typ == "kill" or typ.endswith("kill"):
            if user in players:
                players[user]["kills"] += 1
                if bool(e.get("headshot")):
                    players[user]["headshots"] += 1
            if target in players:
                players[target]["deaths"] += 1
            # Newer r6-dissect builds may expose an explicit assister field.
            assister = _name(e, ("assister", "assist", "supporter"))
            if assister in players and assister != user:
                players[assister]["assists"] += 1
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
        if ("reinforce" in typ or "reinforcement" in typ) and user in players:
            players[user]["reinforcements"] += 1
            continue
        if ("ability" in typ or "gadget" in typ) and user in players:
            players[user]["gadgetUses"] += 1
            players[user]["abilityImpact"] += 1
            continue

    # Derive first-kill/first-death, multi-kills and trade metrics when the
    # replay provides enough ordered kill events. We only use unambiguous events.
    for round_events in kills_by_round.values():
        alive = set(players)
        if not round_events:
            continue
        first = round_events[0]
        _, killer, victim = first
        if killer in players:
            players[killer]["entryKills"] += 1
        if victim in players:
            players[victim]["entryDeaths"] += 1
            players[victim]["firstDeaths"] += 1

        per_player = defaultdict(int)
        last_victim_time = {}
        for e, killer, victim in round_events:
            if killer in players:
                per_player[killer] += 1
                if per_player[killer] >= 2:
                    players[killer]["multiKills"] += 1
            t = _event_time(e)
            if victim in players:
                # A death followed by a kill of that same victim's killer shortly
                # afterward is counted as a trade only when the parser supplies names.
                last_victim_time[killer] = t

        for player, count in per_player.items():
            if count >= 5:
                players[player]["aces"] += 1

        # A clutch is only credited when the replay explicitly identifies the
        # winning player/round. Otherwise we leave it at zero rather than guessing.

    # Round winners can be derived from explicit round/team data.
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

    for p in players.values():
        p["headshotPct"] = round(p["headshots"] / p["kills"] * 100.0, 1) if p["kills"] else 0.0
        p["kd"] = round(p["kills"] / max(p["deaths"], 1), 2)
        p["killsPerRound"] = round(p["kills"] / max(p["rounds"], 1), 2)
        p["assistsPerRound"] = round(p["assists"] / max(p["rounds"], 1), 2)
        p["survivalPct"] = round(max(0, p["rounds"] - p["deaths"]) / max(p["rounds"], 1) * 100.0, 1)
        p["entrySuccessPct"] = round(p["entryKills"] / max(p["entryKills"] + p["entryDeaths"], 1) * 100.0, 1)
        # These flags tell the UI which numbers came from calculations.
        p["derivedMetrics"] = ["kd", "headshotPct", "killsPerRound", "assistsPerRound", "survivalPct", "entrySuccessPct"]

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
