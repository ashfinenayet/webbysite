import os
from flask import Flask, render_template_string, redirect, request, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Replace with your Spotify app credentials
SPOTIPY_CLIENT_ID = "f7df24f592d54815927d22a509353139"
SPOTIPY_CLIENT_SECRET = "a88d835440fe49739effefdd64fc7ce5"
SPOTIPY_REDIRECT_URI = "http://localhost:8888/callback"
SCOPE = "user-library-read"

@app.route('/')
def index():
    if 'token_info' not in session:
        auth_url = SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=SCOPE
        ).get_authorize_url()
        return redirect(auth_url)
    
    token_info = session['token_info']
    sp = spotipy.Spotify(auth=token_info['access_token'])
    results = sp.current_user_saved_tracks(limit=50)
    covers = [item['track']['album']['images'][0]['url'] for item in results['items'] if item['track']['album']['images']]

    return render_template_string(GALLERY_TEMPLATE, covers=covers)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SCOPE
    )
    token_info = oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect('/')

GALLERY_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
  <title>Spotify Liked Covers</title>
  <style>
    body {
      background: #111;
      color: white;
      font-family: monospace;
      text-align: center;
    }
    h1 {
      padding: 20px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: 15px;
      padding: 20px;
    }
    img {
      width: 100%;
      border: 2px solid #888;
      border-radius: 6px;
      transition: 0.3s;
    }
    img:hover {
      transform: scale(1.05);
      border-color: white;
    }
  </style>
</head>
<body>
  <h1>🎵 Spotify Liked Album Covers</h1>
  <div class="grid">
    {% for cover in covers %}
      <img src="{{ cover }}" alt="Album Cover">
    {% endfor %}
  </div>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(debug=True, port=8888)