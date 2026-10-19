import ctypes
import time

user32 = ctypes.windll.user32

# Native Windows Hardware Click Constants
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

class ClickController:
    def __init__(self):
        self.wink_min_dur = 0.10        
        self.wink_max_dur = 0.70        
        self.double_click_cadence = 1.20 

        self.l_start = 0.0
        self.r_start = 0.0
        self.l_closed = False
        self.r_closed = False
        
        self.left_wink_count = 0
        self.last_left_wink_time = 0.0
        self.pending_left_single = False
        self.pending_right_single = False
        self.last_right_wink_time = 0.0
        
        self.freeze_until = 0.0

    def reset(self):
        self.l_closed = False
        self.r_closed = False
        self.pending_left_single = False
        self.pending_right_single = False
        self.left_wink_count = 0

    def _hardware_click(self, button="left", double=False):
        """Forces OS-level clicks to bypass Windows security on Menu bars"""
        if button == "left":
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            if double:
                time.sleep(0.05)
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif button == "right":
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

    def process(self, l_closed, r_closed, both_closed, now):
        action_text, action_color, status_str = None, None, None

        # Cancel any single-eye wink in progress if both eyes close (blink or long blink)
        if both_closed:
            self.l_closed = False
            self.r_closed = False

        # 1. Execute Pending Clicks
        if self.pending_left_single and not l_closed and (now - self.last_left_wink_time > self.double_click_cadence):
            self._hardware_click(button="left", double=False)
            self.pending_left_single = False
            self.left_wink_count = 0
            self.freeze_until = now + 0.20
            return "LEFT CLICK", (0, 255, 0), "LEFT CLICK"

        if self.pending_right_single and not r_closed and (now - self.last_right_wink_time > self.double_click_cadence):
            self._hardware_click(button="right", double=False)
            self.pending_right_single = False
            self.freeze_until = now + 0.20
            return "RIGHT CLICK", (255, 0, 255), "RIGHT CLICK"

        # 2. Left Eye Logic
        if l_closed and not r_closed and not both_closed:
            if not self.l_closed:
                self.l_start, self.l_closed = now, True

        if not l_closed and self.l_closed:
            dur = now - self.l_start
            if not both_closed and (self.wink_min_dur <= dur <= self.wink_max_dur):
                if self.left_wink_count == 0:
                    self.left_wink_count = 1
                    self.last_left_wink_time = now
                    self.pending_left_single = True
                    status_str = "Left Wink 1/2..."
                elif self.left_wink_count == 1 and (now - self.last_left_wink_time <= self.double_click_cadence):
                    self._hardware_click(button="left", double=True)
                    self.pending_left_single = False
                    self.left_wink_count = 0
                    self.freeze_until = now + 0.30
                    return "DOUBLE LEFT CLICK", (255, 255, 0), "DOUBLE CLICK"
            self.l_closed = False

        # 3. Right Eye Logic
        if r_closed and not l_closed and not both_closed:
            if not self.r_closed:
                self.r_start, self.r_closed = now, True

        if not r_closed and self.r_closed:
            dur = now - self.r_start
            if not both_closed and (self.wink_min_dur <= dur <= self.wink_max_dur):
                self.pending_right_single = True
                self.last_right_wink_time = now
            self.r_closed = False
            
        return action_text, action_color, status_str