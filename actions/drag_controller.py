import time
import math
import pyautogui

class DragController:
    # INCREASED THRESHOLD to 0.07. Normal facial expressions will be ignored.
    def __init__(self, smile_threshold=0.07, hold_duration=0.5):
        self.smile_threshold = smile_threshold
        self.hold_duration = hold_duration
        self.baseline = None
        
        self.is_dragging = False
        self.is_smiling = False
        self.smile_start_time = 0.0
        self.drag_toggled_this_smile = False
        self.freeze_until = 0.0

    def reset(self):
        """Releases the mouse and resets states if recalibrated."""
        if self.is_dragging:
            pyautogui.mouseUp(button='left')
        self.is_dragging = False
        self.is_smiling = False
        self.drag_toggled_this_smile = False
        self.baseline = None

    def calibrate(self, landmarks, w, h):
        """Sets the relaxed mouth width."""
        if not landmarks: return
        self.baseline = self.get_mouth_width_ratio(landmarks, w, h)

    def get_mouth_width_ratio(self, landmarks, w, h):
        # 61 and 291 are the extreme left and right corners of the mouth
        mx1, my1 = landmarks[61].x * w, landmarks[61].y * h
        mx2, my2 = landmarks[291].x * w, landmarks[291].y * h
        mouth_w = math.hypot(mx1 - mx2, my1 - my2)

        # 33 and 263 are the outer corners of the eyes, used to scale for distance
        ex1, ey1 = landmarks[33].x * w, landmarks[33].y * h
        ex2, ey2 = landmarks[263].x * w, landmarks[263].y * h
        face_w = math.hypot(ex1 - ex2, ey1 - ey2)

        return mouth_w / face_w if face_w > 0 else 0

    def process(self, landmarks, w, h, now):
        # Auto-calibrate if missing
        if self.baseline is None:
            self.calibrate(landmarks, w, h)
            return None, None, None

        current_ratio = self.get_mouth_width_ratio(landmarks, w, h)
        
        # Detect if the mouth is stretched wider than the relaxed baseline
        currently_smiling = (current_ratio - self.baseline) > self.smile_threshold

        if currently_smiling:
            if not self.is_smiling:
                self.is_smiling = True
                self.smile_start_time = now
                self.drag_toggled_this_smile = False

            dur = now - self.smile_start_time
            
            # Toggle Drag & Drop on 0.5s hold of the smile
            if dur >= self.hold_duration and not self.drag_toggled_this_smile:
                self.is_dragging = not self.is_dragging
                self.drag_toggled_this_smile = True
                self.freeze_until = now + 0.3

                if self.is_dragging:
                    pyautogui.mouseDown(button='left')
                    return "DRAGGING (Smile again to Drop)", (255, 100, 100), "DRAG START"
                else:
                    pyautogui.mouseUp(button='left')
                    return "DROPPED", (0, 255, 0), "DROP"
            
            # Show a helpful loading percentage on the HUD before it triggers
            elif not self.drag_toggled_this_smile and dur > 0.15:
                 percent = min(100, int((dur / self.hold_duration) * 100))
                 return f"Hold Smile... ({percent}%)", (255, 165, 0), None

        else:
            self.is_smiling = False

        return None, None, None