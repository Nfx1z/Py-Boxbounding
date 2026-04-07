# Image Annotation Toolkit

## Installation
Install the required Python packages:
```bash
pip install opencv-python pandas
```

## 1. Manual Annotation (`annotate.py`)
Draw bounding boxes on an image interactively and export the results.

### Usage
```bash
python annotate.py --image path/to/image.jpg
```
To specify a custom output folder:
```bash
python annotate.py --image path/to/image.jpg --output my_results/
```

### Controls
- **Left-click + Drag**: Draw a bounding box
- **Enter / Space**: Confirm the current box and type the label in the terminal
- **Z**: Undo the last drawn box
- **S**: Save all annotations and exit
- **Q / Esc**: Quit without saving

### Output Files
After pressing `S`, the tool generates:
- `image_annotated.jpg` – Image with boxes and labels drawn on it
- `image_detections.csv` – Per-box data: `id, label, instance, x1, y1, x2, y2, width, height, center_x, center_y`
- `image_summary.csv` – Object counts: `object, count`

---

## 2. CSV to Image (`csv_to_image.py`)
Redraw bounding boxes from a detections CSV file onto an image. Useful for verifying annotations or regenerating visuals.

### Usage
```bash
python csv_to_image.py --image path/to/image.jpg --csv path/to/detections.csv --output result.jpg
```

### Optional Arguments
- `--output`: Output image path (default: `annotated_result.jpg`)
- `--thickness`: Bounding box line thickness (default: `4`)
- `--font-scale`: Label font scale (default: `1.0`)

---

## Typical Workflow
1. Annotate an image:
   ```bash
   python annotate.py --image photo.jpg --output dataset/
   ```
2. Open `dataset/photo_detections.csv` in a spreadsheet editor to review or edit coordinates/labels if needed.
3. Redraw the boxes to verify changes:
   ```bash
   python csv_to_image.py --image photo.jpg --csv dataset/photo_detections.csv --output verified.jpg
   ```