from flask import Flask, render_template, request, jsonify, send_file
import os
import requests
from bs4 import BeautifulSoup
import time
import json
from urllib.parse import urljoin
import io

app = Flask(__name__)

def scrape_loveable(url):
    try:
        # Add headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        # Get the page content with timeout
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract code blocks
        code_blocks = []
        for pre in soup.find_all('pre'):
            code = pre.get_text()
            if code.strip():
                code_blocks.append(code)
        
        # Extract file links
        file_links = []
        for a in soup.find_all('a'):
            href = a.get('href')
            if href and (href.endswith('.js') or href.endswith('.css') or href.endswith('.html')):
                full_url = urljoin(url, href)
                file_links.append({
                    'url': full_url,
                    'filename': href.split('/')[-1]
                })
        
        return {
            'code_blocks': code_blocks,
            'file_links': file_links
        }
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        raise
    except Exception as e:
        print(f"Error scraping: {str(e)}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        results = scrape_loveable(url)
        return jsonify(results)
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch URL: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/download', methods=['POST'])
def download():
    try:
        url = request.json.get('url')
        filename = request.json.get('filename')
        
        if not url or not filename:
            return jsonify({'error': 'Missing URL or filename'}), 400
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        return send_file(
            io.BytesIO(response.content),
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to download file: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# For local development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
