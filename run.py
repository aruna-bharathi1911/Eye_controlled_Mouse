import os
import sys
import math
import time
import json
import threading
import urllib.request
import socket
import cv2
import pyautogui
from PIL import Image
import customtkinter as ctk

# --- IMPORT MVC COMPONENTS ---
from ui import EyeMouseUI
from actions.cursor_controller import CursorController
from actions.click_controller import ClickController
from actions.scroll_controller import ScrollController
from actions.drag_controller import DragController

pyautogui.PAUSE = 0.0
pyautogui.FAILSAFE = False

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils import database as db

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Landmark indices
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
NOSE_TIP = 1
MOUTH_CALC = [13, 14, 78, 308]
MOUTH_OUTER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]

def euclidean_dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def get_ear(indices, landmarks, w, h):
    pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
    a = euclidean_dist(pts[1], pts[5])
    b = euclidean_dist(pts[2], pts[4])
    c = euclidean_dist(pts[0], pts[3])
    return (a + b) / (2.0 * c) if c > 0 else 0.0

def get_mar(indices, landmarks, w, h):
    pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
    v = euclidean_dist(pts[0], pts[1])
    ho = euclidean_dist(pts[2], pts[3])
    return v / ho if ho > 0 else 0.0


class SystemController:
    def __init__(self):
        self.config_path = os.path.join(PROJECT_ROOT, "config.json")
        db.init_db()
        last_ip = db.get_last_ip()
        self.saved_ip = last_ip or self.load_config()

        model_path = os.path.join(PROJECT_ROOT, "face_landmarker.task")
        if not os.path.exists(model_path) or os.path.getsize(model_path) < 1000000:
            urllib.request.urlretrieve(
                "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
                model_path
            )
        with open(model_path, "rb") as f:
            model_data = f.read()

        options = vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_buffer=model_data),
            running_mode=vision.RunningMode.IMAGE,
            num_faces=4,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector = vision.FaceLandmarker.create_from_options(options)

        self.cursor = CursorController()
        self.clicker = ClickController()
        self.scroller = ScrollController()
        self.dragger = DragController()

        self.locked_face_center = None
        self.last_seen_time = 0.0
        self.neutral_nose = None
        self.is_calibrated = False

        self.l_ear_history = []
        self.r_ear_history = []
        self.ear_threshold = 0.20       
        self.mar_threshold = 0.32
        
        self.both_closed = False
        self.control_mode = 0 
        self.mouth_open_start = 0.0
        self.mouth_ready = False
        self.last_toggle = 0.0

        self.hud_action_text = ""
        self.hud_action_color = (0, 255, 0)
        self.hud_action_expiry = 0.0

        self.cap = None
        self.is_running = False
        self.current_ctk_image = None
        self.latest_status = {}

        # Initialize the View (UI) and pass the callbacks
        self.ui = EyeMouseUI(
            start_cmd=self.start_camera,
            stop_cmd=self.stop_camera,
            calib_cmd=self.recalibrate,
            exit_cmd=self.on_close,
            saved_ip=self.saved_ip
        )

        self._ui_refresh_loop()

    def run(self):
        self.ui.mainloop()

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    return data.get("droidcam_ip", "")
            except:
                return ""
        return ""

    def save_config(self, ip):
        try:
            with open(self.config_path, "w") as f:
                json.dump({"droidcam_ip": ip}, f)
        except Exception as e:
            pass

    def recalibrate(self):
        self.is_calibrated = False
        self.locked_face_center = None
        self.neutral_nose = None
        self.both_closed = False
        self.l_ear_history.clear()
        self.r_ear_history.clear()
        self.cursor.reset()
        self.clicker.reset()
        self.dragger.reset()
        self.scroller.is_scroll_mode = False
        self.scroller.blink_start_time = 0.0
        self.scroller.has_toggled_this_blink = False
        self.scroller.eyes_are_closed = False

    def _get_locked_face(self, face_landmarks_list, w, h, now):
        if not face_landmarks_list:
            if self.locked_face_center and (now - self.last_seen_time > 1.5):
                self.locked_face_center = None
                self.is_calibrated = False
            return None

        face_candidates = []
        for lm in face_landmarks_list:
            nx = lm[NOSE_TIP].x * w
            ny = lm[NOSE_TIP].y * h
            eye_y = (lm[33].y + lm[263].y) / 2.0 * h
            mouth_y = lm[14].y * h
            face_size = abs(mouth_y - eye_y)
            face_candidates.append({"landmarks": lm, "center": (nx, ny), "size": face_size})

        if self.locked_face_center is None:
            primary_face = max(face_candidates, key=lambda f: f["size"])
            self.locked_face_center = primary_face["center"]
            self.last_seen_time = now
            return primary_face["landmarks"]

        closest_face = min(
            face_candidates,
            key=lambda f: math.hypot(f["center"][0] - self.locked_face_center[0], f["center"][1] - self.locked_face_center[1])
        )
        dist_to_lock = math.hypot(
            closest_face["center"][0] - self.locked_face_center[0],
            closest_face["center"][1] - self.locked_face_center[1]
        )

        if dist_to_lock < 180:
            self.locked_face_center = (
                0.7 * self.locked_face_center[0] + 0.3 * closest_face["center"][0],
                0.7 * self.locked_face_center[1] + 0.3 * closest_face["center"][1]
            )
            self.last_seen_time = now
            return closest_face["landmarks"]
        else:
            return None

    def _resolve_droidcam_targets(self, ip_input):
        """
        Parses raw IP/port input into clean host, port, and stream candidate URLs.
        Handles cases like:
          - '192.168.1.5' (defaults to port 4747)
          - '192.168.1.5:4747'
          - 'http://192.168.1.5:4747/video'
          - 'http://192.168.1.5:4747/mjpegfeed'
        """
        raw = (ip_input or "").strip()
        raw = raw.replace("http://", "").replace("https://", "")
        # Remove any path suffix like /video or /mjpegfeed
        base = raw.split("/")[0].strip()
        if not base:
            return None, None, []
        if ":" in base:
            parts = base.split(":")
            host = parts[0].strip()
            try:
                port = int(parts[1].strip())
            except ValueError:
                port = 4747
        else:
            host = base
            port = 4747
        urls = [
            f"http://{host}:{port}/video",
            f"http://{host}:{port}/mjpegfeed",
        ]
        return host, port, urls

    def _test_host_reachable(self, host, port, timeout=1.8):
        """Quick network probe to verify phone IP/port is reachable over Wi-Fi."""
        try:
            sock = socket.create_connection((host, int(port)), timeout=timeout)
            sock.close()
            return True
        except Exception:
            return False

    def _open_droidcam_stream(self, urls):
        """Attempts to open MJPEG video stream using CAP_FFMPEG and default backends."""
        for url in urls:
            try:
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                if cap.isOpened():
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        return cap, url
                    cap.release()
            except Exception:
                pass

            try:
                cap = cv2.VideoCapture(url)
                if cap.isOpened():
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        return cap, url
                    cap.release()
            except Exception:
                pass
        return None, None

    def _try_open_physical_cam(self, idx):
        """Attempts to open a physical/virtual camera (e.g. DroidCam PC Client)."""
        try:
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
                ret, test_frame = cap.read()
                if ret and test_frame is not None:
                    return cap
                cap.release()
        except Exception:
            pass

        try:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
                ret, test_frame = cap.read()
                if ret and test_frame is not None:
                    return cap
                cap.release()
        except Exception:
            pass
        return None

    def start_camera(self):
        if not self.is_running:
            self.recalibrate()
            cam_choice = self.ui.get_cam_choice()
            ip_input = self.ui.get_ip_input()

            self.ui.update_camera_indicator("● CONNECTING...", is_active=False)
            self.ui.update_badge("camera", "Connecting...", "blue")

            threading.Thread(target=self._connect_camera_worker, args=(cam_choice, ip_input), daemon=True).start()

    def _connect_camera_worker(self, cam_choice, ip_input):
        cap = None
        cam_display = "Cam 0 ON"
        mirror_state = True

        is_ip_mode = "IP" in cam_choice or "Wi-Fi" in cam_choice
        is_cam1 = "Cam 1" in cam_choice or ("USB" in cam_choice and not is_ip_mode)
        is_cam2 = "Cam 2" in cam_choice

        if is_ip_mode:
            mirror_state = False
            host, port, urls = self._resolve_droidcam_targets(ip_input)
            if not host:
                self.ui.update_camera_indicator("● NO IP ENTERED", is_active=False)
                self.ui.update_badge("camera", "Enter Phone IP", "red")
                return

            # Test reachability with 1.8s timeout
            is_reachable = self._test_host_reachable(host, port, timeout=1.8)
            if not is_reachable:
                db.save_connection(f"{host}:{port}", status="Failed", notes="Unreachable on Wi-Fi")

                # Fallback: check if DroidCam PC Client / USB is available at Cam 1
                fallback_cap = self._try_open_physical_cam(1)
                if fallback_cap:
                    cap = fallback_cap
                    cam_display = "DroidCam Cam 1 (USB)"
                else:
                    self.ui.update_camera_indicator("● CANNOT REACH IP", is_active=False)
                    self.ui.update_badge("camera", f"Unreachable ({host})", "red")
                    return
            else:
                cap, success_url = self._open_droidcam_stream(urls)
                if cap is not None:
                    cam_display = "DroidCam IP ON"
                    self.save_config(f"{host}:{port}")
                    db.save_connection(f"{host}:{port}", status="Connected", notes=f"Stream: {success_url}")
                    self.ui.refresh_ip_list()
                else:
                    db.save_connection(f"{host}:{port}", status="Failed", notes="Stream decode failed")
                    self.ui.update_camera_indicator("● STREAM FAILED", is_active=False)
                    self.ui.update_badge("camera", "Stream Decode Error", "red")
                    return

        elif is_cam1:
            mirror_state = False
            cap = self._try_open_physical_cam(1)
            if not cap:
                cap = self._try_open_physical_cam(2)
                cam_display = "DroidCam Cam 2 ON" if cap else "Cam 1 ON"
            else:
                cam_display = "DroidCam Cam 1 ON"

        elif is_cam2:
            mirror_state = False
            cap = self._try_open_physical_cam(2)
            cam_display = "Cam 2 ON"

        else:
            # Standard Laptop Camera (Index 0)
            mirror_state = True
            cap = self._try_open_physical_cam(0)
            cam_display = "Laptop Cam ON"

        if cap is None or not cap.isOpened():
            self.ui.update_camera_indicator("● CONNECTION FAILED", is_active=False)
            self.ui.update_badge("camera", "Camera Not Found", "red")
            self.is_running = False
            return

        # Test grab a single frame to ensure feed is healthy
        ret, test_frame = cap.read()
        if not ret or test_frame is None:
            cap.release()
            self.ui.update_camera_indicator("● NO VIDEO FRAME", is_active=False)
            self.ui.update_badge("camera", "No Video Feed", "red")
            self.is_running = False
            return

        self.cap = cap
        self.ui.set_mirror_state(mirror_state)
        self.is_running = True
        self.ui.update_camera_indicator(f"● {cam_display}", is_active=True)
        self.ui.update_badge("camera", "Active", "green")

        threading.Thread(target=self._cv_worker, daemon=True).start()

    def stop_camera(self):
        self.is_running = False
        self.control_mode = 0
        if self.dragger.is_dragging:
            pyautogui.mouseUp(button='left')
            self.dragger.is_dragging = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
            
        self.ui.update_camera_indicator("● Camera OFF", is_active=False)
        self.ui.update_badge("camera", "Inactive", "red")
        self.ui.update_badge("face", "Searching...", "neutral")
        self.ui.update_badge("left_eye", "Unknown", "neutral")
        self.ui.update_badge("right_eye", "Unknown", "neutral")
        self.ui.update_badge("cursor", "Disabled", "red")
        self.ui.update_badge("click_action", "None", "neutral")
        self.ui.update_badge("mouth", "Closed", "neutral")
        self.ui.update_badge("mode", "Paused", "neutral")
        self.ui.clear_video_frame()

    def _cv_worker(self):
        consecutive_read_fails = 0
        while self.is_running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                consecutive_read_fails += 1
                if consecutive_read_fails > 45: # ~1.5s of failed frames
                    self.ui.update_camera_indicator("● FEED INTERRUPTED", is_active=False)
                    self.ui.update_badge("camera", "Feed Lost", "red")
                time.sleep(0.02)
                continue

            consecutive_read_fails = 0

            if self.ui.get_mirror_state():
                frame = cv2.flip(frame, 1)

            h, w = frame.shape[:2]
            now = time.time()

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.detector.detect(mp_img)

            lm = self._get_locked_face(result.face_landmarks, w, h, now)

            if lm is not None:
                self.latest_status["face"] = ("Locked (User)", "green")

                is_mirrored = self.ui.get_mirror_state()
                if is_mirrored:
                    raw_l_ear = get_ear(RIGHT_EYE, lm, w, h)
                    raw_r_ear = get_ear(LEFT_EYE, lm, w, h)
                else:
                    raw_l_ear = get_ear(LEFT_EYE, lm, w, h)
                    raw_r_ear = get_ear(RIGHT_EYE, lm, w, h)
                mar = get_mar(MOUTH_CALC, lm, w, h)

                self.l_ear_history.append(raw_l_ear)
                self.r_ear_history.append(raw_r_ear)
                if len(self.l_ear_history) > 3: self.l_ear_history.pop(0)
                if len(self.r_ear_history) > 3: self.r_ear_history.pop(0)

                l_ear = sum(self.l_ear_history) / len(self.l_ear_history)
                r_ear = sum(self.r_ear_history) / len(self.r_ear_history)

                # Robust Eye State Detection with Asymmetric Wink Disambiguation
                l_low = l_ear < self.ear_threshold
                r_low = r_ear < self.ear_threshold

                ear_diff = abs(l_ear - r_ear)
                # Significant asymmetry indicates an intentional single-eye wink
                is_asymmetric = (ear_diff >= 0.035) or (min(l_ear, r_ear) < max(l_ear, r_ear) * 0.72)

                if l_low and r_low:
                    if is_asymmetric:
                        # Winking one eye caused facial squinting on the other eye.
                        # The eye with significantly lower EAR is closed; the higher eye is open!
                        if l_ear < r_ear:
                            l_closed = True
                            r_closed = False
                        else:
                            l_closed = False
                            r_closed = True
                    else:
                        # Symmetrical drop: both eyes genuinely closed (blink / long blink)
                        l_closed = True
                        r_closed = True
                elif l_low and not r_low:
                    l_closed = True
                    r_closed = False
                elif r_low and not l_low:
                    l_closed = False
                    r_closed = True
                else:
                    # Neither is below threshold, but check for asymmetric drop near threshold
                    if is_asymmetric and min(l_ear, r_ear) < (self.ear_threshold + 0.02):
                        if l_ear < r_ear:
                            l_closed = True
                            r_closed = False
                        else:
                            l_closed = False
                            r_closed = True
                    else:
                        l_closed = False
                        r_closed = False

                self.both_closed = l_closed and r_closed

                l_color = "red" if l_closed else "green"
                self.latest_status["left_eye"] = (f"CLOSED ({l_ear:.2f})" if l_closed else f"OPEN ({l_ear:.2f})", l_color)
                r_color = "red" if r_closed else "green"
                self.latest_status["right_eye"] = (f"CLOSED ({r_ear:.2f})" if r_closed else f"OPEN ({r_ear:.2f})", r_color)

                nose = lm[NOSE_TIP]
                nx, ny = nose.x * w, nose.y * h

                if not self.is_calibrated:
                    self.neutral_nose = (nx, ny)
                    self.dragger.calibrate(lm, w, h) 
                    open_ear = (l_ear + r_ear) / 2.0
                    if open_ear > 0.15:
                        self.ear_threshold = max(0.16, min(0.22, open_ear * 0.68))
                        self.scroller.ear_threshold = self.ear_threshold
                    self.is_calibrated = True

                cv2.circle(rgb, (int(nx), int(ny)), 5, (0, 255, 255), -1)
                for idx in LEFT_EYE + RIGHT_EYE:
                    cv2.circle(rgb, (int(lm[idx].x * w), int(lm[idx].y * h)), 2, (0, 120, 255), -1)
                for idx in MOUTH_OUTER:
                    cv2.circle(rgb, (int(lm[idx].x * w), int(lm[idx].y * h)), 2, (255, 255, 0), -1)

                if mar > self.mar_threshold:
                    self.latest_status["mouth"] = (f"Open ({mar:.2f})", "blue")
                    if self.mouth_open_start == 0:
                        self.mouth_open_start = now
                    if (now - self.mouth_open_start) >= 0.6:
                        self.mouth_ready = True
                else:
                    self.latest_status["mouth"] = (f"Closed ({mar:.2f})", "neutral")
                    if self.mouth_ready:
                        if (now - self.last_toggle) > 1.0:
                            self.control_mode = 1 if self.control_mode == 0 else 0
                            self.last_toggle = now
                            self.neutral_nose = (nx, ny) 
                            self.dragger.calibrate(lm, w, h) 
                            
                            if self.control_mode == 1:
                                self.hud_action_text = "TRACKING ACTIVE"
                                self.hud_action_color = (0, 255, 0)
                            else:
                                self.hud_action_text = "TRACKING PAUSED"
                                self.hud_action_color = (255, 60, 60)
                            
                            self.hud_action_expiry = now + 1.2
                    self.mouth_ready = False
                    self.mouth_open_start = 0.0

                if self.control_mode == 0:
                    self.latest_status["cursor"] = ("Disabled", "red")
                    self.latest_status["mode"] = ("Paused", "neutral")
                
                elif self.control_mode == 1:
                    
                    # 1. Check Drag Controller FIRST to detect the smile
                    d_text, d_col, d_stat = self.dragger.process(lm, w, h, now)
                    
                    # --- GESTURE PRIORITY FIX ---
                    # If smiling (Duchenne smile), force system to ignore closed eyes
                    if self.dragger.is_smiling:
                        l_closed, r_closed, self.both_closed = False, False, False
                        self.scroller.eyes_are_closed = False
                        self.scroller.blink_start_time = 0.0

                    # 2. Check Scroll Module
                    is_scrolling, scroll_text = self.scroller.process(lm, ny, w, h, both_closed=self.both_closed)
                    
                    if is_scrolling:
                        self.latest_status["cursor"] = ("Scrolling", "blue")
                        self.latest_status["mode"] = ("Scroll Mode", "blue")
                        self.hud_action_text = f"SCROLLING: {scroll_text}"
                        self.hud_action_color = (0, 165, 255)
                        self.hud_action_expiry = now + 0.5
                    
                    else:
                        if scroll_text == "Scroll Mode OFF":
                            self.hud_action_text = "SCROLL MODE EXITED"
                            self.hud_action_color = (0, 255, 0)
                            self.hud_action_expiry = now + 1.2
                        elif d_text:
                            self.hud_action_text = d_text
                            self.hud_action_color = d_col
                            self.hud_action_expiry = now + 1.2
                        if d_stat:
                            self.latest_status["click_action"] = (d_stat, "blue" if "START" in d_stat else "green")

                        # 3. Check Click Controller
                        action_txt, action_col, stat_str = self.clicker.process(l_closed, r_closed, self.both_closed, now)
                        if action_txt:
                            self.hud_action_text = action_txt
                            self.hud_action_color = action_col
                            self.hud_action_expiry = now + 1.2
                        if stat_str:
                            self.latest_status["click_action"] = (stat_str, "blue" if "Wink" in stat_str else "green")
                        
                        if self.dragger.is_dragging:
                            self.latest_status["cursor"] = ("Dragging", "blue")
                            self.latest_status["mode"] = ("Drag Mode", "blue")
                            if now > self.hud_action_expiry:
                                self.hud_action_text = "DRAGGING..."
                                self.hud_action_color = (255, 165, 0)
                        else:
                            self.latest_status["cursor"] = ("Enabled", "green")
                            self.latest_status["mode"] = ("Active Tracking", "blue")

                        # 4. Check Cursor Module 
                        is_winking = (self.clicker.l_closed or self.clicker.r_closed) and not self.both_closed
                        is_frozen = now < max(self.clicker.freeze_until, self.dragger.freeze_until)
                        
                        if not is_winking and not is_frozen:
                            self.clicker.locked_pos = None 
                            self.cursor.process(nx, ny, self.neutral_nose, now)

            else:
                self.latest_status["face"] = ("Searching...", "red")
                self.latest_status["left_eye"] = ("Unknown", "neutral")
                self.latest_status["right_eye"] = ("Unknown", "neutral")
                self.latest_status["mode"] = ("Paused", "neutral")

            if now < self.hud_action_expiry and self.hud_action_text:
                text = self.hud_action_text
                font = cv2.FONT_HERSHEY_DUPLEX
                scale = 0.8
                thickness = 2
                (text_w, text_h), _ = cv2.getTextSize(text, font, scale, thickness)
                center_x = w // 2
                x1, y1 = center_x - (text_w // 2) - 16, 50
                x2, y2 = center_x + (text_w // 2) + 16, 50 + text_h + 20
                cv2.rectangle(rgb, (x1, y1), (x2, y2), (20, 20, 20), -1)
                cv2.rectangle(rgb, (x1, y1), (x2, y2), self.hud_action_color, 2)
                cv2.putText(rgb, text, (x1 + 16, y2 - 12), font, scale, self.hud_action_color, thickness, cv2.LINE_AA)

            cw, ch = self.ui.get_video_dimensions()
            if cw > 50 and ch > 50:
                scale = min((cw - 20) / w, (ch - 20) / h)
                tw, th = int(w * scale), int(h * scale)
                frame_thumb = cv2.resize(rgb, (tw, th), interpolation=cv2.INTER_LINEAR)
                img = Image.fromarray(frame_thumb)
                self.current_ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=(tw, th))

    def _ui_refresh_loop(self):
        if self.is_running and self.current_ctk_image:
            self.ui.set_video_frame(self.current_ctk_image)
        for k, v in list(self.latest_status.items()):
            self.ui.update_badge(k, v[0], v[1])
        self.ui.after(30, self._ui_refresh_loop)

    def on_close(self):
        self.stop_camera()
        self.ui.destroy()

if __name__ == "__main__":
    controller = SystemController()
    controller.run()