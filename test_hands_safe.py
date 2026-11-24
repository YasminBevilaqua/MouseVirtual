import cv2
from core.camera import AsyncCamera
from core.tracker import HandTracker

print("Modo de diagnóstico: mouse e atalhos desativados.")
print("Q ou ESC para sair.")

with AsyncCamera() as camera, HandTracker() as tracker:
    while True:
        frame = camera.read()
        if frame is None:
            continue

        hands = tracker.process(frame)

        if hands.right is not None:
            label_r = "DETECTADA"
        else:
            label_r = "ausente"

        if hands.left is not None:
            label_l = "DETECTADA"
        else:
            label_l = "ausente"

        cv2.putText(
            frame, f"MAO DIREITA: {label_r}", (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
        )
        cv2.putText(
            frame, f"MAO ESQUERDA: {label_l}", (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2
        )

        cv2.imshow("Diagnostico seguro - Air Mouse", frame)
        key = cv2.waitKey(1) & 0xFF

        if key in (ord("q"), 27):
            break

    cv2.destroyAllWindows()
