# R6 Stream Processor

This folder is the backend design for the tournament video analyzer.

## Pipeline

Twitch stream(s) -> capture/ingest -> frame sampler -> R6 HUD detector/OCR -> event timeline -> stat aggregation -> MVP scoring -> Firebase.

The processor is intentionally separate from the GitHub Pages frontend. The frontend cannot securely hold Twitch application secrets or continuously process video.

## Perspective model

The tournament supports up to 8 registered player streams, but a match may have only 1-2 useful perspectives. The processor must never invent an event that is not observable. Multiple perspectives are correlated by timestamp when available.

## Event types

The first detector target is:
- round start/end
- player identity
- kills/deaths
- headshot indicator when visible
- assists when visible
- plants/defusals
- defuse denial / time-denial actions when observable
- entry kills / first deaths
- clutch situations and outcomes
- round result

The event schema should preserve `confidence`, `sourceStream`, and `timestamp` so the dashboard can distinguish verified observations from uncertain detections.

## MVP

The MVP scorer should prioritize match influence, not raw kills. Inputs include combat output, K/D, KOST-like round success, entry impact, objective actions, survival, clutch outcomes, time-denial actions, trades, and round/match swing events. Missing visibility reduces confidence rather than creating a penalty for an unseen event.

## First live test

Use the registered `nhill_3` / Thunderpants324 perspective first. Do not start an 8-stream run until the single-perspective detector is validated.
