"""
CSV to Annotated Image – Auto-Draw Tool
========================================
Read detections CSV and redraw all bounding boxes on the original image.

Usage:
    python csv_to_image.py --image photo.jpg --csv photo_detections.csv --output result.jpg
"""

import argparse
import cv2
import pandas as pd
from pathlib import Path


# ── colour palette (BGR) – same as annotate.py ───────────────────────────────
PALETTE = [
    (56, 245, 100), (54, 162, 235), (255, 99, 132), (255, 205, 86),
    (153, 102, 255), (255, 159, 64), (0, 220, 220), (220, 60, 60),
    (60, 179, 113), (255, 140, 0),
]

def _color(idx: int):
    return PALETTE[idx % len(PALETTE)]


def draw_annotations(image_path: str, csv_path: str, output_path: str,
                     box_thickness: int = 4, font_scale: float = 1.0):
    """
    Load image + CSV, draw all boxes with labels, save result.
    """
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot open image: {image_path}")

    # Load CSV
    df = pd.read_csv(csv_path)
    print(f"✓ Loaded {len(df)} detections from {csv_path}")

    # Track label → color index (for consistent coloring)
    label_colors = {}

    for _, row in df.iterrows():
        x1, y1 = int(row['x1']), int(row['y1'])
        x2, y2 = int(row['x2']), int(row['y2'])
        label = str(row['label'])
        instance = str(row['instance'])  # e.g. "Person 1"

        # Assign consistent color per label
        if label not in label_colors:
            label_colors[label] = len(label_colors)
        color = _color(label_colors[label])

        # Draw bounding box
        cv2.rectangle(img, (x1, y1), (x2, y2), color, box_thickness)

        # Draw label background + text
        _put_label(img, instance, x1, y1, color, font_scale)

    # Save result
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(output_path, img)
    print(f"✓ Annotated image saved: {output_path}")
    return output_path


def _put_label(img, text, x1, y1, color, font_scale=1.0):
    """Draw filled label background + white text (same style as annotate.py)."""
    font_thickness = 2
    (tw, th), bl = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)
    padding = 6
    cv2.rectangle(img, (x1, y1 - th - bl - padding), (x1 + tw + padding, y1), color, -1)
    cv2.putText(img, text, (x1 + 4, y1 - bl - 4),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Redraw bounding boxes from CSV onto image")
    parser.add_argument("--image", required=True, help="Path to original image")
    parser.add_argument("--csv", required=True, help="Path to detections CSV")
    parser.add_argument("--output", default="annotated_result.jpg", help="Output image path")
    parser.add_argument("--thickness", type=int, default=4, help="Box line thickness (default: 4)")
    parser.add_argument("--font-scale", type=float, default=1.0, help="Label font scale (default: 1.0)")
    args = parser.parse_args()

    draw_annotations(
        args.image, 
        args.csv, 
        args.output,
        box_thickness=args.thickness,
        font_scale=args.font_scale
    )