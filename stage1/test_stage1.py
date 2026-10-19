import sys
import os

# 1. Ensure Python locates 'utils' from the parent root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import cv2
import math
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 2. Import landmark indices and metrics from the utils package
try:
    from utils.landmarks import (
        LEFT_EYE, RIGHT_EYE, LEFT_IRIS_CENTER, RIGHT_IRIS_CENTER,
        MOUTH_CALC, MOUTH_OUTER, NOSE_TIP
    )
    from utils.metrics import get_ear, get_mar, get_iris_coords
except ModuleNotFoundError:
    LEFT_EYE = [362, 385, 387, 263, 373, 380]
    RIGHT_EYE = [33, 160, 158, 133, 153, 144]
    LEFT_IRIS_CENTER = [474, 475, 476, 477]
    RIGHT_IRIS_CENTER = [469, 470, 471, 472]
    NOSE_TIP = 1
    MOUTH_CALC = [13, 14, 78, 308]
    MOUTH_OUTER = [
        61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291,
        308, 324, 318, 402, 317, 14, 87, 178, 88, 95
    ]

    def euclidean_dist(pt1, pt2):
        return math.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])

    def get_ear(indices, landmarks, w, h):
        pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
        v1 = euclidean_dist(pts[1], pts[5])
        v2 = euclidean_dist(pts[2], pts[4])
        horiz = euclidean_dist(pts[0], pts[3])
        return (v1 + v2) / (2.0 * horiz) if horiz > 0 else 0.0

    def get_mar(indices, landmarks, w, h):
        pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
        vert = euclidean_dist(pts[0], pts[1])
        horiz = euclidean_dist(pts[2], pts[3])
        return vert / horiz if horiz > 0 else 0.0

    def get_iris_coords(indices, landmarks, w, h):
        pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        return int(round(cx)), int(round(cy))

# 3. Model path verification
MODEL_PATH = os.path.join(PROJECT_ROOT, "face_landmarker.task")

def check_model_exists():
    if not os.path.exists(MODEL_PATH):
        print("\n" + "=" * 65)
        print(f"❌ Model file missing at: {MODEL_PATH}")
        print("Please download 'face_landmarker.task' and put it in:")
        print(f"{PROJECT_ROOT}")
        print("=" * 65 + "\n")
        sys.exit(1)
    else:
        print(f"✅ Found model task file at: {MODEL_PATH}")

def main():
    check_model_exists()

    # Initialize MediaPipe Task API
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5
    )
    detector = vision.FaceLandmarker.create_from_options(options)

    # Initialize Webcam
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("❌ Cannot access the webcam. Check camera permissions.")
        return

    print("\n" + "=" * 55)
    print("🚀 STAGE 1 VALIDATION FEED ACTIVE")
    print("• Blue dots: Eye outlines")
    print("• Green dots: Iris tracking centers")
    print("• Yellow dots: Mouth outline")
    print("• Cyan dot: Nose reference anchor")
    print("• Bottom HUD: Live EAR and MAR numerical readouts")
    print("• Press [Q] or [ESC] to exit")
    print("=" * 55 + "\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_img)

        l_ear, r_ear, mar = 0.0, 0.0, 0.0

        if result.face_landmarks and len(result.face_landmarks) > 0:
            lm = result.face_landmarks[0]

            l_ear = get_ear(LEFT_EYE, lm, w, h)
            r_ear = get_ear(RIGHT_EYE, lm, w, h)
            mar = get_mar(MOUTH_CALC, lm, w, h)

            # Draw Eyes (Blue points)
            for idx in LEFT_EYE + RIGHT_EYE:
                cv2.circle(frame, (int(round(lm[idx].x * w)), int(round(lm[idx].y * h))), 2, (255, 120, 0), -1)

            # Draw Iris Centers (Green points) - explicitly cast to integer
            l_ix, l_iy = get_iris_coords(LEFT_IRIS_CENTER, lm, w, h)
            r_ix, r_iy = get_iris_coords(RIGHT_IRIS_CENTER, lm, w, h)
            cv2.circle(frame, (int(round(l_ix)), int(round(l_iy))), 4, (0, 255, 0), -1)
            cv2.circle(frame, (int(round(r_ix)), int(round(r_iy))), 4, (0, 255, 0), -1)

            # Draw Mouth Contour (Yellow points)
            for idx in MOUTH_OUTER:
                cv2.circle(frame, (int(round(lm[idx].x * w)), int(round(lm[idx].y * h))), 2, (0, 255, 255), -1)

            # Draw Nose Tip Anchor (Cyan point)
            cv2.circle(frame, (int(round(lm[NOSE_TIP].x * w)), int(round(lm[NOSE_TIP].y * h))), 5, (255, 255, 0), -1)

        # Bottom HUD strip
        cv2.rectangle(frame, (0, h - 50), (w, h), (20, 20, 20), -1)
        hud_text = f"L-EAR: {l_ear:.2f} | R-EAR: {r_ear:.2f} | MAR: {mar:.2f} | Face: {'DETECTED' if result.face_landmarks else 'SEARCHING...'}"
        cv2.putText(frame, hud_text, (25, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

        cv2.imshow("Stage 1 - Facial Metrics Validation", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in [ord('q'), 27]:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()