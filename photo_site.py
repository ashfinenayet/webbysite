import os
import random
from flask import Flask, render_template_string, send_from_directory, request
import exifread
import pandas as pd

app = Flask(__name__)

IMG_DIR = '/Users/ashfi/Documents/FUJI Edits'
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')
image_files = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(IMAGE_EXTENSIONS)]

HTML_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <title>EXIF Viewer</title>
  <meta charset="UTF-8" />
  <link rel="stylesheet" href="https://unpkg.com/@sakun/system.css" />
  <style>
    .window {
      position: absolute;
      padding: 0;
      user-select: none;
      resize: both;
      overflow: auto;
    }
    .title-bar {
      cursor: move;
    }
    .image-container {
      position: relative;
    }
    .loader {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 40px;
      height: 40px;
      background-image: url('https://upload.wikimedia.org/wikipedia/commons/d/de/Mac_Loading_Icon.gif');
      background-size: contain;
      background-repeat: no-repeat;
      z-index: 10;
    }
    img.fade-in {
      opacity: 0;
      transition: opacity 0.5s ease-in;
    }
    img.fade-in.loaded {
      opacity: 1;
    }
    .menu-bar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 1000;
      background: #c0c0c0;
      display: flex;
      align-items: center;
      padding: 4px 12px;
      font-family: inherit;
      font-size: 14px;
      border-bottom: 2px solid black;
      box-shadow: inset 0 -1px 0 #fff;
      gap: 1rem;
    }
    .menu-bar button {
      background: none;
      border: none;
      font-weight: bold;
      cursor: pointer;
    }
    .metadata-scrollable {
    max-height: 300px;
    overflow-y: auto;
    padding-right: 10px;
    }

    body {
      padding-top: 30px;
    }
  </style>
  <script>
    document.addEventListener('DOMContentLoaded', () => {
      document.querySelectorAll('.window').forEach((win, i) => {
        const titleBar = win.querySelector('.title-bar');
        let isDragging = false;
        let offsetX, offsetY;
        const id = `window-${i}`;

        const saved = JSON.parse(localStorage.getItem(id));
        if (saved) {
          win.style.left = saved.left;
          win.style.top = saved.top;
        }

        titleBar.addEventListener('mousedown', e => {
          isDragging = true;
          offsetX = e.clientX - win.offsetLeft;
          offsetY = e.clientY - win.offsetTop;
          win.style.zIndex = 1000;
        });

        document.addEventListener('mousemove', e => {
          if (isDragging) {
            win.style.left = `${e.clientX - offsetX}px`;
            win.style.top = `${e.clientY - offsetY}px`;
          }
        });

        document.addEventListener('mouseup', () => {
          if (isDragging) {
            localStorage.setItem(id, JSON.stringify({
              left: win.style.left,
              top: win.style.top
            }));
          }
          isDragging = false;
        });
      });

      const img = document.querySelector('img.fade-in');
      if (img) {
        img.addEventListener('load', () => {
          img.classList.add('loaded');
          const loader = document.querySelector('.loader');
          if (loader) loader.style.display = 'none';
        });
      }
    });
  </script>
</head>
<body>
  <div class="menu-bar">
  <a href="/" class="btn">Home</a>
  <a href="/contact" class="btn">Contact</a>
  <a href="/about" class="btn">About</a>
</div>

  <div class="window" style="width: 40rem; top: 50px; left: 50px;">
    <div class="title-bar">
      <button aria-label="Close" class="close"></button>
      <h1 class="title">EXIF Viewer</h1>
      <button aria-label="Resize" class="resize"></button>
    </div>
    <div class="separator"></div>
    <div class="window-pane">
      <form method="get">
        <section class="field-row" style="justify-content: space-between;">
          <label for="filename">Choose Image:</label>
          <select name="filename" id="filename" onchange="this.form.submit()">
            {% for file in image_files %}
              <option value="{{ file }}" {% if file == selected_file %}selected{% endif %}>{{ file }}</option>
            {% endfor %}
          </select>
          <button class = "btn" type="submit" name="random" value="1">🎲 Random</button>
        </section>
      </form>
    </div>
  </div>

  {% if selected_file %}
  <div class="window" style="width: 40rem; top: 150px; left: 100px;">
    <div class="title-bar">
      <button aria-label="Close" class="close"></button>
      <h1 class="title">Preview</h1>
      <button aria-label="Resize" class="resize"></button>
    </div>
    <div class="separator"></div>
    <div class="window-pane image-container">
      <div class="loader"></div>
      <img class="fade-in" src="/image/{{ selected_file }}" alt="Selected Photo" style="max-width: 100%; height: auto; display: block; margin: auto;">
    </div>
  </div>

  <div class="window" style="width: 40rem; top: 300px; left: 150px;">
    <div class="title-bar">
      <button aria-label="Close" class="close"></button>
      <h1 class="title">Metadata</h1>
      <button aria-label="Resize" class="resize"></button>
    </div>
    <div class="separator"></div>
    <div class="window-pane">
      <table class="interactive" style="width: 100%;">
        <tbody>
          {% for key, value in metadata.items() %}
            <tr><td><b>{{ key }}</b></td><td>{{ value }}</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  {% endif %}
</body>
</html>
'''

@app.route("/image/<filename>")
def serve_image(filename):
    return send_from_directory(IMG_DIR, filename)

@app.route("/")
def index():
    selected_file = request.args.get("filename")
    if request.args.get("random") or not selected_file:
        selected_file = random.choice(image_files)

    image_path = os.path.join(IMG_DIR, selected_file)
    metadata = {}

    with open(image_path, 'rb') as f:
        tags = exifread.process_file(f, details=False)
        metadata = {str(tag): str(tags[tag]) for tag in tags}

    return render_template_string(HTML_TEMPLATE,
                                  image_files=image_files,
                                  selected_file=selected_file,
                                  metadata=metadata)
@app.route("/about")
def about_page():
    return render_template_string(open("About.html").read())

@app.route("/contact")
def contact_page():
    return render_template_string(open("Contact.html").read())

if __name__ == "__main__":
    app.run(debug=True)