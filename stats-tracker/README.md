# R6 Custom Stats Tracker

A browser-based match recorder for Rainbow Six Siege custom games. It is platform-neutral: the same tracker can record matches containing PC players, Xbox players, or a mix.

## What it tracks

- Match ID, map, platform, and teams
- Player roster and team assignment
- Round wins and live round score
- Kills and deaths
- Headshots
- Defuser plants and disables
- Match leaderboard and K/D
- JSON export/import for saving a match or moving it to another computer
- Local browser persistence with `localStorage`

## Important platform note

The tracker does **not** run code on an Xbox. Xbox has no general mechanism for a normal web page to read Siege's internal live match events. The tracker therefore records Xbox matches through the same event controls used for any platform.

On PC, an automatic connector can later feed the same event model from a supported live-game-data provider. Overwolf currently documents R6 events for match, roster, kill, death, player, and defuser data. The web tracker is intentionally separated from that connector so Xbox and PC can use the same scoreboard.

## Open it

Open `index.html` in this folder. For the tournament website, publish this folder with GitHub Pages or serve it locally.

## Event model

The UI is designed around a simple normalized event stream:

- `round_win`
- `kill`
- `defuser_plant`
- `defuser_disable`

A future PC connector only needs to translate live R6 events into these actions. Xbox can use the same actions through the controls on the page.
