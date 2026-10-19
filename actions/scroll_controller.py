import time
import math
import pyautogui

# Eye Landmarks for EAR calculation
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

class ScrollController:
    # Set to 0.5 seconds. Normal blinks are ~0.15 seconds, so they are ignored.
    def __init__(self, ear_threshold=0.20, deadzone_y=4.0, scroll_cooldown=0.06, hold_duration=0.5):
        self.ear_threshold = ear_threshold
        self.deadzone_y = deadzone_y
        self.scroll_cooldown = scroll_cooldown
        self.hold_duration = hold_duration
        
        # Scroll State
        self.is_scroll_mode = False
        self.scroll_anchor_y = 0.0
        self.last_scroll_time = 0.0
        
        # Long Blink Tracking
        self.eyes_are_closed = False
        self.blink_start_time = 0.0
        self.has_toggled_this_blink = False

    def euclidean_dist(self, p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def get_ear(self, indices, landmarks, w, h):
        pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
        a = self.euclidean_dist(pts[1], pts[5])
        b = self.euclidean_dist(pts[2], pts[4])
        c = self.euclidean_dist(pts[0], pts[3])
        return (a + b) / (2.0 * c) if c > 0 else 0.0

    def calibrate(self, landmarks, w, h):
        """Resets the scroll state when Recalibrate is pressed."""
        self.is_scroll_mode = False
        self.eyes_are_closed = False
        self.blink_start_time = 0.0
        self.has_toggled_this_blink = False

    def process(self, landmarks, nose_y, w, h, both_closed=None):
        now = time.time()
        
        # 1. Determine if BOTH eyes are closed (not a single-eye wink)
        if both_closed is not None:
            currently_closed = bool(both_closed)
        else:
            l_ear = self.get_ear(LEFT_EYE, landmarks, w, h)
            r_ear = self.get_ear(RIGHT_EYE, landmarks, w, h)
            ear_diff = abs(l_ear - r_ear)
            currently_closed = (l_ear < self.ear_threshold) and (r_ear < self.ear_threshold) and (ear_diff < 0.035)

        # 2. Long Blink Detection Logic
        if currently_closed:
            if not self.eyes_are_closed:
                self.eyes_are_closed = True
                self.blink_start_time = now
            
            # Check if eyes have been held closed long enough
            hold_time = now - self.blink_start_time
            if hold_time >= self.hold_duration and not self.has_toggled_this_blink:
                self.is_scroll_mode = not self.is_scroll_mode
                self.has_toggled_this_blink = True # Prevents rapid flipping while eyes remain shut
                
                if self.is_scroll_mode:
                    self.scroll_anchor_y = nose_y
                    return True, "Scroll Mode ON"
                else:
                    return False, "Scroll Mode OFF"
                    
            # Provide visual feedback while holding (before the toggle actually triggers)
            if not self.has_toggled_this_blink:
                percent = min(100, int((hold_time / self.hold_duration) * 100))
                return True, f"Hold to toggle... ({percent}%)"

        else:
            # Eyes opened: reset all blink tracking variables
            self.eyes_are_closed = False
            self.blink_start_time = 0.0
            self.has_toggled_this_blink = False

        # 3. Execute Scrolling if active
        if self.is_scroll_mode:
            dy = nose_y - self.scroll_anchor_y
            if abs(dy) > self.deadzone_y and (now - self.last_scroll_time > self.scroll_cooldown):
                direction = 1 if dy < 0 else -1
                magnitude = max(1, int(abs(dy) - self.deadzone_y) * 20)
                pyautogui.scroll(direction * magnitude)
                self.last_scroll_time = now
                return True, f"{'Up' if direction > 0 else 'Down'}"
            return True, "Active (Nod to Scroll)"
        
        return False, ""