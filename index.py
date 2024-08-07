from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import yt_dlp as youtube_dl
import ffmpeg
import uuid
import json

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
METADATA_FILE = 'metadata.json'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {'shorts': []}

def save_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)

@app.route('/process-video', methods=['POST'])
def process_video():
    data = request.json
    video_url = data.get('url')
    segment_length = data.get('segment_length',300)  # Default to 60 seconds if not provided
    
    # Validate segment_length
    try:
        segment_length = int(segment_length)
        if segment_length <= 0:
            raise ValueError("Segment length must be a positive integer.")
    except (ValueError, TypeError) as e:
        return jsonify({'error': 'Invalid segment length', 'details': str(e)}), 400

    video_file = os.path.join(UPLOAD_FOLDER, f"video_{uuid.uuid4().hex}.mp4")
    ydl_opts = {'outtmpl': video_file, 'format': 'mp4'}
    
    # Download the video
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except Exception as e:
        return jsonify({'error': 'Error downloading video', 'details': str(e)}), 500

    # Probe video duration
    try:
        probe = ffmpeg.probe(video_file, v='error', select_streams='v:0', show_entries='stream=duration')
        duration = float(probe['streams'][0]['duration'])
    except ffmpeg.Error as e:
        return jsonify({'error': 'Error probing video duration', 'details': str(e)}), 500

    file_urls = []
    for start_time in range(0, int(duration), segment_length):
        end_time = min(start_time + segment_length, duration)
        short_file = os.path.join(UPLOAD_FOLDER, f"short_{uuid.uuid4().hex}.mp4")
        try:
            ffmpeg.input(video_file, ss=start_time, to=end_time).output(short_file).run(overwrite_output=True)
            file_url = f'http://localhost:5000/download/{os.path.basename(short_file)}'
            file_urls.append(file_url)
        except ffmpeg.Error as e:
            return jsonify({'error': 'Error processing video segment', 'details': str(e)}), 500
    
    os.remove(video_file)
    
    return jsonify({'fileUrls': file_urls})

@app.route('/download/<filename>')
def download_file(filename):
    print("dd",send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True, mimetype='video/mp4'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True, mimetype='video/mp4')

@app.route('/list-shorts', methods=['GET'])
def list_shorts():
    metadata = load_metadata()
    return jsonify(metadata)

if __name__ == '__main__':
    app.run(debug=True)
