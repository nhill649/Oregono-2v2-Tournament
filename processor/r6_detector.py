"""Conservative R6 HUD detector.

This module deliberately emits only high-confidence observations. It is designed to
be fed screenshots/frames from a real stream and improved from real tournament footage.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, asdict
from typing import Iterable

import cv2
import numpy as np
import pytesseract

@dataclass
class Observation:
    player: str
    kills: int
    deaths: int
    assists: int
    headshots: int = 0
    plants: int = 0
    defusals: int = 0
    timestamp: float = 0.0
    confidence: float = 0.0


def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def crop_scoreboard(frame: np.ndarray, crop=(0.06, 0.08, 0.94, 0.95)) -> np.ndarray:
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = crop
    return frame[int(y1*h):int(y2*h), int(x1*w):int(x2*w)]


def read_text(frame: np.ndarray) -> list[str]:
    img = crop_scoreboard(frame)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    text = pytesseract.image_to_string(threshold, config="--psm 6")
    return [line.strip() for line in text.splitlines() if line.strip()]


def find_player_line(lines: Iterable[str], player: str) -> str | None:
    target = normalize(player)
    for line in lines:
        if target and target in normalize(line):
            return line
    return None


def parse_player_row(line: str, player: str) -> Observation | None:
    nums = [int(n) for n in re.findall(r"(?<!\d)(\d{1,2})(?!\d)", line)]
    if len(nums) < 3:
        return None
    # R6 scoreboard layouts vary. Treat the final three numeric fields as K/D/A
    # until a real tournament frame gives us a layout-specific calibration.
    k, d, a = nums[-3:]
    if k > 20 or d > 20 or a > 20:
        return None
    return Observation(player=player, kills=k, deaths=d, assists=a, confidence=0.70)


def detect(frame: np.ndarray, players: Iterable[str], timestamp: float = 0.0) -> list[dict]:
    lines = read_text(frame)
    results = []
    for player in players:
        line = find_player_line(lines, player)
        if not line:
            continue
        obs = parse_player_row(line, player)
        if obs:
            obs.timestamp = timestamp
            results.append(asdict(obs))
    return results
