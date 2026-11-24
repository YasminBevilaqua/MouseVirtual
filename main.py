
# main.py
"""
AI Air Mouse — Entry point.

Startup sequence (ORDER MATTERS):
  1. Configure logging
  2. Set Windows timer resolution to 1ms
  3. Elevate process to HIGH_PRIORITY_CLASS
  4. Register main thread with MMCSS ("Games" profile)
  5. Build virtual desktop + trackpad zone
  6. Disable Windows pointer acceleration (restore on exit)
  7. Start async camera
  8. Start MediaPipe hand tracker
  9. Instantiate gesture processor + actuator
  10. Run inference loop
  11. On exit: restore Windows settings and release resources

Exit handling:
  - Ctrl+C -> clean shutdown
  - Q on camera window -> clean shutdown
  - Unhandled exception -> log traceback, then clean shutdown
  - atexit handler -> safety net for Windows settings restoration
"""

import atexit
import ctypes
import logging
import os
import time
import traceback

import psutil
import cv2

from config import PROCESS_PRIORITY, TIMER_RESOLUTION_MS, DEBUG_GESTURES
from core.camera import AsyncCamera
from core.tracker import HandTracker
from core.gestures import GestureOrchestrator
from core.actuator import MouseActuator
from core.display import build_virtual_desktop, build_trackpad_zone

# Importa o overlay para permitir desenhar pontos e informações.
from core.debug_overlay import draw_debug_frame


# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("airmouse.main")


# ── Windows OS Setup ──────────────────────────────────────────────────────────

def _apply_windows_performance() -> dict:
    """Apply Windows performance settings and save original values."""
    original = {}

    # 1. Timer resolution
    try:
        winmm = ctypes.windll.winmm
        winmm.timeBeginPeriod(TIMER_RESOLUTION_MS)
        original["timer_period"] = TIMER_RESOLUTION_MS
        logger.info(
            "Windows timer resolution set to %dms",
            TIMER_RESOLUTION_MS,
        )
    except Exception as e:
        logger.warning("Failed to set timer resolution: %s", e)

    # 2. Process priority
    try:
        proc = psutil.Process(os.getpid())
        proc.nice(PROCESS_PRIORITY)
        logger.info(
            "Process priority set to HIGH_PRIORITY_CLASS (0x%X)",
            PROCESS_PRIORITY,
        )
    except psutil.AccessDenied:
        logger.warning(
            "Could not elevate process priority — "
            "run as administrator for best performance"
        )

    # 3. MMCSS
    try:
        avrt = ctypes.windll.avrt
        task_index = ctypes.c_ulong(0)
        avrt.AvSetMmThreadCharacteristicsW.restype = ctypes.c_void_p

        handle = avrt.AvSetMmThreadCharacteristicsW(
            "Games",
            ctypes.byref(task_index),
        )

        if handle:
            original["mmcss_handle"] = handle
            logger.info(
                "MMCSS thread registered as 'Games' (handle=%d)",
                handle,
            )
        else:
            logger.warning("MMCSS registration returned NULL handle")

    except Exception as e:
        logger.warning("MMCSS registration failed: %s", e)

    # 4. Disable Windows pointer acceleration
    original_mouse_params = (ctypes.c_int * 3)(0, 0, 0)

    get_result = ctypes.windll.user32.SystemParametersInfoW(
        3, 0, original_mouse_params, 0
    )

    if not get_result:
        logger.warning(
            "SystemParametersInfoW(SPI_GETMOUSE) failed — "
            "cannot save/restore mouse settings"
        )
    else:
        original["mouse_params"] = list(original_mouse_params)

        no_accel = (ctypes.c_int * 3)(0, 0, 0)

        set_result = ctypes.windll.user32.SystemParametersInfoW(
            4, 0, no_accel, 2
        )

        if not set_result:
            logger.warning(
                "SystemParametersInfoW(SPI_SETMOUSE) failed — "
                "pointer acceleration may not be disabled"
            )
        else:
            logger.info("Windows pointer acceleration disabled")

    return original


def _restore_windows_settings(original: dict) -> None:
    """Restore all Windows settings mutated during startup."""

    if "timer_period" in original:
        ctypes.windll.winmm.timeEndPeriod(original["timer_period"])
        logger.info("Windows timer resolution restored")

    if "mmcss_handle" in original:
        try:
            ctypes.windll.avrt.AvRevertMmThreadCharacteristics(
                original["mmcss_handle"]
            )
            logger.info("MMCSS thread unregistered")
        except Exception as e:
            logger.warning("MMCSS revert failed: %s", e)

    if "mouse_params" in original:
        restored = (ctypes.c_int * 3)(
            *original["mouse_params"]
        )

        ctypes.windll.user32.SystemParametersInfoW(
            4, 0, restored, 2
        )

        logger.info("Windows pointer acceleration restored")


# ── Main Loop ─────────────────────────────────────────────────────────────────

def run() -> None:
    original_settings: dict = {}

    # Performance measurements
    perf = {
        "n": 0,
        "tracker": 0.0,
        "gestures": 0.0,
        "clock": time.perf_counter(),
    }

    def _emergency_restore():
        """atexit safety net."""
        if original_settings:
            _restore_windows_settings(original_settings)

    atexit.register(_emergency_restore)

    logger.info("=== AI Air Mouse starting ===")

    original_settings.update(_apply_windows_performance())

    desktop = build_virtual_desktop()
    trackpad = build_trackpad_zone()

    actuator = MouseActuator(
        desktop.total_width,
        desktop.total_height,
    )

    frame_count = 0
    fps_clock = time.perf_counter()
    none_count = 0

    with AsyncCamera() as camera, HandTracker() as tracker:
        processor = GestureOrchestrator(
            actuator,
            desktop,
            trackpad,
        )

        logger.info(
            "Running. Press Q on the camera window or Ctrl+C to exit."
        )

        try:
            while True:
                frame = camera.read()

                if frame is None:
                    none_count += 1

                    if none_count > 5000:
                        logger.error(
                            "Camera produced no frames for ~5 seconds — "
                            "camera may be disconnected"
                        )
                        break

                    time.sleep(0.001)
                    continue

                none_count = 0

                # ── MediaPipe hand tracking ──
                t0 = time.perf_counter()
                hands = tracker.process(frame)
                t1 = time.perf_counter()

                # ── Gesture processing ──
                height, width = frame.shape[:2]
                processor.process(hands, (width, height))
                t2 = time.perf_counter()

                perf["n"] += 1
                perf["tracker"] += t1 - t0
                perf["gestures"] += t2 - t1

                # ── Camera + hand landmarks + debug overlay ──
                if DEBUG_GESTURES:
                    display_frame = draw_debug_frame(
                        frame.copy(),
                        hands,
                        processor.right_state,
                    )
                else:
                    display_frame = frame.copy()

                cv2.imshow(
                    "AI Air Mouse - Camera",
                    cv2.resize(
                        display_frame,
                        None,
                        fx=0.5,
                        fy=0.5,
                        interpolation=cv2.INTER_AREA,
                    ),
                )

                # Pressione Q com a janela selecionada para sair.
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

                # ── FPS and performance telemetry ──
                frame_count += 1
                now = time.perf_counter()

                if now - fps_clock >= 5.0:
                    fps = frame_count / (now - fps_clock)
                    logger.info("FPS: %.1f", fps)

                    n = perf["n"]

                    if n > 0:
                        logger.info(
                            "PERF | MediaPipe: %.1f ms | Gestos: %.1f ms",
                            perf["tracker"] * 1000 / n,
                            perf["gestures"] * 1000 / n,
                        )

                    frame_count = 0
                    fps_clock = now

                    # Reset measurement window
                    perf = {
                        "n": 0,
                        "tracker": 0.0,
                        "gestures": 0.0,
                        "clock": now,
                    }

        except KeyboardInterrupt:
            logger.info("Ctrl+C received — shutting down cleanly")

        except Exception:
            logger.error(
                "Unhandled exception:\n%s",
                traceback.format_exc(),
            )

        finally:
            cv2.destroyAllWindows()

            if actuator.is_dragging:
                actuator.drag_end()

            _restore_windows_settings(original_settings)
            original_settings.clear()

            logger.info("=== AI Air Mouse stopped ===")


if __name__ == "__main__":
    run()
