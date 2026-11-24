
# core/gestures/right_hand.py
"""
Right-hand gesture processor.

Gestures:
- Thumb + index pinch: left click
- Thumb + middle pinch: right click
- Four fingers extended: Win+Tab

Index pinch:
- Pixel-based distance (40 px threshold)
- 5 consecutive frames to confirm
- Hysteresis to prevent jitter
"""

import time
import math
import logging
from enum import Enum, auto

from config import (
    CAMERA_FPS,
    THUMB_MIDDLE_CLICK_DIST,
    GESTURE_COOLDOWN_SECONDS,
    PINCH_CLICK_COOLDOWN_FRAMES,
    PINCH_CONFIRM_FRAMES,
    PINCH_ENTER_PX,
    PINCH_RELEASE_PX,
    ONE_EURO_MINCUTOFF,
    ONE_EURO_BETA,
    ONE_EURO_DCUTOFF,
)

from core.tracker import Landmark
from core.filter import OneEuroFilter
from core.display import VirtualDesktop, TrackpadZone, map_to_desktop
from core.actuator import MouseActuator
from core.gestures.utils import dist3d, is_four_fingers

logger = logging.getLogger(__name__)

# Evita reativação por pequenas oscilações após soltar.
LEFT_PINCH_REARM_FRAMES = 3


class _State(Enum):
    IDLE = auto()
    PINCHING = auto()


class RightHandProcessor:
    """Processes right-hand landmarks on each camera frame."""

    def __init__(
        self,
        actuator: MouseActuator,
        desktop: VirtualDesktop,
        trackpad: TrackpadZone,
    ) -> None:
        self._actuator = actuator
        self._desktop = desktop
        self._trackpad = trackpad

        self._state = _State.IDLE

        self._last_gesture_time = 0.0
        self._click_cooldown_frames = 0

        self._four_since = None
        self._four_fired = False

        self._thumb_idx_pinching = False
        self._thumb_mid_pinching = False

        self._pinch_confirm_frames = 0
        self._pinch_release_frames = 0

        self._d_thumb_mid_filtered = None

        self._filter_x = OneEuroFilter(
            freq=float(CAMERA_FPS),
            mincutoff=ONE_EURO_MINCUTOFF,
            beta=ONE_EURO_BETA,
            dcutoff=ONE_EURO_DCUTOFF,
        )
        self._filter_y = OneEuroFilter(
            freq=float(CAMERA_FPS),
            mincutoff=ONE_EURO_MINCUTOFF,
            beta=ONE_EURO_BETA,
            dcutoff=ONE_EURO_DCUTOFF,
        )

    def process(
        self,
        landmarks: list[Landmark] | None,
        frame_size: tuple[int, int] | None = None,
    ) -> None:

        if self._click_cooldown_frames > 0:
            self._click_cooldown_frames -= 1

        if landmarks is None:
            self._state = _State.IDLE

            self._thumb_idx_pinching = False
            self._thumb_mid_pinching = False

            self._pinch_confirm_frames = 0
            self._pinch_release_frames = 0

            self._d_thumb_mid_filtered = None

            self._four_since = None
            self._four_fired = False
            return

        now = time.perf_counter()

        # frame_size = (width, height)
        if frame_size is None:
            from config import CAMERA_WIDTH, CAMERA_HEIGHT
            width, height = CAMERA_WIDTH, CAMERA_HEIGHT
        else:
            width, height = frame_size

        four_fingers = is_four_fingers(landmarks)

        # Distância em pixels entre polegar (4) e indicador (8).
        dx = (landmarks[4].x - landmarks[8].x) * width
        dy = (landmarks[4].y - landmarks[8].y) * height
        pinch_distance_px = math.hypot(dx, dy)

        # Distâncias 3D para reconhecimento das pinças.
        raw_idx_3d = dist3d(landmarks[4], landmarks[8])
        raw_mid = dist3d(landmarks[4], landmarks[12])

        # Suavização da distância polegar-médio.
        alpha = 0.35

        if self._d_thumb_mid_filtered is None:
            self._d_thumb_mid_filtered = raw_mid
        else:
            self._d_thumb_mid_filtered += alpha * (
                raw_mid - self._d_thumb_mid_filtered
            )

        d_thumb_mid = self._d_thumb_mid_filtered

        # Confirm one click per pinch; hysteresis prevents jitter from rearming it.
        if self._thumb_idx_pinching:
            if pinch_distance_px >= PINCH_RELEASE_PX:
                self._pinch_release_frames += 1

                if self._pinch_release_frames >= LEFT_PINCH_REARM_FRAMES:
                    self._thumb_idx_pinching = False
                    self._pinch_release_frames = 0
                    self._state = _State.IDLE

                    logger.debug(
                        "Pinça liberada: %.1f px",
                        pinch_distance_px,
                    )
            else:
                self._pinch_release_frames = 0

        else:
            if pinch_distance_px < PINCH_ENTER_PX:
                self._pinch_confirm_frames += 1

                if self._pinch_confirm_frames >= PINCH_CONFIRM_FRAMES:
                    self._thumb_idx_pinching = True
                    self._pinch_confirm_frames = 0
                    self._pinch_release_frames = 0
                    self._state = _State.PINCHING

                    logger.info(
                        "PINÇA CONFIRMADA | %.1f px",
                        pinch_distance_px,
                    )

                    if self._click_cooldown_frames == 0:
                        self._actuator.left_click()
                        self._click_cooldown_frames = (
                            PINCH_CLICK_COOLDOWN_FRAMES
                        )
                        logger.info("Clique esquerdo")
            else:
                self._pinch_confirm_frames = 0

        # Clique direito: polegar + dedo médio.
        # Ambas as distâncias são comparadas na mesma escala 3D.
        middle_is_closer = (
            d_thumb_mid + 0.025 < raw_idx_3d
        )

        if self._thumb_mid_pinching:
            if d_thumb_mid > 0.075 or not middle_is_closer:
                self._thumb_mid_pinching = False

        elif d_thumb_mid < min(THUMB_MIDDLE_CLICK_DIST, 0.050):
            if middle_is_closer and not self._thumb_idx_pinching:
                self._thumb_mid_pinching = True

        # Win+Tab: quatro dedos estendidos por 250 ms.
        if four_fingers:
            if self._four_since is None:
                self._four_since = now

            if (
                not self._four_fired
                and now - self._four_since >= 0.25
                and now - self._last_gesture_time
                >= GESTURE_COOLDOWN_SECONDS
            ):
                self._actuator.win_tab()
                self._last_gesture_time = now
                self._four_fired = True
                logger.info("Win+Tab: quatro dedos")

            return

        else:
            self._four_since = None
            self._four_fired = False

        # Clique direito.
        if (
            self._thumb_mid_pinching
            and self._state == _State.IDLE
            and now - self._last_gesture_time
            >= GESTURE_COOLDOWN_SECONDS
        ):
            self._actuator.right_click()
            self._last_gesture_time = now
            logger.info("Clique direito")
            return

        # Movimento do cursor.
        filtered_x = self._filter_x(landmarks[8].x, now)
        filtered_y = self._filter_y(landmarks[8].y, now)

        screen_x, screen_y = map_to_desktop(
            filtered_x,
            filtered_y,
            self._trackpad,
            self._desktop,
        )

        self._actuator.move(screen_x, screen_y)
