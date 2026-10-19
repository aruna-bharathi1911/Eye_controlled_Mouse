# utils/metrics.py
import math

def euclidean_dist(p1, p2):
    """Calculates 2D Euclidean distance between two points."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def get_ear(indices, landmarks, w, h):
    """
    Computes Eye Aspect Ratio (EAR).
    Open eye: 0.25 - 0.35 | Closed eye / blink: drops below 0.18
    """
    pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
    a = euclidean_dist(pts[1], pts[5])
    b = euclidean_dist(pts[2], pts[4])
    c = euclidean_dist(pts[0], pts[3])
    return (a + b) / (2.0 * c) if c > 0 else 0.0

def get_mar(indices, landmarks, w, h):
    """
    Computes Mouth Aspect Ratio (MAR).
    Closed mouth: 0.05 - 0.15 | Open mouth: rises above 0.30
    """
    pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
    vertical = euclidean_dist(pts[0], pts[1])
    horizontal = euclidean_dist(pts[2], pts[3])
    return vertical / horizontal if horizontal > 0 else 0.0

def get_iris_coords(center_idx, landmarks, w, h):
    """Returns pixel coordinates (x, y) of an iris center landmark."""
    lm = landmarks[center_idx]
    return lm.x * w, lm.y * h

class EMA:
    """Exponential Moving Average filter for smooth, jitter-free cursor coords."""
    def __init__(self, alpha=0.65):
        self.alpha = alpha
        self.x, self.y = None, None

    def update(self, new_x, new_y):
        if self.x is None:
            self.x, self.y = new_x, new_y
        self.x = self.alpha * self.x + (1.0 - self.alpha) * new_x
        self.y = self.alpha * self.y + (1.0 - self.alpha) * new_y
        return int(round(self.x)), int(round(self.y))