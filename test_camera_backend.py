import cv2
import time

for name, backend in [
    ("AUTO", cv2.CAP_ANY),
    ("MSMF", cv2.CAP_MSMF),
    ("DSHOW", cv2.CAP_DSHOW),
]:
    cap = cv2.VideoCapture(0, backend)
    print(f"\n{name}: aberta={cap.isOpened()}")

    if cap.isOpened():
        for i in range(5):
            ok, frame = cap.read()
            brilho = round(float(frame.mean()), 2) if ok and frame is not None else -1
            print(f"  Quadro {i+1}: recebido={ok}, brilho={brilho}")
            time.sleep(0.2)

    cap.release()
