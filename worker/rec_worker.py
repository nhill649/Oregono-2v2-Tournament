"""Native .rec processing adapter for the existing worker."""
import os, tempfile, requests, time
from replay_parser import parse_rec


def install(app_module):
    old_process_match = app_module.process_match

    def process_match(match_index, data, match):
        url = str(match.get("replayUrl") or "")
        is_rec = str(match.get("replayFormat") or "").lower() == "rec" or str(match.get("fileName") or "").lower().endswith(".rec")
        if not url or not is_rec:
            return old_process_match(match_index, data, match)

        matches = list(data.get("matches") or [])
        while len(matches) < 7:
            matches.append({})
        match = dict(matches[match_index])
        match["status"] = "Parsing .REC replay..."
        matches[match_index] = match
        app_module.db.collection("tournaments").document("oregano-stats").set({"matches": matches, "workerStatus": "processing_rec"}, merge=True)

        fd, path = tempfile.mkstemp(suffix=".rec")
        os.close(fd)
        try:
            with requests.get(url, stream=True, timeout=(20, 600)) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_content(1024 * 1024):
                        if chunk:
                            f.write(chunk)

            result = parse_rec(path)
            players = result.get("players", [])
            if not players:
                raise RuntimeError("The .rec parser found no players in this replay.")

            totals = data.setdefault("players", {})
            old_match_stats = (data.get("matchStats") or {}).get(str(match_index), {})
            for name, old in old_match_stats.items():
                if name in totals:
                    for key, value in old.items():
                        if key != "name":
                            totals[name][key] = max(0, float(totals[name].get(key, 0) or 0) - float(value or 0))

            match_stats = {}
            for p in players:
                name = p["name"]
                target = totals.setdefault(name, {
                    "name": name, "team": "", "kills": 0, "deaths": 0, "assists": 0,
                    "headshots": 0, "plants": 0, "defusals": 0, "rounds": 0,
                    "clutches": 0, "entryKills": 0, "entryDeaths": 0,
                    "reinforcements": 0, "abilityImpact": 0, "gadgetUses": 0,
                    "supportActions": 0, "gameWinningMoves": 0, "roundWins": 0,
                    "matches": 0,
                })
                contribution = {key: float(p.get(key, 0) or 0) for key in (
                    "kills", "deaths", "assists", "headshots", "plants", "defusals",
                    "rounds", "clutches", "entryKills", "entryDeaths", "reinforcements",
                    "abilityImpact", "gadgetUses", "supportActions", "gameWinningMoves", "roundWins")}
                match_stats[name] = contribution
                for key, value in contribution.items():
                    target[key] = float(target.get(key, 0) or 0) + value
                target["operator"] = p.get("operator", "")
                target["teamIndex"] = p.get("teamIndex")
                target["headshotPct"] = round(float(target.get("headshots", 0)) / max(float(target.get("kills", 0)), 1) * 100, 1)
                target["kd"] = round(float(target.get("kills", 0)) / max(float(target.get("deaths", 0)), 1), 2)

            data.setdefault("matchStats", {})[str(match_index)] = match_stats
            for p in totals.values():
                p["matches"] = len([x for x in (data.get("matchStats") or {}).values() if p["name"] in x])

            app_module.update_awards(data)
            match["status"] = "Processed .REC replay"
            match["processedAt"] = time.time()
            match["processingError"] = ""
            match["parser"] = "r6-dissect"
            match["map"] = result.get("map")
            match["gameVersion"] = result.get("gameVersion")
            match["matchType"] = result.get("matchType")
            match["parsedPlayers"] = len(players)
            match["parsedEvents"] = len(result.get("matchFeedback") or [])
            matches[match_index] = match
            data["matches"] = matches
            data["workerStatus"] = "ready"
            data["workerLastEventAt"] = time.time()
            app_module.db.collection("tournaments").document("oregano-stats").set(data, merge=True)
            return data
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    app_module.process_match = process_match
    return app_module
