
"""
Debug overlay for AI Air Mouse.
Displays fingertip landmarks and pinch distance in pixels.
"""

import math

import cv2
import numpy as np

from config import (
    PINCH_CLICK_COOLDOWN_FRAMES,
    PINCH_CONFIRM_FRAMES,
    PINCH_ENTER_PX,
    PINCH_RELEASE_PX,
)
from core.tracker import HandsResult, Landmark


_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17), (5, 9), (9, 13), (13, 17),
]

_GREEN = (0, 220, 80)
_ORANGE = (0, 160, 255)
_WHITE = (255, 255, 255)
_YELLOW = (0, 215, 255)
_PINK = (255, 80, 200)
_RED = (0, 0, 255)
_CYAN = (255, 255, 0)
_FONT = cv2.FONT_HERSHEY_SIMPLEX

# Landmark IDs for fingertip positions.
FINGERTIPS = {
    4: ("THUMB", (255, 255, 0)),
    8: ("INDEX", (0, 255, 255)),
    12: ("MIDDLE", (255, 0, 255)),
    16: ("RING", (255, 128, 0)),
    20: ("PINKY", (0, 128, 255)),
}


def _lm_px(lm: Landmark, w: int, h: int) -> tuple[int, int]:
    """Convert normalized landmarks into image pixel coordinates."""
    x = max(0, min(w - 1, int(round(lm.x * w))))
    y = max(0, min(h - 1, int(round(lm.y * h))))
    return x, y


def _draw_hand(
    img: np.ndarray,
    lms: list[Landmark],
    color: tuple,
    label: str,
) -> None:
    h, w = img.shape[:2]

    # Draw hand skeleton.
    for a, b in _CONNECTIONS:
        cv2.line(
            img,
            _lm_px(lms[a], w, h),
            _lm_px(lms[b], w, h),
            color,
            2,
            cv2.LINE_AA,
        )

    # Draw all landmarks.
    for lm in lms:
        x, y = _lm_px(lm, w, h)
        cv2.circle(img, (x, y), 4, color, -1, cv2.LINE_AA)

    # Highlight fingertips.
    for idx, (name, tip_color) in FINGERTIPS.items():
        lm = lms[idx]
        x, y = _lm_px(lm, w, h)

        cv2.circle(img, (x, y), 11, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.circle(img, (x, y), 8, tip_color, 2, cv2.LINE_AA)
        cv2.circle(img, (x, y), 3, tip_color, -1, cv2.LINE_AA)

        label_text = f"{idx} {name}"
        label_y = y - 15 if y > 35 else y + 25

        cv2.putText(
            img,
            label_text,
            (max(2, min(w - 120, x + 8)), label_y),
            _FONT,
            0.45,
            (0, 0, 0),
            3,
            cv2.LINE_AA,
        )

        cv2.putText(
            img,
            label_text,
            (max(2, min(w - 120, x + 8)), label_y),
            _FONT,
            0.45,
            tip_color,
            1,
            cv2.LINE_AA,
        )

    wx, wy = _lm_px(lms[0], w, h)

    cv2.putText(
        img,
        label,
        (max(5, wx + 12), max(20, wy - 8)),
        _FONT,
        0.7,
        color,
        2,
        cv2.LINE_AA,
    )


def draw_debug_frame(
    frame: np.ndarray,
    hands: HandsResult,
    right_state: str,
) -> np.ndarray:

    out = frame.copy()
    h, w = out.shape[:2]

    if hands.right is not None:
        landmarks = hands.right

        _draw_hand(out, landmarks, _GREEN, "R (RIGHT)")

        thumb = landmarks[4]
        index = landmarks[8]
        middle = landmarks[12]

        # Real 2D distance in pixels.
        d_ti_px = math.hypot(
            (thumb.x - index.x) * w,
            (thumb.y - index.y) * h,
        )

        # 3D distances for diagnostics.
        d_ti_3d = math.sqrt(
            (thumb.x - index.x) ** 2
            + (thumb.y - index.y) ** 2
            + (thumb.z - index.z) ** 2
        )

        d_tm_3d = math.sqrt(
            (thumb.x - middle.x) ** 2
            + (thumb.y - middle.y) ** 2
            + (thumb.z - middle.z) ** 2
        )

        # Visual indication based on pixel threshold.
        line_color = (
            _GREEN
            if d_ti_px < PINCH_ENTER_PX
            else _YELLOW
        )

        cv2.line(
            out,
            _lm_px(thumb, w, h),
            _lm_px(index, w, h),
            line_color,
            3,
            cv2.LINE_AA,
        )

        cv2.line(
            out,
            _lm_px(thumb, w, h),
            _lm_px(middle, w, h),
            _PINK,
            2,
            cv2.LINE_AA,
        )

        tip_lines = []

        for idx, (name, _) in FINGERTIPS.items():
            lm = landmarks[idx]
            tip_lines.append(
                f"{idx} {name}: x={lm.x:.3f} y={lm.y:.3f}"
            )

        hud_lines = [
            f"State: {right_state}",
            f"T-I: {d_ti_px:.1f} px | Limit: {PINCH_ENTER_PX:.0f} px",
            f"Rearm: {PINCH_RELEASE_PX:.0f} px",
            (
                f"Click: {PINCH_CONFIRM_FRAMES} frames | "
                f"Cooldown: {PINCH_CLICK_COOLDOWN_FRAMES} frames"
            ),
            f"T-I 3D: {d_ti_3d:.3f}",
            f"T-M 3D: {d_tm_3d:.3f}",
            (
                "Visual: PINCH RANGE"
                if d_ti_px < PINCH_ENTER_PX
                else "Visual: OPEN"
            ),
            "R hand: DETECTED",
            "L hand: " + (
                "DETECTED"
                if hands.left is not None
                else "absent"
            ),
            *tip_lines,
            "Q = quit",
        ]

    else:
        hud_lines = [
            f"State: {right_state}",
            "R hand: absent",
            "L hand: " + (
                "DETECTED"
                if hands.left is not None
                else "absent"
            ),
            "Q = quit",
        ]

    if hands.left is not None:
        _draw_hand(out, hands.left, _ORANGE, "L (LEFT)")

    # HUD background.
    pad = 8
    line_h = 21
    box_w = min(390, w - 1)
    box_h = min(len(hud_lines) * line_h + pad * 2, h - 1)

    cv2.rectangle(
        out,
        (0, 0),
        (box_w, box_h),
        (30, 30, 30),
        -1,
    )

    for idx, line in enumerate(hud_lines):
        y = pad + line_h * (idx + 1) - 4

        if y >= h:
            break

        color = _WHITE

        if "DETECTED" in line:
            color = _GREEN
        elif "PINCH RANGE" in line:
            color = _GREEN
        elif line.startswith("T-I:"):
            color = _CYAN
        elif any(
            line.startswith(f"{i} {name}:")
            for i, (name, _) in FINGERTIPS.items()
        ):
            color = _CYAN

        cv2.putText(
            out,
            line,
            (pad, y),
            _FONT,
            0.43,
            color,
            1,
            cv2.LINE_AA,
        )

    return out
