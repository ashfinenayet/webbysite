import os
import random
from flask import Flask, request, render_template
from flask_compress import Compress
import boto3

app = Flask(__name__)
Compress(app)

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
        # Match the requested key to a known one
        selected_image = next((img for img in s3_images if img["key"] == selected_key), None)
        if not selected_image:
            return f"Image not found: {selected_key}"

    # Optional: load precomputed EXIF from S3 (disabled for now)
    metadata = {"Note": "Metadata unavailable in this version."}

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
