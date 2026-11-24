import cv2

from core.camera import AsyncCamera
from core.tracker import HandTracker
from core.gestures.utils import (
    is_fist,
    is_peace_sign,
    is_open_palm,
    is_v_sign,
    is_four_fingers,
    dist3d,
)


def draw_hand_status(frame, landmarks, title, x, y, color):
    cv2.putText(
        frame, title, (x, y),
        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2
    )

    if landmarks is None:
        cv2.putText(
            frame, "Mao nao detectada", (x, y + 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1
        )
        return

    thumb_index = dist3d(landmarks[4], landmarks[8])
    thumb_middle = dist3d(landmarks[4], landmarks[12])

    results = [
        ("Punho fechado", is_fist(landmarks)),
        ("Sinal de paz", is_peace_sign(landmarks)),
        ("Palma aberta", is_open_palm(landmarks)),
        ("Sinal V", is_v_sign(landmarks)),
        ("Quatro dedos", is_four_fingers(landmarks)),
        ("Pinca indicador", thumb_index < 0.060),
        ("Pinca medio", thumb_middle < 0.065),
    ]

    for i, (name, detected) in enumerate(results):
        status = "SIM" if detected else "nao"
        text = f"{name}: {status}"
        cv2.putText(
            frame, text, (x, y + 25 + i * 23),
            cv2.FONT_HERSHEY_SIMPLEX, 0.48,
            (0, 255, 0) if detected else (190, 190, 190), 1
        )


print("DIAGNOSTICO SEGURO: nenhum mouse ou atalho sera acionado.")
print("Pressione Q ou ESC para sair.")

with AsyncCamera() as camera, HandTracker() as tracker:
    while True:
        frame = camera.read()
        if frame is None:
            continue

        hands = tracker.process(frame)

        draw_hand_status(
            frame, hands.right, "MAO DIREITA", 15, 25, (0, 255, 0)
        )
        draw_hand_status(
            frame, hands.left, "MAO ESQUERDA", 340, 25, (0, 165, 255)
        )

        cv2.imshow("Diagnostico de gestos - seguro", frame)
        key = cv2.waitKey(1) & 0xFF

        if key in (ord("q"), 27):
            break

    cv2.destroyAllWindows()
