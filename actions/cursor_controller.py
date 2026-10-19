import math
import ctypes
import pyautogui

user32 = ctypes.windll.user32

class LowPassFilter:
    def __init__(self, alpha):
        self.alpha = alpha
        self.s = None
    def filter(self, val):
        self.s = val if self.s is None else self.alpha * val + (1.0 - self.alpha) * self.s
        return self.s

class OneEuroFilter:
    def __init__(self, min_cutoff=0.25, beta=0.04, d_cutoff=1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.x_filter = LowPassFilter(self._alpha(min_cutoff, 1 / 30.0))
        self.dx_filter = LowPassFilter(self._alpha(d_cutoff, 1 / 30.0))
        self.last_time = None

    def _alpha(self, cutoff, dt):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, val, timestamp):
        if self.last_time is None:
            self.last_time = timestamp
            return self.x_filter.filter(val)
        dt = max(timestamp - self.last_time, 1e-4)
        self.last_time = timestamp
        prev_val = self.x_filter.s if self.x_filter.s is not None else val
        dval = (val - prev_val) / dt
        edval = self.dx_filter.filter(dval)
        cutoff = self.min_cutoff + self.beta * abs(edval)
        self.x_filter.alpha = self._alpha(cutoff, dt)
        return self.x_filter.filter(val)

class CursorController:
    def __init__(self):
        # Increased smoothing to eliminate micro-jitters (lowered min_cutoff)
        self.filter_x = OneEuroFilter(min_cutoff=0.015, beta=0.007)
        self.filter_y = OneEuroFilter(min_cutoff=0.015, beta=0.007)
        self.cursor_history = []
        
        self.screen_w, self.screen_h = pyautogui.size()
        self.last_cursor_pos = (self.screen_w / 2.0, self.screen_h / 2.0)
        
        self.deadzone_radius = 6.0   
        self.speed_multiplier = 2.2  
        self.range_x = 35.0
        self.range_y = 26.0

    def reset(self):
        self.cursor_history.clear()

    def process(self, nx, ny, neutral_nose, now):
        if neutral_nose is None:
            return

        raw_dx = nx - neutral_nose[0]
        raw_dy = ny - neutral_nose[1]
        dist = math.hypot(raw_dx, raw_dy)

        if dist < self.deadzone_radius:
            dx, dy = 0.0, 0.0
        else:
            # EXPONENTIAL CURVE: ** 1.45 instead of 1.15. 
            # This makes small movements highly accurate and large movements fast.
            scale = ((dist - self.deadzone_radius) / dist) ** 1.45
            dx = raw_dx * scale
            dy = raw_dy * scale

        target_x = (self.screen_w / 2.0) + (dx / self.range_x) * (self.screen_w / 2.0) * self.speed_multiplier
        target_y = (self.screen_h / 2.0) + (dy / self.range_y) * (self.screen_h / 2.0) * self.speed_multiplier

        target_x = max(0, min(self.screen_w - 1, target_x))
        target_y = max(0, min(self.screen_h - 1, target_y))

        smooth_x = self.filter_x.filter(target_x, now)
        smooth_y = self.filter_y.filter(target_y, now)

        self.cursor_history.append((smooth_x, smooth_y))
        if len(self.cursor_history) > 6: 
            self.cursor_history.pop(0)

        avg_x = sum(p[0] for p in self.cursor_history) / len(self.cursor_history)
        avg_y = sum(p[1] for p in self.cursor_history) / len(self.cursor_history)

        if math.hypot(avg_x - self.last_cursor_pos[0], avg_y - self.last_cursor_pos[1]) >= 2.0:
            user32.SetCursorPos(int(avg_x), int(avg_y))
            self.last_cursor_pos = (avg_x, avg_y)