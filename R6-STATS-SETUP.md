# R6 Custom Game Tracking

The stats dashboard is `stats.html` and the controller is `stats-admin.html`.

## What is implemented
- Twitch channel source list stored in Firestore.
- Public tournament stats dashboard.
- Player tournament totals: kills, deaths, assists, headshots, rounds, matches, K/D and MVP score.
- Automatic match-MVP display from processed match data.
- Admin controls for adding/removing Twitch sources and tournament players.
- Optional processing worker in `worker/` that captures a Twitch stream, samples frames, OCRs the R6 scoreboard and writes observations to Firestore.

## Important limitation
A Twitch embed is a playback surface, not a raw video-frame feed. Twitch's official embed API exposes player controls and playback metadata, but it does not expose the game's pixels to the webpage. The actual stat extraction therefore runs in the separate worker. The worker is deliberately conservative: if OCR is uncertain it skips the observation instead of inventing stats.

For tournament-grade accuracy, the scoreboard crop and OCR parser should be calibrated against the exact stream layout/resolution used by the tournament. The first version is designed to get the pipeline working and provide a correction point before relying on it for official results.

## Worker deployment
Build `worker/Dockerfile` on a service that supports long-running containers. Set:

- `WORKER_TOKEN` — secret used by the admin page.
- `FIREBASE_SERVICE_ACCOUNT_JSON` — Firebase service-account JSON as one environment variable, or use platform Application Default Credentials.
- `FIREBASE_PROJECT_ID` — `oregano-2v2-tournament`.
- Optional `SCOREBOARD_CROP` — normalized `x1,y1,x2,y2`, default `0.08,0.15,0.92,0.90`.

The worker exposes `/health`, `/start`, and `/stop`.

## Firebase
The public page reads `tournaments/oregano-stats`. The admin page writes its configuration to the same document. Use Firebase Authentication/Firestore Security Rules to protect admin writes; do not put a Firebase service-account key in the website.
