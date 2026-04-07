import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import json

# ── Palette ──────────────────────────────────────────────────────────────────
PALETTE_RGB = [(56, 245, 100), (54, 162, 235), (255, 99, 132), (255, 205, 86), (153, 102, 255), (255, 159, 64), (0, 220, 220)]
PALETTE_HEX = ["#38F564", "#36A2EB", "#FF6384", "#FFCD56", "#9966FF", "#FF9F40", "#00DCDC"]

def get_color_index(label):
    return abs(hash(str(label))) % len(PALETTE_RGB)

# ── PIL Export ───────────────────────────────────────────────────────────────
def draw_label_on_pil(img, text, x1, y1, color_rgb, font_size):
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
            
    bbox = draw.textbbox((x1, y1), text, font=font)
    # Background for label text
    draw.rectangle([bbox[0]-5, bbox[1]-5, bbox[2]+5, bbox[3]+5], fill=color_rgb)
    draw.text((x1, y1), text, fill=(255, 255, 255), font=font)

def create_annotated_image(pil_img, boxes, font_size):
    img_copy = pil_img.copy()
    draw = ImageDraw.Draw(img_copy)
    for box in boxes:
        x1, y1, x2, y2 = box["bbox"]
        color = PALETTE_RGB[get_color_index(box["label"])]
        # Border thickness scales with image size
        thickness = max(4, int(img_copy.width * 0.006))
        draw.rectangle([x1, y1, x2, y2], outline=color, width=thickness)
        draw_label_on_pil(img_copy, box["label"], x1, y1, color, font_size)
    return img_copy

# ── The "Clean" Wrapper Component ──────────────────────────────────────────
def st_clean_canvas(image, current_label, storage_key, zoom_level, wrapper_h):
    if image is None: return
    
    w, h = image.size
    disp_w, disp_h = int(w * zoom_level), int(h * zoom_level)
    
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    img_src = f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    
    html = f"""
    <div id="wrapper" style="width:100%; height:{wrapper_h}vh; overflow:auto; border:2px solid #333; background:#0e0e0e; position:relative; border-radius:4px;">
      <div id="container" style="width:{disp_w}px; height:{disp_h}px; position:relative; margin:0 auto;">
        <img src="{img_src}" style="width:100%; height:100%; display:block; user-select:none;" draggable="false">
        <canvas id="c" width="{w}" height="{h}" 
                style="position:absolute; top:0; left:0; width:100%; height:100%; cursor:crosshair; z-index:10;"></canvas>
      </div>
    </div>
    <script>
      const c = document.getElementById('c'), ctx = c.getContext('2d');
      const SKEY = '{storage_key}';
      
      let boxes = JSON.parse(window.parent.localStorage.getItem(SKEY) || '[]');
      let drawing = false, sx, sy, curX, curY;

      const redraw = () => {{
        ctx.clearRect(0,0,c.width,c.height);
        boxes.forEach(b => {{
          ctx.strokeStyle = '#38f564'; ctx.lineWidth = 4;
          ctx.strokeRect(b.bbox[0], b.bbox[1], b.bbox[2]-b.bbox[0], b.bbox[3]-b.bbox[1]);
          ctx.fillStyle = '#38f564'; ctx.font = "bold 20px Arial";
          ctx.fillText(b.label, b.bbox[0], b.bbox[1]-8);
        }});
        if(drawing) {{
          ctx.strokeStyle = "white"; ctx.setLineDash([4,4]); ctx.lineWidth = 2;
          ctx.strokeRect(sx, sy, curX-sx, curY-sy);
          ctx.setLineDash([]);
        }}
      }};

      const getPos = (e) => {{
        const rect = c.getBoundingClientRect();
        return {{ x: (e.clientX-rect.left)*(c.width/rect.width), y: (e.clientY-rect.top)*(c.height/rect.height) }};
      }};

      c.onmousedown = e => {{ const p = getPos(e); drawing = true; sx = p.x; sy = p.y; }};
      c.onmousemove = e => {{ if(!drawing) return; const p = getPos(e); curX = p.x; curY = p.y; redraw(); }};
      c.onmouseup = e => {{
        if(!drawing) return; drawing = false;
        const p = getPos(e);
        if(Math.abs(p.x - sx) > 3) {{
            boxes.push({{label: '{current_label}', bbox: [Math.min(sx,p.x), Math.min(sy,p.y), Math.max(sx,p.x), Math.max(sy,p.y)]}});
            window.parent.localStorage.setItem(SKEY, JSON.stringify(boxes));
        }}
        redraw();
      }};
      c.oncontextmenu = e => {{ e.preventDefault(); boxes.pop(); window.parent.localStorage.setItem(SKEY, JSON.stringify(boxes)); redraw(); }};
      redraw();
    </script>
    """
    # Streamlit component height slightly larger than wrapper height to avoid double scrolls
    st.components.v1.html(html, height=(wrapper_h * 10) + 60)

# ── Main App ─────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="Annotator v8", layout="wide")
    from streamlit_js_eval import streamlit_js_eval

    if "boxes" not in st.session_state: st.session_state.boxes = []
    if "image" not in st.session_state: st.session_state.image = None

    st.sidebar.title("⚙️ Workspace")
    active_label = st.sidebar.text_input("Current Class", value="object")
    
    # CONTROL THE WRAPPER SIZE
    wrapper_h = st.sidebar.slider("Workspace Vertical Height", 50, 95, 90)
    zoom_val = st.sidebar.slider("Zoom Range", 0.1, 5.0, 1.0, 0.1)
    font_size = st.sidebar.slider("Export Label Size", 10, 250, 60)
    
    uploaded_file = st.sidebar.file_uploader("1. Upload Image", type=["jpg", "png"])
    if uploaded_file:
        img = Image.open(uploaded_file).convert("RGB")
        if st.session_state.get("image_name") != uploaded_file.name:
            st.session_state.image, st.session_state.image_name = img, uploaded_file.name
            st.session_state.boxes = []

    if not st.session_state.image:
        st.info("Upload an image in the sidebar to start annotating.")
        return

    storage_key = f"ann_v8_{st.session_state.image_name}"
    
    # CSV Import Force-Sync
    st.sidebar.divider()
    csv_file = st.sidebar.file_uploader("2. Import CSV", type=["csv"])
    if csv_file:
        df_in = pd.read_csv(csv_file)
        st.session_state.boxes = [{"label": str(r.label), "bbox": [int(r.x1), int(r.y1), int(r.x2), int(r.y2)]} for r in df_in.itertuples()]
        streamlit_js_eval(js_expressions=f"window.parent.localStorage.setItem('{storage_key}', '{json.dumps(st.session_state.boxes)}')", key="csv_sync_v8")
        st.sidebar.success("CSV Loaded & Visible")

    # Workspace
    st.subheader(f"🖼️ {st.session_state.image_name}")
    st_clean_canvas(st.session_state.image, active_label, storage_key, zoom_val, wrapper_h)
    
    if st.button("🔄 SAVE & SYNC PROGRESS", type="primary", use_container_width=True):
        js_data = streamlit_js_eval(js_expressions=f"window.parent.localStorage.getItem('{storage_key}')", key="sync_final_v8")
        if js_data:
            st.session_state.boxes = json.loads(js_data)
            st.rerun()

    # Data & Export
    st.divider()
    if st.session_state.boxes:
        st.subheader("📋 Labels & Download")
        df = pd.DataFrame([{"label": b["label"], "x1": b["bbox"][0], "y1": b["bbox"][1], "x2": b["bbox"][2], "y2": b["bbox"][3]} for b in st.session_state.boxes])
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", hide_index=True)
        st.session_state.boxes = [{"label": r.label, "bbox": [int(r.x1), int(r.y1), int(r.x2), int(r.y2)]} for r in edited_df.itertuples()]

        colA, colB = st.columns(2)
        with colA:
            annot_img = create_annotated_image(st.session_state.image, st.session_state.boxes, font_size)
            buf = io.BytesIO()
            annot_img.save(buf, format="JPEG")
            st.download_button("📥 Final Image", buf.getvalue(), "annotated_v8.jpg", use_container_width=True)
        with colB:
            csv_out = edited_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Final CSV", csv_out, "detections_v8.csv", use_container_width=True)

if __name__ == "__main__":
    main()