import os
import base64
import uuid
import binascii
import numpy as np
from PIL import Image as PILImage, ImageFilter
from io import BytesIO

# Try to import cv2, otherwise use a deterministic PIL/numpy fallback pipeline
try:
    import cv2
except ImportError:
    cv2 = None


class PalmAnalysisError(ValueError):
    """Raised when an uploaded image cannot be decoded, validated, or does not
    contain a detectable hand/palm region."""
    pass


class PalmCVService:
    """
    Real, deterministic palm feature extraction pipeline.

    Pipeline (OpenCV path):
      1. Decode + validate the uploaded image.
      2. Segment the hand from the background using HSV/YCrCb skin-color
         thresholds (with an Otsu-threshold fallback for non-skin-tone or
         low-contrast images).
      3. Extract the largest contour, convex hull, and convexity defects to
         locate fingers and derive palm-shape / finger-structure geometry.
      4. Restrict analysis to the palm region (below the finger bases, above
         the wrist) and run Canny edge detection + probabilistic Hough line
         detection to measure real line/edge density in the anatomical zones
         that correspond to the Life, Head, Heart, Fate, and Sun lines.
      5. Convert edge/line density in each zone into a bounded confidence
         score (0-100). These are derived from actual pixel data in the
         uploaded image, not randomized.
      6. Render an annotated image (hand contour, convex hull, detected line
         segments) so the "processed" output is a genuine visualization of
         what was detected, not a decorative mock overlay.
    """

    def __init__(self, output_dir: str = "static/palm_images"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Public entrypoint
    # ------------------------------------------------------------------ #
    def analyze_palm_image(self, base64_image: str) -> dict:
        pil_img = self._decode_and_validate(base64_image)

        filename = f"{uuid.uuid4()}"
        orig_path = os.path.join(self.output_dir, f"{filename}_orig.png")
        pil_img.save(orig_path)
        processed_path = os.path.join(self.output_dir, f"{filename}_processed.png")

        if cv2 is not None:
            result = self._analyze_with_opencv(pil_img, processed_path)
        else:
            result = self._analyze_with_pillow_fallback(pil_img, processed_path)

        result["image_path"] = orig_path
        result["processed_image_path"] = processed_path
        return result

    # ------------------------------------------------------------------ #
    # Decoding / validation
    # ------------------------------------------------------------------ #
    def _decode_and_validate(self, base64_image: str) -> "PILImage.Image":
        if not base64_image or not isinstance(base64_image, str):
            raise PalmAnalysisError("No image data was provided.")

        if "," in base64_image:
            base64_image = base64_image.split(",")[1]

        try:
            img_bytes = base64.b64decode(base64_image, validate=True)
        except (binascii.Error, ValueError):
            raise PalmAnalysisError("Uploaded image is not valid base64 data.")

        if len(img_bytes) < 100:
            raise PalmAnalysisError("Uploaded image payload is too small to be a valid image.")

        try:
            pil_img = PILImage.open(BytesIO(img_bytes))
            pil_img.load()
        except Exception:
            raise PalmAnalysisError("Uploaded file could not be decoded as an image.")

        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        width, height = pil_img.size
        if width < 150 or height < 150:
            raise PalmAnalysisError("Image dimensions too small for reliable palm feature extraction (minimum 150x150).")
        if width > 6000 or height > 6000:
            raise PalmAnalysisError("Image dimensions are too large to process.")

        return pil_img

    # ------------------------------------------------------------------ #
    # OpenCV pipeline
    # ------------------------------------------------------------------ #
    def _analyze_with_opencv(self, pil_img, processed_path: str) -> dict:
        rgb = np.array(pil_img)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        h, w = bgr.shape[:2]

        hand_mask = self._segment_hand(bgr)
        contour = self._largest_contour(hand_mask)

        if contour is None or cv2.contourArea(contour) < (w * h * 0.03):
            raise PalmAnalysisError(
                "Could not detect a hand/palm region in the uploaded image. "
                "Please upload a clear, well-lit photo of an open palm against a plain background."
            )

        hull_indices = cv2.convexHull(contour, returnPoints=False)
        hull_points = cv2.convexHull(contour, returnPoints=True)
        x, y, bw, bh = cv2.boundingRect(contour)

        # --- Finger detection via convexity defects -----------------------
        finger_tip_count, defect_points, avg_finger_len, finger_len_std = self._detect_fingers(
            contour, hull_indices, (x, y, bw, bh)
        )

        # --- Palm shape & finger structure classification ------------------
        palm_shape = self._classify_palm_shape(bw, bh, finger_tip_count)
        finger_structure = self._classify_finger_structure(avg_finger_len, finger_len_std, bh)

        # --- Palm-region ROI (below finger bases, above wrist) --------------
        # Approximate palm as the lower ~55% of the hand bounding box.
        palm_y0 = y + int(bh * 0.42)
        palm_y1 = y + int(bh * 0.98)
        palm_x0 = x + int(bw * 0.05)
        palm_x1 = x + int(bw * 0.95)
        palm_y0, palm_y1 = max(0, palm_y0), min(h, palm_y1)
        palm_x0, palm_x1 = max(0, palm_x0), min(w, palm_x1)

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        smoothed = cv2.bilateralFilter(enhanced, 9, 60, 60)
        edges = cv2.Canny(smoothed, 40, 120)

        # Mask edges to the palm region and hand silhouette only.
        roi_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(roi_mask, [contour], -1, 255, thickness=-1)
        palm_region_mask = np.zeros((h, w), dtype=np.uint8)
        palm_region_mask[palm_y0:palm_y1, palm_x0:palm_x1] = 255
        combined_mask = cv2.bitwise_and(roi_mask, palm_region_mask)
        palm_edges = cv2.bitwise_and(edges, edges, mask=combined_mask)

        lines = cv2.HoughLinesP(
            palm_edges, 1, np.pi / 180, threshold=18,
            minLineLength=max(10, int(bw * 0.08)), maxLineGap=8
        )
        lines = [] if lines is None else [l[0] for l in lines]

        zones = self._principal_line_zones(palm_x0, palm_y0, palm_x1, palm_y1)
        line_scores = {}
        for line_name, (zx0, zy0, zx1, zy1) in zones.items():
            line_scores[line_name] = self._score_zone(lines, palm_edges, zx0, zy0, zx1, zy1)

        overall_conf = round(
            sum(line_scores.values()) / len(line_scores), 1
        ) if line_scores else 0.0

        # --- Render annotated processed image --------------------------------
        annotated = bgr.copy()
        cv2.drawContours(annotated, [contour], -1, (34, 197, 94), 2)          # green hand outline
        cv2.polylines(annotated, [hull_points], True, (251, 191, 36), 2)      # gold convex hull
        for pt in defect_points:
            cv2.circle(annotated, pt, 5, (236, 72, 153), -1)                  # pink finger valleys
        for (lx1, ly1, lx2, ly2) in lines:
            cv2.line(annotated, (lx1, ly1), (lx2, ly2), (139, 92, 246), 2)    # mystic purple detected lines
        cv2.rectangle(annotated, (palm_x0, palm_y0), (palm_x1, palm_y1), (59, 130, 246), 1)

        cv2.imwrite(processed_path, annotated)

        return {
            "palm_shape": palm_shape,
            "finger_structure": finger_structure,
            "life_line_conf": line_scores.get("life", 0.0),
            "head_line_conf": line_scores.get("head", 0.0),
            "heart_line_conf": line_scores.get("heart", 0.0),
            "fate_line_conf": line_scores.get("fate", 0.0),
            "sun_line_conf": line_scores.get("sun", 0.0),
            "overall_conf": overall_conf,
            "detected_finger_count": finger_tip_count,
            "detected_line_segments": len(lines),
        }

    def _segment_hand(self, bgr: np.ndarray) -> np.ndarray:
        """Segment a hand/skin region. Falls back to an Otsu threshold on
        luminance if skin-color thresholding fails to find enough pixels
        (covers gloved hands, illustrated palms, or unusual lighting)."""
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)

        lower_hsv = np.array([0, 20, 60], dtype=np.uint8)
        upper_hsv = np.array([25, 180, 255], dtype=np.uint8)
        mask_hsv = cv2.inRange(hsv, lower_hsv, upper_hsv)

        lower_ycrcb = np.array([0, 135, 80], dtype=np.uint8)
        upper_ycrcb = np.array([255, 180, 135], dtype=np.uint8)
        mask_ycrcb = cv2.inRange(ycrcb, lower_ycrcb, upper_ycrcb)

        mask = cv2.bitwise_and(mask_hsv, mask_ycrcb)
        kernel = np.ones((7, 7), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.dilate(mask, kernel, iterations=1)

        if cv2.countNonZero(mask) < (bgr.shape[0] * bgr.shape[1] * 0.02):
            # Fallback: Otsu threshold assuming a roughly plain/contrasting background.
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # Ensure foreground is the smaller (subject), not the larger (background)
            if cv2.countNonZero(mask) > mask.size * 0.6:
                mask = cv2.bitwise_not(mask)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        return mask

    def _largest_contour(self, mask: np.ndarray):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        return max(contours, key=cv2.contourArea)

    def _detect_fingers(self, contour, hull_indices, bbox):
        x, y, bw, bh = bbox
        finger_tip_count = 0
        defect_points = []
        finger_lengths = []

        try:
            defects = cv2.convexityDefects(contour, hull_indices)
        except cv2.error:
            defects = None

        if defects is not None:
            centroid_y = y + bh * 0.65  # approx palm center, below finger bases
            for i in range(defects.shape[0]):
                s, e, f, d = defects[i, 0]
                start = tuple(contour[s][0])
                end = tuple(contour[e][0])
                far = tuple(contour[f][0])
                depth = d / 256.0

                # A meaningful finger valley: deep enough relative to hand size,
                # and located above the approximate palm centroid (i.e. between fingers).
                if depth > bh * 0.08 and far[1] < centroid_y:
                    finger_tip_count += 1
                    defect_points.append(far)
                    len_a = np.hypot(start[0] - far[0], start[1] - far[1])
                    len_b = np.hypot(end[0] - far[0], end[1] - far[1])
                    finger_lengths.append((len_a + len_b) / 2.0)

        # Valleys detected == (fingers - 1) when all 4 gaps are visible;
        # clamp into a realistic 0-5 range for a human hand.
        estimated_fingers = min(5, max(1, finger_tip_count + 1)) if defect_points else 0

        avg_len = float(np.mean(finger_lengths)) if finger_lengths else bh * 0.35
        std_len = float(np.std(finger_lengths)) if finger_lengths else 0.0

        return estimated_fingers, defect_points, avg_len, std_len

    def _classify_palm_shape(self, bw: int, bh: int, finger_count: int) -> str:
        # Traditional palmistry hand-shape typing driven by measured geometry:
        # aspect ratio (palm length vs width) and relative finger length.
        aspect = bh / float(bw) if bw else 1.0
        long_hand = aspect >= 1.35
        long_fingers = finger_count >= 4  # detected an open, extended-finger pose

        if long_hand and long_fingers:
            return "Water Hand"      # long palm, long fingers
        if long_hand and not long_fingers:
            return "Fire Hand"       # long palm, short/closed fingers
        if not long_hand and long_fingers:
            return "Air Hand"        # square palm, long fingers
        return "Earth Hand"          # square palm, short fingers

    def _classify_finger_structure(self, avg_len: float, std_len: float, bh: int) -> str:
        variability = (std_len / avg_len) if avg_len else 0.0
        relative_len = avg_len / float(bh) if bh else 0.0

        if variability > 0.35:
            return "Spatulate Structure"
        if relative_len > 0.42:
            return "Psychic Structure"
        if relative_len < 0.28:
            return "Square Structure"
        return "Conical Structure"

    def _principal_line_zones(self, x0, y0, x1, y1):
        """Anatomically-inspired sub-regions of the palm ROI for each of the
        five tracked lines, expressed as pixel rectangles."""
        w = x1 - x0
        h = y1 - y0
        return {
            # Life line: curves around the thumb mount (left side of ROI)
            "life": (x0, y0, x0 + int(w * 0.4), y1),
            # Head line: horizontal band through the upper-middle of the palm
            "head": (x0 + int(w * 0.15), y0, x1 - int(w * 0.1), y0 + int(h * 0.35)),
            # Heart line: horizontal band near the top of the palm
            "heart": (x0 + int(w * 0.15), y0, x1, y0 + int(h * 0.2)),
            # Fate line: vertical band through the center of the palm
            "fate": (x0 + int(w * 0.35), y0, x0 + int(w * 0.65), y1),
            # Sun line: vertical band under the ring finger (right-of-center)
            "sun": (x0 + int(w * 0.55), y0, x0 + int(w * 0.8), y0 + int(h * 0.7)),
        }

    def _score_zone(self, lines, edge_img, zx0, zy0, zx1, zy1) -> float:
        zx0, zy0 = max(0, zx0), max(0, zy0)
        zx1 = min(edge_img.shape[1], zx1)
        zy1 = min(edge_img.shape[0], zy1)
        if zx1 <= zx0 or zy1 <= zy0:
            return 0.0

        zone_area = (zx1 - zx0) * (zy1 - zy0)
        zone_edges = edge_img[zy0:zy1, zx0:zx1]
        edge_density = cv2.countNonZero(zone_edges) / float(zone_area) if zone_area else 0.0

        # Count Hough segments whose midpoint falls in this zone as a proxy
        # for a clearly-traced line (vs. scattered noise/texture edges).
        segment_hits = 0
        segment_length = 0.0
        for (lx1, ly1, lx2, ly2) in lines:
            mx, my = (lx1 + lx2) / 2.0, (ly1 + ly2) / 2.0
            if zx0 <= mx <= zx1 and zy0 <= my <= zy1:
                segment_hits += 1
                segment_length += np.hypot(lx2 - lx1, ly2 - ly1)

        # Combine edge density (texture-level signal) with clean detected
        # segments (structure-level signal) into a bounded 0-100 confidence.
        density_score = min(60.0, edge_density * 4000.0)
        segment_score = min(40.0, segment_hits * 8.0 + segment_length * 0.02)
        score = density_score + segment_score

        return round(min(98.0, max(5.0, score)), 1)

    # ------------------------------------------------------------------ #
    # Fallback pipeline (no OpenCV available)
    # ------------------------------------------------------------------ #
    def _analyze_with_pillow_fallback(self, pil_img, processed_path: str) -> dict:
        """Deterministic, image-derived fallback using only PIL + numpy when
        OpenCV isn't installed. Uses grayscale edge-filter density per
        quadrant instead of Hough/contour analysis. Still no randomness."""
        gray = pil_img.convert("L")
        w, h = gray.size
        edges = gray.filter(ImageFilter.FIND_EDGES)
        arr = np.array(edges, dtype=np.float32)

        # Threshold edge intensity to build a binary edge map.
        thresh = arr.mean() + arr.std()
        binary = (arr > thresh).astype(np.uint8)

        # Palm ROI: lower ~55% of the frame (mirrors the OpenCV ROI heuristic).
        y0, y1 = int(h * 0.42), h
        x0, x1 = int(w * 0.05), int(w * 0.95)
        roi = binary[y0:y1, x0:x1]

        def zone_score(fx0, fy0, fx1, fy1):
            zx0, zx1 = int((x1 - x0) * fx0), int((x1 - x0) * fx1)
            zy0, zy1 = int((y1 - y0) * fy0), int((y1 - y0) * fy1)
            zone = roi[zy0:zy1, zx0:zx1]
            if zone.size == 0:
                return 5.0
            density = float(zone.sum()) / zone.size
            return round(min(95.0, max(5.0, density * 500.0)), 1)

        life_conf = zone_score(0.0, 0.0, 0.4, 1.0)
        head_conf = zone_score(0.15, 0.0, 0.9, 0.35)
        heart_conf = zone_score(0.15, 0.0, 1.0, 0.2)
        fate_conf = zone_score(0.35, 0.0, 0.65, 1.0)
        sun_conf = zone_score(0.55, 0.0, 0.8, 0.7)
        overall_conf = round((life_conf + head_conf + heart_conf + fate_conf + sun_conf) / 5.0, 1)

        aspect = h / float(w) if w else 1.0
        palm_shape = "Water Hand" if aspect >= 1.35 else "Earth Hand"
        finger_structure = "Conical Structure" if overall_conf >= 55 else "Square Structure"

        edges.convert("RGB").save(processed_path)

        return {
            "palm_shape": palm_shape,
            "finger_structure": finger_structure,
            "life_line_conf": life_conf,
            "head_line_conf": head_conf,
            "heart_line_conf": heart_conf,
            "fate_line_conf": fate_conf,
            "sun_line_conf": sun_conf,
            "overall_conf": overall_conf,
            "detected_finger_count": 0,
            "detected_line_segments": 0,
        }


palm_cv_service = PalmCVService()
