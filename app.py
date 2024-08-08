from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import json
import yt_dlp as youtube_dl
import ffmpeg
import logging
import random
import time

# Setup logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
METADATA_FILE = 'metadata.json'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {'shorts': []}

def save_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)

def download_video_file(video_url, output_path):
    ydl_opts = {'outtmpl': output_path, 'format': 'mp4'}
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        raise

def process_video_task(video_url, segment_length):
    video_file = os.path.join(UPLOAD_FOLDER, f"video_{uuid.uuid4().hex}.mp4")

    # Download the video with a delay
    time.sleep(random.uniform(1, 3))  # Sleep for a random duration between 1 and 3 seconds
    try:
        download_video_file(video_url, video_file)
    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        return {'error': 'Error downloading video', 'details': str(e)}

    # Probe video duration
    try:
        probe = ffmpeg.probe(video_file, v='error', select_streams='v:0', show_entries='stream=duration')
        duration = float(probe['streams'][0]['duration'])
    except ffmpeg.Error as e:
        logging.error(f"Error probing video duration: {e}")
        return {'error': 'Error probing video duration', 'details': str(e)}

    file_urls = []
    for start_time in range(0, int(duration), segment_length):
        end_time = min(start_time + segment_length, duration)
        short_file = os.path.join(UPLOAD_FOLDER, f"short_{uuid.uuid4().hex}.mp4")
        try:
            ffmpeg.input(video_file, ss=start_time, to=end_time).output(short_file).run(overwrite_output=True)
            file_urls.append(f'https://youtube-video-download-api-pg6z.onrender.com/download/{os.path.basename(short_file)}')
        except ffmpeg.Error as e:
            logging.error(f"Error processing video segment: {e}")
            return {'error': 'Error processing video segment', 'details': str(e)}

    os.remove(video_file)  # Clean up the original video file
    return {'fileUrls': file_urls}

@app.route('/process-video', methods=['POST'])
def process_video():
    data = request.json
    video_url = data.get('url')
    segment_length = data.get('segment_length', 60)  # Default to 60 seconds if not provided

    # Validate segment_length
    try:
        segment_length = int(segment_length)
        if segment_length <= 0:
            raise ValueError("Segment length must be a positive integer.")
    except (ValueError, TypeError) as e:
        logging.error(f"Invalid segment length: {e}")
        return jsonify({'error': 'Invalid segment length', 'details': str(e)}), 400

    # Start video processing task
    result = process_video_task(video_url, segment_length)
    if 'error' in result:
        return jsonify(result), 500

    return jsonify(result)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True, mimetype='video/mp4')

@app.route('/download-complete-video', methods=['POST'])
def download_complete_video():
    data = request.json
    video_url = data['url']
    
    # Download the complete video from YouTube
    video_file = os.path.join(UPLOAD_FOLDER, f"complete_video_{uuid.uuid4().hex}.mp4")

    # Download the video with a delay
    time.sleep(random.uniform(1, 3))  # Sleep for a random duration between 1 and 3 seconds
    try:
        download_video_file(video_url, video_file)
    except Exception as e:
        logging.error(f"Error downloading complete video: {e}")
        return jsonify({'error': 'Error downloading video', 'details': str(e)}), 500

    return jsonify({'fileUrl': f'https://youtube-video-download-api-pg6z.onrender.com/download/{os.path.basename(video_file)}'})

@app.route('/list-shorts', methods=['GET'])
def list_shorts():
    metadata = load_metadata()
    return jsonify(metadata)

if __name__ == '__main__':
    app.run(debug=True)
