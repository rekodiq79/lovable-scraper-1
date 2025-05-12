from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import os
import requests
from bs4 import BeautifulSoup
import time
import json
from urllib.parse import urljoin, urlparse
import io
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import zipfile
import uuid
import tempfile

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                             'favicon.ico', mimetype='image/vnd.microsoft.icon')

def setup_driver():
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("Chrome WebDriver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {str(e)}")
        raise

def login_to_loveable(driver, email, password):
    try:
        logger.info("Attempting to log in to lovable.dev")
        driver.get("https://lovable.dev/login")
        
        # Wait for email input
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        email_input.send_keys(email)
        
        # Find and click password input
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys(password)
        
        # Find and click login button
        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in')]")
        login_button.click()
        
        # Wait for login to complete
        WebDriverWait(driver, 10).until(
            EC.url_changes("https://lovable.dev/login")
        )
        
        logger.info("Successfully logged in to lovable.dev")
        return True
    except Exception as e:
        logger.error(f"Failed to log in: {str(e)}")
        return False

def scrape_loveable(url, email=None, password=None):
    if not is_valid_url(url):
        raise ValueError("Invalid URL format")
    
    driver = None
    try:
        logger.info(f"Starting to scrape URL: {url}")
        driver = setup_driver()
        
        # Login if credentials are provided
        if email and password:
            if not login_to_loveable(driver, email, password):
                raise ValueError("Failed to authenticate with lovable.dev")
        
        # Navigate to the project URL
        driver.get(url)
        
        # Wait for the content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "pre"))
        )
        
        # Get all code blocks
        code_blocks = []
        pre_elements = driver.find_elements(By.TAG_NAME, "pre")
        for pre in pre_elements:
            code = pre.text
            if code.strip():
                code_blocks.append(code)
        
        # Get all file links
        file_links = []
        a_elements = driver.find_elements(By.TAG_NAME, "a")
        for a in a_elements:
            href = a.get_attribute('href')
            if href and (href.endswith('.js') or href.endswith('.css') or href.endswith('.html')):
                file_links.append({
                    'url': href,
                    'filename': href.split('/')[-1]
                })
        
        if not code_blocks and not file_links:
            raise ValueError("No code blocks or file links found on the page")
        
        logger.info(f"Successfully scraped {len(code_blocks)} code blocks and {len(file_links)} file links")
        return {
            'code_blocks': code_blocks,
            'file_links': file_links
        }
    except Exception as e:
        logger.error(f"Error scraping: {str(e)}")
        raise ValueError(f"Failed to scrape the page: {str(e)}")
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Chrome WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing Chrome WebDriver: {str(e)}")

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

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
            logger.error("Request is not JSON")
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.get_json()
        logger.info(f"Received request data: {data}")
        
        url = data.get('url')
        email = data.get('email')
        password = data.get('password')
        
        if not url:
            logger.error("No URL provided in request")
            return jsonify({'error': 'No URL provided'}), 400
            
        if not is_valid_url(url):
            logger.error(f"Invalid URL format: {url}")
            return jsonify({'error': 'Invalid URL format'}), 400
        
        # Log authentication attempt
        if email and password:
            logger.info(f"Attempting to authenticate with email: {email}")
        else:
            logger.info("No authentication credentials provided")
        
        results = scrape_loveable(url, email, password)
        return jsonify(results)
    except ValueError as e:
        logger.error(f"ValueError in analyze endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in analyze endpoint: {str(e)}")
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
        
        logger.info(f"Starting download for URL: {url}, filename: {filename}")
        
        # Create a temporary directory for the files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download the file
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
                logger.error("Download request timed out")
                return jsonify({'error': 'Download request timed out'}), 408
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error during download: {str(e)}")
                return jsonify({'error': f'Failed to download file. Status code: {e.response.status_code}'}), 500
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error during download: {str(e)}")
                return jsonify({'error': f'Failed to download file: {str(e)}'}), 500
            
            # Save the file
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Create a zip file
            zip_path = os.path.join(temp_dir, f"{filename}.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                zipf.write(file_path, arcname=filename)
            
            # Read the zip file
            with open(zip_path, 'rb') as f:
                zip_content = f.read()
            
            logger.info(f"Successfully created zip file for {filename}")
            return send_file(
                io.BytesIO(zip_content),
                mimetype='application/zip',
                as_attachment=True,
                download_name=f"{filename}.zip"
            )
    except Exception as e:
        logger.error(f"Error in download endpoint: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

# For local development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
