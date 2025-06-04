import os
import tempfile
import subprocess
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
YT_DLP = 'yt-dlp'  # Will use system-installed version
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB limit for responses

@app.route('/health')
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({"status": "healthy", "service": "youtube-subtitle-fetcher"})

@app.route('/api/subtitles', methods=['GET'])
def get_subtitles():
    """API endpoint to fetch subtitles"""
    # Input validation
    video_url = request.args.get('url')
    language = request.args.get('lang', 'en')
    
    if not video_url:
        logger.error("Missing URL parameter")
        return jsonify({'error': 'YouTube URL is required'}), 400
    
    if 'youtube.com/watch?v=' not in video_url and 'youtu.be/' not in video_url:
        logger.error(f"Invalid YouTube URL: {video_url}")
        return jsonify({'error': 'Invalid YouTube URL format'}), 400

    logger.info(f"Processing request for URL: {video_url}, language: {language}")
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Prepare command
            cmd = [
                YT_DLP,
                '--skip-download',
                '--write-subs',
                '--write-auto-subs',
                '--sub-lang', language,
                '--sub-format', 'vtt',
                '--convert-subs', 'srt',
                '--output', f'{tmp_dir}/subtitle',
                '--no-warnings',  # Reduce log noise
                video_url
            ]
            
            logger.info(f"Executing command: {' '.join(cmd)}")
            
            # Run yt-dlp
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            # Check for errors
            if result.returncode != 0:
                error_msg = result.stderr or "Unknown yt-dlp error"
                logger.error(f"yt-dlp failed with code {result.returncode}: {error_msg}")
                return jsonify({
                    'error': f"Subtitle extraction failed: {error_msg}",
                    'yt-dlp_output': result.stdout
                }), 500
            
            # Find subtitle file
            subtitle_file = None
            for ext in ['.srt', '.vtt']:
                possible_file = f"{tmp_dir}/subtitle.{language}{ext}"
                if os.path.exists(possible_file):
                    subtitle_file = possible_file
                    break
            
            if not subtitle_file:
                logger.error("No subtitle file found")
                return jsonify({
                    'error': 'No subtitles found for this language',
                    'available_files': str(os.listdir(tmp_dir))
                }), 404
            
            # Read and return subtitles
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                if len(content) > MAX_CONTENT_LENGTH:
                    content = content[:MAX_CONTENT_LENGTH] + "\n... (truncated)"
                
                logger.info(f"Successfully fetched subtitles ({len(content)} chars)")
                return jsonify({
                    'subtitles': content,
                    'language': language,
                    'source_url': video_url
                })
                
    except subprocess.TimeoutExpired:
        logger.error("yt-dlp timed out after 30 seconds")
        return jsonify({'error': 'Subtitle extraction timed out'}), 504
    except Exception as e:
        logger.exception("Unexpected error occurred")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port)
