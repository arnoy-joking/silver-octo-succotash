import os
import tempfile
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

YT_DLP = 'yt-dlp'  # Will use system-installed version

def get_subtitles(video_url, language='en'):
    """Fetch subtitles and return as text"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            cmd = [
                YT_DLP,
                '--skip-download',
                '--write-subs',
                '--write-auto-subs',
                '--sub-lang', language,
                '--sub-format', 'vtt',
                '--convert-subs', 'srt',
                '--output', f'{tmp_dir}/subtitle',
                video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return None, result.stderr
            
            # Find subtitle file
            for ext in ['.srt', '.vtt']:
                subtitle_file = f"{tmp_dir}/subtitle.{language}{ext}"
                if os.path.exists(subtitle_file):
                    with open(subtitle_file, 'r', encoding='utf-8') as f:
                        return f.read(), None
            
            return None, "No subtitles found"
            
        except Exception as e:
            return None, str(e)

@app.route('/api/subtitles', methods=['GET'])
def api_subtitles():
    video_url = request.args.get('url')
    language = request.args.get('lang', 'en')
    
    if not video_url:
        return jsonify({'error': 'Missing URL parameter'}), 400
    
    subtitles, error = get_subtitles(video_url, language)
    
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify({'subtitles': subtitles})

if __name__ == '__main__':
    app.run(debug=True)