from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
import ffmpeg
import yt_dlp as youtube_dl
import os
import uuid
import secrets
import subprocess

app = Flask(__name__)
CORS(app)

@app.route('/process-video', methods=['POST'])
def process_video():
    data = request.json
    video_url = data['url']

    # Download video from YouTube
    video_file = f"video_{uuid.uuid4().hex}.mp4"
    ydl_opts = {
        'outtmpl': video_file,
        'format': 'mp4'
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    # Get video duration
    probe = ffmpeg.probe(video_file, v='error', select_streams='v:0', show_entries='stream=duration')
    duration = float(probe['streams'][0]['duration'])

    # Define segment length in seconds
    segment_length = 60
    file_urls = []

    for start_time in range(0, int(duration), segment_length):
        end_time = min(start_time + segment_length, duration)
        short_file = f"short_{uuid.uuid4().hex}.mp4"
        ffmpeg.input(video_file, ss=start_time, to=end_time).output(short_file).run()
        file_urls.append(f'http://localhost:5000/download/{short_file}')

    # Clean up the downloaded video
    os.remove(video_file)

    # Return file URLs
    return jsonify({'fileUrls': file_urls})

@app.route('/download-video', methods=['POST'])
def download_video():
    data = request.json
    video_url = data['url']

    # Download the complete video from YouTube
    video_file = f"complete_video_{uuid.uuid4().hex}.mp4"
    ydl_opts = {
        'outtmpl': video_file,
        'format': 'mp4'
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    # Return the URL for downloading the complete video
    return jsonify({'fileUrl': f'http://localhost:5000/download/{video_file}'})

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('.', filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
