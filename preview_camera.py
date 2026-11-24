import cv2
import time

cap = cv2.VideoCapture(0, cv2.CAP_MSMF)

if not cap.isOpened():
    print("Não foi possível abrir a câmera.")
    raise SystemExit(1)

print("Câmera aberta. Pressione Q para fechar a janela.")

try:
    while True:
        ok, frame = cap.read()

        if not ok or frame is None:
            print("Falha ao receber quadro.")
            break

        cv2.imshow("Teste Camo - pressione Q para sair", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    cap.release()
    cv2.destroyAllWindows()
