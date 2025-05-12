from flask import Flask, render_template, request, jsonify, send_file
import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from urllib.parse import urljoin
import io

app = Flask(__name__)

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = os.getenv('CHROME_BIN', '/usr/bin/google-chrome')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_loveable(url):
    driver = setup_driver()
    try:
        driver.get(url)
        time.sleep(2)  # Wait for dynamic content to load
        
        # Get the page source after JavaScript execution
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
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
    finally:
        driver.quit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        results = scrape_loveable(url)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    url = request.json.get('url')
    filename = request.json.get('filename')
    
    if not url or not filename:
        return jsonify({'error': 'Missing URL or filename'}), 400
    
    try:
        response = requests.get(url)
        # In Vercel, we'll return the file content instead of saving to desktop
        return send_file(
            io.BytesIO(response.content),
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# For local development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
