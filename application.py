import os
import random
from flask import Flask, request, render_template
from flask_compress import Compress
import boto3
import json


app = Flask(__name__)
Compress(app)


def load_master_metadata():
    metadata_path = os.path.join("metadata", "exif_metadata.json")

    try:
        with open(metadata_path, "r") as f:
            data = json.load(f)

            if isinstance(data, dict):
                print(f"✅ Loaded {len(data)} metadata entries (dict format)")
                return data

            elif isinstance(data, list):
                print(f"🔁 Detected list format — converting...")
                converted = {
                    item["filename"]: {k: v for k, v in item.items() if k != "filename"}
                    for item in data if "filename" in item
                }
                print(f"✅ Converted {len(converted)} metadata entries")
                return converted

            else:
                print("❌ Unknown metadata structure.")
                return {}

    except Exception as e:
        print(f"⚠️ Failed to load metadata: {e}")
        return {}
master_metadata = load_master_metadata()


# S3 config
bucket_name = 'fuji-images'
region = 'us-east-2'
cloudfront_domain = os.getenv("CLOUDFRONT_DOMAIN")  # optional

s3 = boto3.client('s3')
objects = s3.list_objects_v2(Bucket=bucket_name)

# Build image URLs from S3 keys
s3_images = []
if 'Contents' in objects:
    for obj in objects['Contents']:
        key = obj['Key']
        if key.lower().endswith(('.jpg', '.jpeg', '.png')):
            if cloudfront_domain:
                url = f"https://{cloudfront_domain}/{key}"
            else:
                url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{key}"
            s3_images.append({"key": key, "url": url})
else:
    print("⚠️ No images found in S3 bucket.")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/viewer")
def viewer():
    if not s3_images:
        return "No images available from S3."

    selected_key = request.args.get("filename")
    if request.args.get("random") or not selected_key:
        selected_image = random.choice(s3_images)
    else:
        selected_image = next((img for img in s3_images if img["key"] == selected_key), None)
        if not selected_image:
            return f"Image not found: {selected_key}"

    # Extract just the filename (e.g., IMG_1234.jpg)
    filename = os.path.basename(selected_image["key"])
    metadata = master_metadata.get(filename, {"Note": "No metadata found."})

    return render_template("Viewer.html",
                           image_files=s3_images,
                           selected_file=selected_image["url"],
                           selected_key=selected_image["key"],
                           metadata=metadata)

@app.route("/about")
def about_page():
    return render_template("About.html")

@app.route("/contact")
def contact_page():
    return render_template("Contact.html")

if __name__ == "__main__":
    app.run(debug=True)
