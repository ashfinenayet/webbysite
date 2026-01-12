import os
import boto3
from PIL import Image

# -------- CONFIG --------
BUCKET = "fuji-images"        # your bucket
REGION = "us-east-2"          # your region
LOCAL_DIR = "images"          # local folder containing originals
SIZES = [960, 1600]           # target widths in px
QUALITY = 80                  # for WebP/JPEG; AVIF quality ~30-50 recommended
# ------------------------

s3 = boto3.client("s3", region_name=REGION)

def save_and_upload_variant(img, base_name, size, fmt, ext, content_type, quality):
    """Resize and upload one variant to S3"""
    img_copy = img.copy()
    img_copy.thumbnail((size, size), Image.LANCZOS)

    out_name = f"{os.path.splitext(base_name)[0]}_{size}.{ext}"
    tmp_path = f"/tmp/{out_name}"

    save_kwargs = {}
    if fmt == "JPEG":
        save_kwargs = {"quality": quality, "progressive": True}
    elif fmt == "WEBP":
        save_kwargs = {"quality": quality, "method": 6}
    elif fmt == "AVIF":
        save_kwargs = {"quality": 40}  # AVIF quality scale different

    img_copy.save(tmp_path, fmt, **save_kwargs)

    with open(tmp_path, "rb") as f:
        s3.put_object(
            Bucket=BUCKET,
            Key=out_name,
            Body=f,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable"
        )
    print(f"✅ Uploaded {out_name} ({fmt}, {size}px)")

def process_image(path):
    base_name = os.path.basename(path)
    try:
        with Image.open(path) as img:
            for size in SIZES:
                save_and_upload_variant(img, base_name, size, "JPEG", "jpg", "image/jpeg", QUALITY)
                save_and_upload_variant(img, base_name, size, "WEBP", "webp", "image/webp", QUALITY)
                save_and_upload_variant(img, base_name, size, "AVIF", "avif", "image/avif", QUALITY)
    except Exception as e:
        print(f"⚠️ Skipped {base_name}: {e}")

def main():
    for file in os.listdir(LOCAL_DIR):
        if file.lower().endswith((".jpg", ".jpeg", ".png")):
            process_image(os.path.join(LOCAL_DIR, file))

if __name__ == "__main__":
    main()
