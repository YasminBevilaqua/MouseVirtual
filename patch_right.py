from pathlib import Path
import shutil

path = Path("core/gestures/right_hand.py")
source = path.read_text(encoding="utf-8")

start = source.find("        # Compute wrist velocity")
end = source.find(
    "        if (\n            d_thumb_mid < THUMB_MIDDLE_CLICK_DIST",
    start
)

if start == -1 or end == -1:
    raise SystemExit(
        "ERRO: não encontrei os trechos esperados. Nenhuma alteração foi feita."
    )

backup = path.with_suffix(".py.before_gestures.bak")
if not backup.exists():
    shutil.copy2(path, backup)

source = source[:start] + '''        four_fingers = is_four_fingers(landmarks)
        d_thumb_idx = dist3d(landmarks[4], landmarks[8])
        d_thumb_mid = dist3d(landmarks[4], landmarks[12])
        thumb_idx_pinch = d_thumb_idx < THUMB_INDEX_CLICK_DIST

        # Win+Tab: quatro dedos estendidos e polegar recolhido.
        if four_fingers:
            if self._four_since is None:
                self._four_since = now

            if (
                not self._four_fired
                and now - self._four_since >= 0.25
                and now - self._last_gesture_time >= GESTURE_COOLDOWN_SECONDS
            ):
                self._actuator.win_tab()
                self._last_gesture_time = now
                self._four_fired = True
                logger.debug("Win+Tab: quatro dedos")
            return
        else:
            self._four_since = None
            self._four_fired = False

''' + source[end:]

source = source.replace(
    "from core.gestures.utils import dist3d, is_fist, is_peace_sign",
    "from core.gestures.utils import dist3d, is_four_fingers"
)

source = source.replace("    SCROLLING = auto()\n", "")
source = source.replace("    LOCKED = auto()\n", "")
source = source.replace("        self._last_scroll_time: float = 0.0\n", "")
source = source.replace(
    "        self._prev_wrist_y: float | None = None\n"
    "        self._last_frame_time: float | None = None",
    "        self._four_since: float | None = None\n"
    "        self._four_fired: bool = False"
)
source = source.replace(
    "            self._prev_wrist_y = None\n"
    "            self._last_frame_time = None",
    "            self._four_since = None\n"
    "            self._four_fired = False"
)

if "is_fist(landmarks)" in source or "is_peace_sign(landmarks)" in source:
    raise SystemExit(
        "ERRO: ainda há chamadas das gestões antigas. Arquivo não foi salvo."
    )

path.write_text(source, encoding="utf-8")
print("Correção aplicada em right_hand.py")
print(f"Backup: {backup}")
