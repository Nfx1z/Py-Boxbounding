"""
Manual Bounding Box Annotation Tool
====================================
Draw boxes yourself on any image, label each one, then export:
  - Annotated image  (boxes + labels drawn on it)
  - Detections CSV   (id, label, instance, x1, y1, x2, y2, width, height, cx, cy)
  - Summary CSV      (how many of each object: computer=2, monitor=1, …)

Install:
    pip install opencv-python pandas

Usage:
    python annotate.py --image photo.jpg
    python annotate.py --image photo.jpg --output my_results/

Controls:
    Left-click + drag  →  draw a box
    Enter / Space      →  confirm current box (then type label in terminal)
    Z                  →  undo last box
    S                  →  save & export everything and quit
    Q / Esc            →  quit WITHOUT saving
"""

import argparse
import os
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import pandas as pd


# ── colour palette (BGR) ─────────────────────────────────────────────────────
PALETTE = [
    (56, 245, 100), (54, 162, 235), (255, 99, 132), (255, 205, 86),
    (153, 102, 255), (255, 159, 64), (0, 220, 220), (220, 60, 60),
    (60, 179, 113), (255, 140, 0),
]

def _color(idx: int):
    return PALETTE[idx % len(PALETTE)]


# ── state ─────────────────────────────────────────────────────────────────────
class Annotator:
    def __init__(self, image_path: str, output_dir: str):
        self.image_path = Path(image_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.original   = cv2.imread(str(self.image_path))
        if self.original is None:
            raise FileNotFoundError(f"Cannot open: {image_path}")

        self.canvas     = self.original.copy()
        self.boxes      = []           # list of {"label": str, "bbox": [x1,y1,x2,y2]}
        self.drawing    = False
        self.start      = (-1, -1)
        self.end        = (-1, -1)
        self.label_colors = {}         # label → colour index

        # unique instance counters per label  e.g. {"computer": 2}
        self.instance_count = defaultdict(int)

    # ── mouse callback ────────────────────────────────────────────────────────
    def mouse_cb(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start   = (x, y)
            self.end     = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            self.end = (x, y)
            self._redraw(live_box=(self.start, self.end))

        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            self.end = (x, y)
            self._redraw(live_box=(self.start, self.end))

    # ── redraw canvas from scratch ────────────────────────────────────────────
    def _redraw(self, live_box=None):
        self.canvas = self.original.copy()
        for entry in self.boxes:
            x1, y1, x2, y2 = entry["bbox"]
            color = _color(self._label_idx(entry["label"]))
            cv2.rectangle(self.canvas, (x1, y1), (x2, y2), color, 5)
            self._put_label(self.canvas, entry["display"], x1, y1, color)

        if live_box:
            (sx, sy), (ex, ey) = live_box
            cv2.rectangle(self.canvas, (sx, sy), (ex, ey), (200, 200, 200), 3)

        cv2.imshow("Annotator  —  draw box, then press ENTER to label  |  Z=undo  S=save  Q=quit",
                   self.canvas)

    def _label_idx(self, label: str) -> int:
        if label not in self.label_colors:
            self.label_colors[label] = len(self.label_colors)
        return self.label_colors[label]

    @staticmethod
    def _put_label(img, text, x1, y1, color):
        (tw, th), bl = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.85, 2)
        cv2.rectangle(img, (x1, y1 - th - bl - 4), (x1 + tw + 4, y1), color, -1)
        cv2.putText(img, text, (x1 + 2, y1 - bl - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA)

    # ── confirm a drawn box ───────────────────────────────────────────────────
    def confirm_box(self):
        x1 = min(self.start[0], self.end[0])
        y1 = min(self.start[1], self.end[1])
        x2 = max(self.start[0], self.end[0])
        y2 = max(self.start[1], self.end[1])

        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            print("  Box too small — ignored.")
            return

        print(f"\n  Box drawn at  x1={x1}  y1={y1}  x2={x2}  y2={y2}")
        label = input("  Enter label for this box (e.g. computer, monitor): ").strip()
        if not label:
            print("  No label entered — box discarded.")
            return

        self.instance_count[label] += 1
        n       = self.instance_count[label]
        display = f"{label} {n}"

        self.boxes.append({"label": label, "display": display, "bbox": [x1, y1, x2, y2]})
        print(f"  ✓ Saved as '{display}'")
        self._redraw()

    # ── undo ──────────────────────────────────────────────────────────────────
    def undo(self):
        if not self.boxes:
            print("  Nothing to undo.")
            return
        removed = self.boxes.pop()
        # decrement instance counter
        self.instance_count[removed["label"]] -= 1
        print(f"  Undone: {removed['display']}")
        self._redraw()

    # ── save ──────────────────────────────────────────────────────────────────
    def save(self):
        stem = self.image_path.stem

        # ── annotated image ───────────────────────────────────────────────────
        img_out = self.output_dir / f"{stem}_annotated.jpg"
        cv2.imwrite(str(img_out), self.canvas)
        print(f"\n  Annotated image  →  {img_out}")

        # ── per-box detections CSV ────────────────────────────────────────────
        rows = []
        for i, entry in enumerate(self.boxes, 1):
            x1, y1, x2, y2 = entry["bbox"]
            rows.append({
                "id":       i,
                "label":    entry["label"],
                "instance": entry["display"],          # e.g. "computer 1"
                "x1": x1,  "y1": y1,
                "x2": x2,  "y2": y2,
                "width":    x2 - x1,
                "height":   y2 - y1,
                "center_x": (x1 + x2) // 2,
                "center_y": (y1 + y2) // 2,
            })

        det_csv = self.output_dir / f"{stem}_detections.csv"
        pd.DataFrame(rows).to_csv(det_csv, index=False)
        print(f"  Detections CSV   →  {det_csv}")

        # ── summary CSV ───────────────────────────────────────────────────────
        counts = Counter(e["label"] for e in self.boxes)
        summary_rows = [{"object": k, "count": v}
                        for k, v in sorted(counts.items(), key=lambda x: -x[1])]
        sum_csv = self.output_dir / f"{stem}_summary.csv"
        pd.DataFrame(summary_rows).to_csv(sum_csv, index=False)
        print(f"  Summary CSV      →  {sum_csv}")

        # ── terminal summary ──────────────────────────────────────────────────
        print("\n  ── Annotation Summary ──────────────────")
        for obj, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"     {obj:<22} {cnt:>3}")
        print("  ────────────────────────────────────────")

        return str(img_out), str(det_csv), str(sum_csv)

    # ── main loop ─────────────────────────────────────────────────────────────
    def run(self):
        win = "Annotator  —  draw box, then press ENTER to label  |  Z=undo  S=save  Q=quit"
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(win, self.mouse_cb)
        self._redraw()

        print("\n════════════════════════════════════════")
        print("  MANUAL ANNOTATION TOOL")
        print("  ─────────────────────────────────────")
        print("  Left-click + drag  draw a box")
        print("  Enter / Space      confirm box → type label")
        print("  Z                  undo last box")
        print("  S                  save & quit")
        print("  Q / Esc            quit without saving")
        print("════════════════════════════════════════\n")

        while True:
            key = cv2.waitKey(20) & 0xFF

            if key in (13, 32):          # Enter or Space → confirm box
                self.confirm_box()

            elif key in (ord('z'), ord('Z')):
                self.undo()

            elif key in (ord('s'), ord('S')):
                self.save()
                break

            elif key in (ord('q'), ord('Q'), 27):   # Q or Esc
                print("\n  Quit without saving.")
                break

            if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
                break  # window closed by user

        cv2.destroyAllWindows()


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manual bounding-box annotation tool")
    parser.add_argument("--image",  required=True, help="Path to the image to annotate")
    parser.add_argument("--output", default="annotation_results", help="Output folder")
    args = parser.parse_args()

    Annotator(args.image, args.output).run()