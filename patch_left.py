from pathlib import Path
import shutil

path = Path("core/gestures/left_hand.py")
actuator_path = Path("core/actuator.py")

actuator = actuator_path.read_text(encoding="utf-8")
required = ["alt_tab", "minimize_window", "close_window"]
missing = [
    name for name in required
    if f"def {name}(" not in actuator
]

if missing:
    raise SystemExit(
        "Correção cancelada. Métodos não encontrados em core/actuator.py: "
        + ", ".join(missing)
    )

backup = path.with_suffix(".py.before_gestures.bak")
if not backup.exists():
    shutil.copy2(path, backup)

replacement = '''"""Left-hand gesture processor for Windows shortcuts."""

import time
import logging

from config import GESTURE_COOLDOWN_SECONDS
from core.tracker import Landmark
from core.actuator import MouseActuator
from core.gestures.utils import is_fist, is_v_sign, is_four_fingers

logger = logging.getLogger(__name__)

GESTURE_HOLD_SECONDS = 0.25


class LeftHandProcessor:
    """Recognizes stable left-hand gestures and triggers one shortcut."""

    def __init__(self, actuator: MouseActuator) -> None:
        self._actuator = actuator
        self._last_gesture_time = 0.0
        self._candidate: str | None = None
        self._candidate_since: float | None = None
        self._fired = False

    def process(self, landmarks: list[Landmark] | None) -> None:
        if landmarks is None:
            self._candidate = None
            self._candidate_since = None
            self._fired = False
            return

        now = time.perf_counter()

        # Priority matters: a fist must not be mistaken for another gesture.
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

        if gesture is None or self._fired or self._candidate_since is None:
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
            logger.debug("Close active window (left V)")
        elif gesture == "alt_tab":
            self._actuator.alt_tab()
            logger.debug("Alt+Tab (left four fingers)")

        self._last_gesture_time = now
        self._fired = True
'''

path.write_text(replacement, encoding="utf-8", newline="\n")
print("Correção aplicada em left_hand.py")
print(f"Backup: {backup}")
