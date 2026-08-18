# Oregano 2v2 Tournament — Code Guide

This file is the map for making small, safe changes to the tournament website.

## Main files

- `index.html` — public viewer page. Changes here affect what spectators see.
- `admin.html` — admin/scoring page. Tournament controls, scoring, map assignment, team names, standings, bracket creation, and History controls live here.
- `firebase-config.js` — Firebase configuration. Do not change unless Firebase configuration itself needs to change.

## Safe editing rule

For a small change, edit only the smallest relevant section. Do not replace an entire HTML file when a small function or handler can be changed instead.

Before changing a file:

1. Read the current version from `main`.
2. Identify the exact function/handler that controls the requested behavior.
3. Make the smallest possible change.
4. Keep existing IDs, Firebase field names, state fields, and bracket match keys unless the change specifically requires them.
5. Commit with a specific message describing the change.
6. Check the resulting file/commit before making another change.

Git history is the rollback point. Never force-push or rewrite history for a normal tournament change.

## Admin sections

`admin.html` is organized into labeled sections:

- `TOURNAMENT CONFIGURATION` — default teams, default maps, default champion, bracket match keys.
- `GENERIC HELPERS` — shuffle, score validation, winner/loser helpers.
- `MAP ASSIGNMENT` — all map randomization behavior. This is the first place to look for map changes.
- `LOGIN` — admin authentication UI.
- `POOL RANDOMIZER` — pool matchup generation.
- `FIRESTORE / HISTORY` — saving current state and saved History snapshots.
- `STANDINGS / BRACKET` — standings, seeding, and bracket construction.
- `RENDERING` — admin-page display.
- `BUTTON ACTIONS` — what each admin button does.
- `SCORE / ROLE INPUTS` — score and ATK/DEF changes.
- `REAL-TIME FIREBASE STATE` — live synchronization.

## Current map behavior

There are two intentionally separate controls:

### Randomize Pool Matches

This changes the pool matchups and automatically assigns new maps to pool play and prepares all seven bracket map assignments.

### Randomize Maps for Every Match

This does **not** change teams or matchups. It only reshuffles the maps for the four pool matches and seven bracket matches.

The shared function for this behavior is `randomizeMaps()` in `admin.html`.

The seven bracket map keys are:

`wb1`, `wb2`, `wbf`, `lb1`, `lb2`, `fp1`, `fp2`

Map assignments are stored in `state.pendingBracketMaps` before the bracket is locked/created, so the viewer can use them for a pre-lock preview.

## History safety

History entries are snapshots. Current tournament changes should not mutate previously saved History entries.

History deletion is intentionally separate from current-tournament reset.

## Viewer editing

When changing `index.html`, preserve the existing bracket layout and viewer behavior unless the requested change specifically targets them.

For spectator-only changes, prefer changing the display/rendering function rather than changing the underlying Firebase state model.

## Before declaring a change complete

Check all of these:

- Pool matchup randomization still works.
- Map randomization does not unexpectedly change teams/matchups.
- Maps are saved to Firebase.
- The viewer receives the same saved state.
- Bracket creation still works.
- Scores and ATK/DEF selection still work.
- History save/delete still work.
- Current reset does not delete History.

## Future architecture goal

If the project grows substantially, the next safe structural improvement is to move CSS and JavaScript out of the HTML files into separate files/modules. That should be done as a dedicated refactor with testing, not mixed into a feature change. Until then, the labeled sections in `admin.html` and this guide are the stable map for micro-edits.
