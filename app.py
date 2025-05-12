from flask import Flask, render_template, request, jsonify, send_file
import os
import requests
from bs4 import BeautifulSoup
import time
import json
from urllib.parse import urljoin, urlparse
import io
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def scrape_loveable(url):
    if not is_valid_url(url):
        raise ValueError("Invalid URL format")
        
    try:
        # Add headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        # Get the page content with timeout
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching URL: {url}")
            raise ValueError("Request timed out. Please try again.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error while fetching URL: {url}, status code: {e.response.status_code}")
            raise ValueError(f"Failed to fetch URL. Status code: {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while fetching URL: {url}, error: {str(e)}")
            raise ValueError(f"Failed to fetch URL: {str(e)}")
        
        # Parse the HTML
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logger.error(f"Error parsing HTML for URL: {url}, error: {str(e)}")
            raise ValueError("Failed to parse webpage content")
        
        # Extract code blocks
        code_blocks = []
        try:
            for pre in soup.find_all('pre'):
                code = pre.get_text()
                if code.strip():
                    code_blocks.append(code)
        except Exception as e:
            logger.error(f"Error extracting code blocks: {str(e)}")
            # Continue even if code block extraction fails
        
        # Extract file links
        file_links = []
        try:
            for a in soup.find_all('a'):
                href = a.get('href')
                if href and (href.endswith('.js') or href.endswith('.css') or href.endswith('.html')):
                    full_url = urljoin(url, href)
                    file_links.append({
                        'url': full_url,
                        'filename': href.split('/')[-1]
                    })
        except Exception as e:
            logger.error(f"Error extracting file links: {str(e)}")
            # Continue even if file link extraction fails
        
        if not code_blocks and not file_links:
            raise ValueError("No code blocks or file links found on the page")
            
        return {
            'code_blocks': code_blocks,
            'file_links': file_links
        }
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while scraping: {str(e)}")
        raise ValueError(f"An unexpected error occurred: {str(e)}")

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index page: {str(e)}")
        return jsonify({'error': 'Failed to load the application'}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        url = request.json.get('url')
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
            
        if not is_valid_url(url):
            return jsonify({'error': 'Invalid URL format'}), 400
        
        results = scrape_loveable(url)
        return jsonify(results)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in analyze endpoint: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/download', methods=['POST'])
def download():
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        url = request.json.get('url')
        filename = request.json.get('filename')
        
        if not url or not filename:
            return jsonify({'error': 'Missing URL or filename'}), 400
            
        if not is_valid_url(url):
            return jsonify({'error': 'Invalid URL format'}), 400
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            return jsonify({'error': 'Download request timed out'}), 408
        except requests.exceptions.HTTPError as e:
            return jsonify({'error': f'Failed to download file. Status code: {e.response.status_code}'}), 500
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to download file: {str(e)}'}), 500
        
        return send_file(
            io.BytesIO(response.content),
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Error in download endpoint: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

# For local development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
