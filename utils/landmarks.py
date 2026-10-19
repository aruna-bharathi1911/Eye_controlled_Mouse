# utils/landmarks.py

# Eye Contours (6 points per eye for Eye Aspect Ratio calculation)
# Order: [outer_corner, top_inner, top_outer, inner_corner, bottom_outer, bottom_inner]
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

# Iris Centers & Contours
LEFT_IRIS_CENTER = 473
RIGHT_IRIS_CENTER = 468
LEFT_IRIS = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]

# Stable Face Center
NOSE_TIP = 1

# Eyebrow Anchors
LEFT_EYEBROW = [300, 296, 334, 293]
RIGHT_EYEBROW = [107, 63, 105, 66]

# Mouth calculation points: [upper_lip_inner, lower_lip_inner, left_corner, right_corner]
MOUTH_CALC = [13, 14, 78, 308]

# Mouth full outline for visual feedback
MOUTH_OUTER = [
    61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291,
    308, 324, 318, 402, 317, 14, 87, 178, 88, 95
]