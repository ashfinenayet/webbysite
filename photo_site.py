import os
import random
from flask import Flask, render_template_string, send_from_directory, request, render_template
import exifread
import pandas as pd

app = Flask(__name__)

IMG_DIR = '/Users/ashfi/Documents/FUJI Edits'
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')
image_files = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(IMAGE_EXTENSIONS)]



@app.route("/viewer")
def viewer():
    selected_file = request.args.get("filename")
    if request.args.get("random") or not selected_file:
        selected_file = random.choice(image_files)

    image_path = os.path.join(IMG_DIR, selected_file)
    metadata = {}

    with open(image_path, 'rb') as f:
        tags = exifread.process_file(f, details=False)
        metadata = {str(tag): str(tags[tag]) for tag in tags}

    return render_template("Viewer.html",
                                  image_files=image_files,
                                  selected_file=selected_file,
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