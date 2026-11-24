
"""Gesture processor for the left hand."""

import logging
import time

from config import GESTURE_COOLDOWN_SECONDS
from core.tracker import Landmark
from core.actuator import MouseActuator
from core.gestures.utils import is_fist, is_v_sign, is_four_fingers

logger = logging.getLogger(__name__)

GESTURE_HOLD_SECONDS = 0.18


class LeftHandProcessor:
    """Recognizes left-hand gestures and triggers window actions."""

    def __init__(self, actuator: MouseActuator) -> None:
        self._actuator = actuator
        self._last_gesture_time = 0.0
        self._candidate = None
        self._candidate_since = None
        self._fired = False

    def process(self, landmarks: list[Landmark] | None) -> None:
        """Process landmarks and trigger a gesture after a short hold."""

        if landmarks is None:
            self._candidate = None
            self._candidate_since = None
            self._fired = False
            return

        now = time.perf_counter()

        if is_fist(landmarks):
            gesture = "minimize"
        elif is_v_sign(landmarks):
            gesture = "close"
        elif is_four_fingers(landmarks):
            gesture = "alt_tab"
        else:
            gesture = None

        if gesture != self._candidate:
            self._candidate = gesture
            self._candidate_since = now
            self._fired = False
            return

        if (
            gesture is None
            or self._fired
            or self._candidate_since is None
        ):
            return

        if now - self._candidate_since < GESTURE_HOLD_SECONDS:
            return

        if now - self._last_gesture_time < GESTURE_COOLDOWN_SECONDS:
            return

        if gesture == "minimize":
            self._actuator.minimize_window()
            logger.debug("Minimize active window (left fist)")

        elif gesture == "close":
            self._actuator.close_window()
            logger.debug("Close active tab/window (left V)")

        elif gesture == "alt_tab":
            self._actuator.alt_tab()
            logger.debug("Alt+Tab (left four fingers)")

        self._last_gesture_time = now
        self._fired = True
