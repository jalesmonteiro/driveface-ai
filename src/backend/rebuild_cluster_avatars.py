import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

import base64
import io
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
from faces.models import Cluster, Face
from google_integration.services import GoogleDriveService

def rebuild_avatars():
    clusters = Cluster.objects.all()
    print(f"Total clusters in DB: {clusters.count()}")
    updated = 0
    for c in clusters:
        face = c.faces.select_related("photo", "photo__album__owner").order_by("-detection_confidence").first()
        if not face or not face.photo:
            print(f"Cluster {c.label} ({c.id}): No face found")
            continue
        photo = face.photo
        drive = GoogleDriveService(user=photo.album.owner)
        try:
            stream = drive.download_image_stream(photo.google_file_id)
            if not stream:
                print(f"Cluster {c.label}: Stream empty")
                continue
            img = Image.open(stream).convert("RGB")
            w, h = img.size
            x1 = int(face.bbox_xmin * w)
            y1 = int(face.bbox_ymin * h)
            x2 = int(face.bbox_xmax * w)
            y2 = int(face.bbox_ymax * h)
            bw = max(1, x2 - x1)
            bh = max(1, y2 - y1)
            pad_x = int(bw * 0.35)
            pad_y = int(bh * 0.35)
            crop_x1 = max(0, x1 - pad_x)
            crop_y1 = max(0, y1 - pad_y)
            crop_x2 = min(w, x2 + pad_x)
            crop_y2 = min(h, y2 + pad_y)
            face_img = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            face_thumb = face_img.resize((160, 160), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            face_thumb.save(buf, format="WEBP", quality=85)
            b64 = f"data:image/webp;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
            c.avatar_crop_webp = b64
            c.save(update_fields=["avatar_crop_webp"])
            updated += 1
            print(f"[OK] Face cropped for '{c.label}' from {photo.filename} - bbox: [{face.bbox_xmin:.2f}, {face.bbox_ymin:.2f}, {face.bbox_xmax:.2f}, {face.bbox_ymax:.2f}]")
        except Exception as e:
            print(f"[ERR] Error cropping {c.label}: {e}")
    print(f"\nCompleted! {updated}/{clusters.count()} clusters updated with cropped faces.")

if __name__ == "__main__":
    rebuild_avatars()
