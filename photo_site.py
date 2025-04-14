import os
import random
from flask import Flask, render_template_string, send_from_directory, request, render_template
import exifread
import pandas as pd
import boto3

app = Flask(__name__)

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


IMG_DIR = '/Users/ashfi/code/R_projects/photos/static/images'
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')
image_files = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(IMAGE_EXTENSIONS)]



import tempfile

@app.route("/viewer")
def viewer():
    # Use image URLs from S3 bucket
    if not urls:
        return "No images available from S3."

    selected_url = request.args.get("url")
    if request.args.get("random") or not selected_url:
        selected_url = random.choice(urls)

    # Extract S3 key from URL
    key = selected_url.split(f"{bucket_name}.s3.{region}.amazonaws.com/")[-1]

    # Download image to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(key)[-1]) as tmp:
        s3.download_fileobj(bucket_name, key, tmp)
        tmp_path = tmp.name

    # Read EXIF data
    metadata = {}
    try:
        with open(tmp_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            metadata = {str(tag): str(tags[tag]) for tag in tags}
    except Exception as e:
        metadata = {"Error": f"Could not extract EXIF data: {e}"}
    finally:
        os.remove(tmp_path)  # Clean up

    return render_template("Viewer.html",
                           image_files=urls,
                           selected_file=selected_url,
                           metadata=metadata)


@app.route("/")
def home():
    return render_template("index.html")  # Your homepage

@app.route("/about")
def about_page():
    return render_template("About.html")  # Uses templates/About.html

@app.route("/contact")
def contact_page():
    return render_template("Contact.html")  # Uses templates/Contact.html

@app.route("/image/<filename>")
def serve_image(filename):
    return send_from_directory(IMG_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True)