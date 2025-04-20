import os
import random
from flask import Flask, render_template_string, send_from_directory, request, render_template
from flask_compress import Compress
import exifread
import pandas as pd
import boto3
from functools import lru_cache

app = Flask(__name__)
Compress(app)

bucket_name = 'fuji-images'
region = 'us-east-2'  # e.g., 'us-east-1'

s3 = boto3.client('s3')

# List all files in the bucket
objects = s3.list_objects_v2(Bucket=bucket_name)
urls = []
# Generate public URLs (assuming your bucket is public or files are public)
if 'Contents' in objects:
    for obj in objects['Contents']:
        key = obj['Key']
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{key}"
        urls.append(url)
else:
    print("No files found.")


IMG_DIR = 'static/images'
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')
image_files = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(IMAGE_EXTENSIONS)]

@lru_cache(maxsize=256)
def get_exif_data(image_path):
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            return {str(tag): str(tags[tag]) for tag in tags}
    except Exception as e:
        return {"Error": f"Could not extract EXIF data: {e}"}


@app.route("/viewer")
def viewer():
    if not image_files:
        return "No images found in local directory."

    selected_file = request.args.get("filename")
    if request.args.get("random") or not selected_file:
        selected_file = random.choice(image_files)

    image_path = os.path.join(IMG_DIR, selected_file)

    # Extract EXIF data from the local image file
    metadata = get_exif_data(image_path)

    return render_template("Viewer.html",
                           image_files=image_files,
                           selected_file=selected_file,
                           metadata=metadata)

@app.route("/image/<filename>")
def serve_image(filename):
    return send_from_directory(IMG_DIR, filename)
@app.route("/")
def home():
    return render_template("index.html")  # Your homepage


@app.route("/about")
def about_page():
    return render_template("About.html")  # Uses templates/About.html

@app.route("/contact")
def contact_page():
    return render_template("Contact.html")  # Uses templates/Contact.html



if __name__ == "__main__":
    app.run(debug=True)