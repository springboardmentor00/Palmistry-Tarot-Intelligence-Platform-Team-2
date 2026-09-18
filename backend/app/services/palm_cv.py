import base64
import binascii
import os
import uuid
from io import BytesIO

import cv2
import numpy as np
from PIL import Image as PILImage

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover
    mp = None


class PalmCVService:
    def __init__(self, output_dir: str = "static/palm_images"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.hands = None
        if mp is not None:
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.5)

    @staticmethod
    def _confidence(region: np.ndarray, scale: float = 1000.0) -> float:
        density = float(np.mean(region > 0))
        return round(min(100.0, density * scale), 1)

    def analyze_palm_image(self, base64_image: str) -> dict:
        if not base64_image:
            raise ValueError("Palm image is required.")
        if "," in base64_image:
            base64_image = base64_image.split(",", 1)[1]
        try:
            img_bytes = base64.b64decode(base64_image, validate=True)
            pil_img = PILImage.open(BytesIO(img_bytes)).convert("RGB")
        except (binascii.Error, ValueError, OSError) as exc:
            raise ValueError("Invalid base64 image payload.") from exc
        if pil_img.width < 100 or pil_img.height < 100:
            raise ValueError("Image dimensions must be at least 100x100 pixels.")
        if pil_img.width * pil_img.height > 16_000_000:
            raise ValueError("Image is too large to process safely.")

        filename = uuid.uuid4().hex[:16]
        orig_path = os.path.join(self.output_dir, f"{filename}_orig.png")
        processed_path = os.path.join(self.output_dir, f"{filename}_proc.png")
        pil_img.save(orig_path, format="PNG")

        bgr = np.array(pil_img)[:, :, ::-1].copy()
        h, w = bgr.shape[:2]
        landmarks = []
        if self.hands is not None:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            result = self.hands.process(rgb)
            if result.multi_hand_landmarks:
                hand = result.multi_hand_landmarks[0]
                landmarks = [(int(lm.x * w), int(lm.y * h)) for lm in hand.landmark]

        palm_shape = "Not detected"
        finger_structure = "Not detected"
        if len(landmarks) >= 21:
            wrist = np.array(landmarks[0], dtype=float)
            middle_mcp = np.array(landmarks[9], dtype=float)
            index_mcp = np.array(landmarks[5], dtype=float)
            pinky_mcp = np.array(landmarks[17], dtype=float)
            palm_width = np.linalg.norm(index_mcp - pinky_mcp)
            palm_length = np.linalg.norm(wrist - middle_mcp)
            ratio = palm_length / max(palm_width, 1e-6)
            if ratio < 0.95:
                palm_shape = "Earth Hand (Square)"
            elif ratio <= 1.10:
                palm_shape = "Air Hand (Balanced)"
            elif ratio <= 1.25:
                palm_shape = "Fire Hand (Rectangular)"
            else:
                palm_shape = "Water Hand (Long & Oval)"

            finger_tips = [8, 12, 16, 20]
            finger_lengths = [np.linalg.norm(np.array(landmarks[i], dtype=float) - np.array(landmarks[i - 4], dtype=float)) for i in finger_tips]
            spread = float(np.std(finger_lengths) / max(np.mean(finger_lengths), 1e-6))
            finger_structure = "Evenly proportioned" if spread < 0.20 else "Varied proportions"

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        smoothed = cv2.bilateralFilter(enhanced, 9, 75, 75)
        edges = cv2.Canny(smoothed, 30, 90)

        heart_region = edges[0:int(h * 0.35), :]
        head_region = edges[int(h * 0.35):int(h * 0.65), :]
        life_region = edges[int(h * 0.50):, 0:int(w * 0.60)]
        fate_region = edges[:, int(w * 0.35):int(w * 0.65)]
        life = self._confidence(life_region, 450)
        head = self._confidence(head_region, 450)
        heart = self._confidence(heart_region, 450)
        fate = self._confidence(fate_region, 450)
        sun = round((heart + fate) / 2.0, 1)
        overall = round((life + head + heart + fate + sun) / 5.0, 1)

        output = bgr.copy()
        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(output, contours, -1, (255, 255, 0), 1)
        for point in landmarks:
            cv2.circle(output, point, 4, (0, 215, 255), -1)
        cv2.imwrite(processed_path, output)

        return {
            "image_path": orig_path,
            "processed_image_path": processed_path,
            "palm_shape": palm_shape,
            "finger_structure": finger_structure,
            "life_line_conf": life,
            "head_line_conf": head,
            "heart_line_conf": heart,
            "fate_line_conf": fate,
            "sun_line_conf": sun,
            "overall_conf": overall,
            "hand_features": {"landmark_count": len(landmarks), "image_width": w, "image_height": h},
        }


palm_cv_service = PalmCVService()
