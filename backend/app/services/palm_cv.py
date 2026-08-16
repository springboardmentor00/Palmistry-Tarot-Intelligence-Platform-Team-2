import base64
import os
import uuid
import numpy as np
from io import BytesIO
from PIL import Image as PILImage

# Primary CV libraries
try:
    import cv2
except ImportError:
    cv2 = None

try:
    import mediapipe as mp
except ImportError:
    mp = None


class PalmCVService:
    def __init__(self, output_dir: str = "static/palm_images"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize MediaPipe Hands if available
        if mp is not None:
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                static_image_mode=True,
                max_num_hands=1,
                min_detection_confidence=0.5,
            )
        else:
            self.hands = None

    def analyze_palm_image(self, base64_image: str) -> dict:
        # 1. Base64 Clean & Decode
        if "," in base64_image:
            base64_image = base64_image.split(",")[1]

        img_bytes = base64.b64decode(base64_image)
        pil_img = PILImage.open(BytesIO(img_bytes))

        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        width, height = pil_img.size
        if width < 100 or height < 100:
            raise ValueError("Image dimensions too small for landmark extraction.")

        # File paths
        filename = f"{uuid.uuid4().hex[:10]}"
        orig_path = os.path.join(self.output_dir, f"{filename}_orig.png")
        processed_path = os.path.join(self.output_dir, f"{filename}_proc.png")

        pil_img.save(orig_path)

        # Defaults in case of fallback
        palm_shape = "Earth (Square)"
        finger_structure = "Proportional Structure"
        life_conf, head_conf, heart_conf, fate_conf, sun_conf = 75.0, 75.0, 75.0, 70.0, 65.0

        if cv2 is not None:
            # Convert PIL to BGR OpenCV image
            open_cv_image = np.array(pil_img)[:, :, ::-1].copy()
            h, w, _ = open_cv_image.shape

            # 2. Real MediaPipe Landmark Detection (if installed)
            landmarks_pts = []
            if self.hands is not None:
                rgb_img = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2RGB)
                results = self.hands.process(rgb_img)

                if results.multi_hand_landmarks:
                    hand_lm = results.multi_hand_landmarks[0]
                    landmarks_pts = [
                        (int(lm.x * w), int(lm.y * h)) for lm in hand_lm.landmark
                    ]

            # 3. Calculate Palm Aspect Ratio & Shape Classification
            if len(landmarks_pts) >= 18:
                wrist = np.array(landmarks_pts[0])
                index_mcp = np.array(landmarks_pts[5])
                middle_mcp = np.array(landmarks_pts[9])
                pinky_mcp = np.array(landmarks_pts[17])

                palm_w = np.linalg.norm(index_mcp - pinky_mcp)
                palm_l = np.linalg.norm(wrist - middle_mcp)
                ratio = palm_l / (palm_w + 1e-5)

                if ratio < 0.95:
                    palm_shape = "Earth Hand (Square)"
                elif ratio <= 1.1:
                    palm_shape = "Air Hand (Square & Long Fingers)"
                elif ratio <= 1.25:
                    palm_shape = "Fire Hand (Rectangular)"
                else:
                    palm_shape = "Water Hand (Long & Oval)"

            # 4. Computer Vision Image Processing (CLAHE + Bilateral + Canny)
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            smoothed = cv2.bilateralFilter(enhanced, 9, 75, 75)
            edges = cv2.Canny(smoothed, 30, 90)

            # 5. Deterministic Region-Based Line Confidence Scoring
            # Measures actual edge density in specific palm quadrants
            heart_region = edges[0 : int(h * 0.35), :]
            head_region = edges[int(h * 0.35) : int(h * 0.65), :]
            life_region = edges[int(h * 0.5) :, 0 : int(w * 0.6)]
            fate_region = edges[:, int(w * 0.35) : int(w * 0.65)]

            heart_conf = round(min(98.0, max(55.0, float(np.mean(heart_region > 0) * 450))), 1)
            head_conf = round(min(98.0, max(55.0, float(np.mean(head_region > 0) * 420))), 1)
            life_conf = round(min(98.0, max(55.0, float(np.mean(life_region > 0) * 400))), 1)
            fate_conf = round(min(95.0, max(50.0, float(np.mean(fate_region > 0) * 380))), 1)
            sun_conf = round((heart_conf + fate_conf) / 2.1, 1)

            # 6. Draw Visualization Overlay
            output_img = open_cv_image.copy()

            # Overlay edge contours in cyan
            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(output_img, contours, -1, (255, 255, 0), 1)

            # Draw tracked skeleton landmarks if available
            if landmarks_pts:
                for pt in landmarks_pts:
                    cv2.circle(output_img, pt, 4, (0, 215, 255), -1)  # Gold points

            cv2.imwrite(processed_path, output_img)
        else:
            # Simple fallback save if OpenCV isn't available
            pil_img.save(processed_path)

        overall_conf = round(
            (life_conf + head_conf + heart_conf + fate_conf + sun_conf) / 5.0, 1
        )

        return {
            "image_path": orig_path,
            "processed_image_path": processed_path,
            "palm_shape": palm_shape,
            "finger_structure": finger_structure,
            "life_line_conf": life_conf,
            "head_line_conf": head_conf,
            "heart_line_conf": heart_conf,
            "fate_line_conf": fate_conf,
            "sun_line_conf": sun_conf,
            "overall_conf": overall_conf,
        }


palm_cv_service = PalmCVService()
