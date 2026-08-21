# R6 automatic collector

This component is the bridge for PC custom-game telemetry. Rainbow Six Siege currently exposes real-time Game Events through Overwolf's GEP, including CUSTOM playlist detection, match/round state, roster, kills/deaths, and defuser events.

The collector is intended to normalize those events into the same event format used by `../app.js` and send them to the tournament backend.

## Important platform limitation

PC can be read directly through the supported game-event provider. Xbox does not expose the same local game-event interface to a normal Windows app. A truly zero-input Xbox implementation therefore requires an authorized external telemetry source from the game/service, which is not currently available to this project.

Do not treat video/OCR as authoritative match telemetry: it can miss events and should only be considered a future fallback.

## Normalized event shape

```json
{
  "type": "kill",
  "matchId": "pool-1",
  "round": 3,
  "killerId": "player-a",
  "victimId": "player-b",
  "headshot": true,
  "timestamp": 0
}
```

The browser tracker can consume the normalized events without any manual stat entry once a live collector is connected.
