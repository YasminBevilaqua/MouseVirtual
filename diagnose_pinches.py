import time
import math
import cv2
from core.camera import AsyncCamera
from core.tracker import HandTracker

def distance2d(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

def distance3d(a, b):
    return math.sqrt(
        (a.x - b.x)**2 +
        (a.y - b.y)**2 +
        (a.z - b.z)**2
    )

print("Diagnóstico de pinças iniciado. Pressione Q para sair.")
print("Mantenha a mão visível e teste cada pinça separadamente.")

with AsyncCamera() as camera, HandTracker() as tracker:
    try:
        while True:
            frame = camera.read()
            if frame is None:
                time.sleep(0.005)
                continue

            hands = tracker.process(frame)
            hand = hands.right

            if hand is not None:
                ti2 = distance2d(hand[4], hand[8])
                ti3 = distance3d(hand[4], hand[8])
                tm2 = distance2d(hand[4], hand[12])
                tm3 = distance3d(hand[4], hand[12])

                lines = [
                    f"Indicador  2D: {ti2:.3f} | 3D: {ti3:.3f}",
                    f"Medio      2D: {tm2:.3f} | 3D: {tm3:.3f}",
                    "Teste cada pinça separadamente",
                    "Q = sair",
                ]
            else:
                lines = ["Mao direita nao detectada", "Q = sair"]

            y = 30
            for line in lines:
                cv2.putText(
                    frame, line, (15, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    (0, 255, 0), 2, cv2.LINE_AA
                )
                y += 30

            cv2.imshow("Diagnostico de Pinças", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cv2.destroyAllWindows()
