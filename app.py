import os
import tempfile
import subprocess
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configure production logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
YT_DLP = 'yt-dlp'
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB

@app.route('/health')
def health_check():
    """Production health check"""
    return jsonify({
        "status": "healthy",
        "service": "youtube-subtitle-fetcher",
        "environment": os.environ.get('RAILWAY_ENVIRONMENT', 'development')
    })

@app.route('/api/subtitles', methods=['GET'])
def get_subtitles():
    """Production subtitle endpoint"""
    video_url = request.args.get('url')
    language = request.args.get('lang', 'en')
    
    if not video_url:
        return jsonify({'error': 'YouTube URL is required'}), 400
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cmd = [
                YT_DLP,
                '--skip-download',
                '--write-subs',
                '--write-auto-subs',
                '--sub-lang', language,
                '--sub-format', 'vtt',
                '--convert-subs', 'srt',
                '--output', f'{tmp_dir}/subtitle',
                '--no-warnings',
                video_url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return jsonify({
                    'error': 'Subtitle extraction failed',
                    'details': result.stderr
                }), 500
            
            # Find and return subtitles
            for ext in ['.srt', '.vtt']:
                subtitle_file = f"{tmp_dir}/subtitle.{language}{ext}"
                if os.path.exists(subtitle_file):
                    with open(subtitle_file, 'r', encoding='utf-8') as f:
                        return jsonify({
                            'subtitles': f.read(),
                            'language': language
                        })
            
            return jsonify({'error': 'No subtitles found'}), 404
            
    except Exception as e:
        logger.exception("Subtitle extraction error")
        return jsonify({'error': 'Internal server error'}), 500

# Production WSGI entry point
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    if os.environ.get('RAILWAY_ENVIRONMENT') == 'production':
        from waitress import serve
        serve(app, host="0.0.0.0", port=port)
    else:
        app.run(host='0.0.0.0', port=port)
