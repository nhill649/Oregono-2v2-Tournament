# R6 Custom Game Tracking

The stats dashboard is `stats.html` and the Replay Center is `stream-control.html`.

## What is implemented
- Playoff replay slots for Winner Semifinal 1, Winner Semifinal 2, Loser Semifinal, Winner Final, Loser Final, First Place Match 1, and optional First Place Match 2.
- Two-player-per-team gamer-tag roster.
- Pool play is excluded from stat tracking.
- Replay videos are uploaded to Firebase Storage, with the replay URL and match metadata stored in Firestore.
- The separate worker downloads pending replay videos, samples the video, OCRs the R6 scoreboard, and writes detected player totals to Firestore.
- Player tournament totals: kills, deaths, assists, headshots, rounds, matches, K/D and MVP score.
- Tournament MVP plus Top Fragger, Best Teammate, and Most Clutch awards.
- MVP and award scores are normalized from 0.0 to 100.0 with one decimal place.
- Reinforcement impact is intentionally 3%; unique-ability impact is 10%.

## Replay processing pipeline

`Replay Center -> Firebase Storage -> Firestore match record -> stats worker -> video frames -> R6 HUD/scoreboard OCR -> match totals -> tournament totals -> MVP/awards -> public stats dashboard`

The browser does **not** try to analyze the video itself. It uploads the actual replay file so the separate worker can process it reliably.

## Firebase Storage

The repository includes `storage.rules`. Deploy those rules to the tournament Firebase project and make sure Firebase Storage is enabled. The Replay Center requires an authenticated tournament admin to upload replay files.

## Worker deployment

Build `worker/Dockerfile` on a service that supports long-running containers. Set:

- `WORKER_TOKEN` — secret used by the admin page.
- `FIREBASE_SERVICE_ACCOUNT_JSON` — Firebase service-account JSON as one environment variable, or use platform Application Default Credentials.
- `FIREBASE_PROJECT_ID` — `oregano-2v2-tournament`.

The worker exposes `/health`, `/start`, and `/stop`. After the updated worker is deployed, start it once; it continuously checks the playoff match records for newly uploaded replays and processes them automatically.

## Accuracy

The processor is conservative. It only counts scoreboard rows it can associate with the entered gamer tags. If the video opens but the scoreboard is never visible/readable, the Replay Center will show `Replay processed — no scoreboard data detected` instead of inventing statistics.

For tournament-grade accuracy, the scoreboard crop/OCR parser should be calibrated against the exact replay layout and resolution used by the tournament.

## Firebase data

The public page reads `tournaments/oregano-stats`. The Replay Center writes its configuration and replay metadata to the same document. Do not put a Firebase service-account key in the website.
