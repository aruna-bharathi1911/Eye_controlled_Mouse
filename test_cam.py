import cv2

# Check indices 0, 1, and 2
for idx in [0, 1, 2]:
    cap = cv2.VideoCapture(idx)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"Camera found at index: {idx}")
            cv2.imshow(f"Testing Camera Index {idx}", frame)
            cv2.waitKey(2000)  # Shows frame for 2 seconds
            cv2.destroyAllWindows()
        cap.release()