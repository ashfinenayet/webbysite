# app.py

import os
import json
import random
from functools import lru_cache
from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError
from flask import Flask, request, render_template, send_from_directory

# ---------------- CONFIG ----------------
bucket_name = os.getenv("S3_BUCKET", "fuji-images")
region = os.getenv("AWS_REGION", "us-east-2")
cloudfront_domain = os.getenv("CLOUDFRONT_DOMAIN")  # e.g., d123abc.cloudfront.net
METADATA_PATH = os.getenv("METADATA_PATH", os.path.join("metadata", "exif_metadata.json"))
# ----------------------------------------

app = Flask(__name__)
s3 = boto3.client("s3", region_name=region)

# ---------- METADATA LOADER (robust, normalized) ----------
def _basename(name: str) -> str:
    """Normalize to base filename (strip any folder prefixes)."""
    return os.path.basename(name)

@lru_cache(maxsize=1)
def load_master_metadata(path: str = METADATA_PATH) -> dict:
    """
    Always return a dict keyed by base filename:
        { "DSCF3623.jpg": {...}, "DSCF3624.jpg": {...}, ... }
    Accepts a JSON file path or a JSON string. Handles dict-or-list JSON.
    - If dict: keys may include paths; they are normalized to basenames.
    - If list: expects a 'filename' field per item; normalized to basename.
    """
    # Allow injecting raw JSON string via env
    if isinstance(path, str) and path.strip().startswith(("{", "[")):
        data = json.loads(path)
    else:
        with open(path, "r") as f:
            data = json.load(f)

    out = {}
    if isinstance(data, dict):
        for k, v in data.items():
            out[_basename(k)] = v if isinstance(v, dict) else {"value": v}
        return out

    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            fname = item.get("filename")
            if not fname:
                continue
            base = _basename(fname)
            out[base] = {k: v for k, v in item.items() if k != "filename"}
        return out

    return {}

master_metadata = load_master_metadata()

# ---------- URL BUILDING / S3 HELPERS ----------
def build_cdn_url(key: str) -> str:
    """
    Public URL for a given S3 key via CloudFront (if set) or S3.
    URL-encodes path segments except '/'.
    """
    enc = quote(key, safe="/")
    if cloudfront_domain:
        return f"https://{cloudfront_domain}/{enc}"
    return f"https://{bucket_name}.s3.{region}.amazonaws.com/{enc}"

@lru_cache(maxsize=4096)
def s3_exists(key: str) -> bool:
    """HEAD the object to check existence (raw key, not encoded)."""
    try:
        s3.head_object(Bucket=bucket_name, Key=key)
        return True
    except ClientError as e:
        # Treat 404/NoSuchKey/NotFound as missing; everything else also False
        return False
    except Exception:
        return False

def best_variant_url(original_key: str) -> str:
    """
    Prefer downsized variants if present; else original.
    Order: 1600 (avif/webp/jpg) → 960 (avif/webp/jpg) → original.
    """
    base, _ = os.path.splitext(original_key)
    candidates = [
        f"{base}_1600.avif", f"{base}_1600.webp", f"{base}_1600.jpg",
        f"{base}_960.avif",  f"{base}_960.webp",  f"{base}_960.jpg",
        original_key,
    ]
    for key in candidates:
        if s3_exists(key):
            return build_cdn_url(key)
    return build_cdn_url(original_key)

def list_images(prefix: str = "") -> list[dict]:
    """List image objects once at startup; returns [{'key', 'url'}, ...]."""
    out = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            if key.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".avif")):
                out.append({"key": key, "url": build_cdn_url(key)})
    return out

# Build once (optionally refresh via admin endpoint if bucket changes)
s3_images = list_images()

# -------------------- ROUTES --------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/viewer")
def viewer():
    if not s3_images:
        return "No images available from S3.", 200

    selected_key = request.args.get("filename")
    if request.args.get("random") or not selected_key:
        selected = random.choice(s3_images)
    else:
        selected = next((img for img in s3_images if img["key"] == selected_key), None)
        if not selected:
            return f"Image not found: {selected_key}", 404

    raw_key = selected["key"]                 # e.g., "images/DSCF3623.jpg"
    filename = _basename(raw_key)            # -> "DSCF3623.jpg"
    metadata = master_metadata.get(filename, {"Note": "No metadata found."})

    # Choose fast variant if available
    selected_variant_url = best_variant_url(raw_key)

    return render_template(
        "Viewer.html",
        image_files=s3_images,
        selected_file=selected_variant_url,   # variant or original
        selected_key=raw_key,
        metadata=metadata,
        cloudfront_domain=cloudfront_domain,
        bucket_name=bucket_name,
        region=region,
    )

@app.route("/about")
def about_page():
    return render_template("About.html")

@app.route("/contact")
def contact_page():
    return render_template("Contact.html")

# Optional: quiet the favicon 404s
@app.route("/favicon.ico")
def favicon():
    return send_from_directory("static", "favicon.ico", mimetype="image/x-icon")

# --------------- MAIN ---------------
if __name__ == "__main__":
    # For dev only; use a real WSGI server in prod
    app.run(debug=True)
