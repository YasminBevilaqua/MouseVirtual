from collections import deque
import time
import math
import cv2
from core.camera import AsyncCamera
from core.tracker import HandTracker

def dist(a, b, use_z=False):
    dx = a.x - b.x
    dy = a.y - b.y
    dz = a.z - b.z if use_z else 0.0
    return math.sqrt(dx*dx + dy*dy + dz*dz)

samples = {
    "Indicador 2D": deque(maxlen=240),
    "Indicador 3D": deque(maxlen=240),
    "Medio 2D": deque(maxlen=240),
    "Medio 3D": deque(maxlen=240),
}
last_report = time.perf_counter()

print("Mantenha cada pinça por alguns segundos.")
print("Os resultados sao atualizados aproximadamente a cada 2 segundos.")
print("Pressione Q para sair.")

with AsyncCamera() as camera, HandTracker() as tracker:
    try:
        while True:
            frame = camera.read()
            if frame is None:
                continue

            hands = tracker.process(frame)
            hand = hands.right
            now = time.perf_counter()

            if hand is not None:
                values = {
                    "Indicador 2D": dist(hand[4], hand[8]),
                    "Indicador 3D": dist(hand[4], hand[8], True),
                    "Medio 2D": dist(hand[4], hand[12]),
                    "Medio 3D": dist(hand[4], hand[12], True),
                }
                for name, value in values.items():
                    samples[name].append(value)

                lines = ["Distancias brutas | Q = sair"]
                for name, value in values.items():
                    lines.append(f"{name}: {value:.3f}")
            else:
                lines = ["Mao direita nao detectada", "Q = sair"]

            if now - last_report >= 2.0 and hand is not None:
                print("\n--- Ultimos ~2 segundos ---")
                for name, data in samples.items():
                    if data:
                        ordered = sorted(data)
                        median = ordered[len(ordered)//2]
                        print(
                            f"{name}: min={min(data):.3f}, "
                            f"mediana={median:.3f}, max={max(data):.3f}"
                        )
                last_report = now

            y = 30
            for line in lines:
                cv2.putText(
                    frame, line, (15, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 255, 0), 2, cv2.LINE_AA
                )
                y += 28

            cv2.imshow("Diagnostico de Pinças", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cv2.destroyAllWindows()
