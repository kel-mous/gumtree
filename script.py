import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import requests
import re
import time
import json
import os

def compare_versions(local_version, github_version):
    """
    Compares two version strings in the format 'MAJOR.MINOR.PATCH'.
    
    Args:
        local_version (str): The local version of the script.
        github_version (str): The version from the GitHub repository.
        
    Returns:
        bool: True if the GitHub version is newer, False otherwise.
    """
    local_version_parts = list(map(int, local_version.split('.')))
    github_version_parts = list(map(int, github_version.split('.')))
    
    # Compare each part of the version: MAJOR, MINOR, PATCH
    for lv, gv in zip(local_version_parts, github_version_parts):
        if gv > lv:
            return True
        elif gv < lv:
            return False
    return False  # Versions are equal

def check_for_update(local_version, github_version_url):
    """
    Checks for updates by comparing the local version with the version hosted on GitHub.
    If an update is available, it notifies the user and provides a link to the repository.
    
    Args:
        local_version (str): The local version of the script (e.g., '1.0.0').
        github_version_url (str): The raw URL to the version information file (JSON) hosted on GitHub.
        
    Returns:
        None
    """
    # Generate a timestamp query string to force GitHub to serve the latest version
    timestamp_url = f"{github_version_url}?timestamp={int(time.time())}"

    # Derive the repository URL from the raw GitHub file URL (without file path)
    repo_url = github_version_url.replace("raw.githubusercontent.com", "github.com")
    repo_url = repo_url.rsplit("/", 1)[0]  # Remove the version.json part to get the repo URL
    
    # Ensure we are removing the `/main` branch name if present
    if repo_url.endswith("/main"):
        repo_url = repo_url.rsplit("/main", 1)[0]

    try:
        # Fetch the version information from the provided GitHub URL
        response = requests.get(timestamp_url)
        response.raise_for_status()  # Ensure we got a valid response (200 OK)

        # Parse the JSON response to extract the version from GitHub
        github_version = response.json()
        github_version_str = github_version.get("version")

        # Compare the versions (e.g., '1.0.0' > '0.9.9')
        if compare_versions(local_version, github_version_str):
            print("A new version is available! Please update your script.")
            print(f"Visit the GitHub repository to check out the latest version: {repo_url}")
            to_continue = input('do you want to continue anyway? (Yes/no): ')
            if to_continue == 'no':
                exit(0)
            if to_continue == 'Yes' or to_continue == 'yes':
                print('continuing the execution...')
            else:
                print('entered something else, defaults to continue execution...')
        else:
            print("Your script is up to date!")

    except requests.exceptions.RequestException as e:
        print(f"Error checking for updates: {e}")

def is_newer_than_three_days(date_str):
    """Checks if a given date string (like 'Just now', '3 mins ago', '8 hours ago', or '2 days ago') is within the last 3 days."""
    now = datetime.now()

    # Special case for 'Just now'
    if date_str.lower() == 'just now':
        return True

    # Regex pattern to match 'X mins ago', 'X hour(s) ago', or 'X day(s) ago'
    minute_match = re.match(r"(\d+)\s*min[s]?\s*ago", date_str, re.IGNORECASE)
    hour_match = re.match(r"(\d+)\s*hour[s]?\s*ago", date_str, re.IGNORECASE)
    day_match = re.match(r"(\d+)\s*day[s]?\s*ago", date_str, re.IGNORECASE)

    if minute_match:
        number = int(minute_match.group(1))
        time_diff = timedelta(minutes=number)
        return (now - time_diff) >= (now - timedelta(days=3))

    if hour_match:
        number = int(hour_match.group(1))
        time_diff = timedelta(hours=number)
        return (now - time_diff) >= (now - timedelta(days=3))

    if day_match:
        number = int(day_match.group(1))
        time_diff = timedelta(days=number)
        return (now - time_diff) >= (now - timedelta(days=3))

    return False

def extract_location(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    if 'center' in query_params:
        location = query_params['center'][0].split(',')
        return float(location[0]), float(location[1])
    return None

def initialize_json_file(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            json.dump({}, file)
        print(f"{file_path} created as an empty file.")

def load_json(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        print(f"Error reading {file_path}. Resetting file.")
        initialize_json_file(file_path)
        return {}

# Define the local version (adjust this to match your script's current version)
local_version = "1.0.0"

# GitHub URL for the version information (raw URL to the JSON file)
github_version_url = "https://raw.githubusercontent.com/kel-mous/gumtree/main/version.json"

# Call the function to check for updates
check_for_update(local_version, github_version_url)

# Initialize URLs and file paths
url = 'https://www.gumtree.com/search?search_location=uk&search_category=property-to-rent&sort=date&page='
output_file = 'temp.json'
closes_file = 'output.json'

initialize_json_file(output_file)
initialize_json_file(closes_file)

# Start the web driver
options = uc.ChromeOptions()
driver = uc.Chrome(options=options)
driver.maximize_window()

# Load existing data
data = load_json(output_file)
everything = load_json(closes_file)

# Loop through the pages to collect URLs
page = 1
i = len(data) + 1

if i == 1:
    # this means that only if temp is empty that we will refill it again, this file contains the links from searching on all the listings
    try:
        while page < 51:
            driver.get(url + str(page))
            time.sleep(0.5)  # Consider using WebDriverWait instead of sleep for better performance

            posts = driver.find_elements(By.CSS_SELECTOR, '[data-q="search-result-anchor"]')
            treated = 0
            
            for post in posts:
                try:
                    href = post.get_attribute('href')
                    if 'Featured' in post.text:
                        print('Featured')
                        continue

                    date_element = post.find_element(By.CSS_SELECTOR, '[data-q="tile-datePosted"]')
                    date_text = date_element.text.strip()
                    
                    print(f'Listing URL: {href}')
                    print(f'Date Posted: {date_text}')

                    if is_newer_than_three_days(date_text):
                        data[f'listing{i}'] = {'url': href, 'found': int(time.time() * 1000)}
                        i += 1
                    
                    treated += 1
                except Exception as e:
                    print(f"Error processing post: {e}")
            
            print(f'Page {page} - Processed {treated} listings')
            page += 1

        # Save data to JSON file
        json_output = json.dumps(data, indent=4)
        with open(output_file, 'w') as file:
            file.write(json_output)

    except Exception as e:
        print(f"Unexpected error: {e}")

# Now process each listing
listings = data.values()
j = len(everything) + 1

for listing in listings:
    url = listing['url']
    if url in everything:
        print(f'Skipping {url}, already processed.')
        continue
    
    driver.get(url)
    try:
        WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
        print("Accepted cookies.")
    except:
        pass
    
    print(f"Processing: {url}")
    item = {'website_id': f'gumtree_{url.split("/")[-1]}', 'link': url, 'found': listing.get('found', None),
            'garden': None, 'pets': None, 'balcony': None, 'floorspace': None, 'price_per_m²': None,
            'phone': None, 'furnished': None, 'bathrooms': 1, 'img': []}
    
    try:
        item['title'] = driver.find_element(By.CSS_SELECTOR, '[data-q="vip-title"]').text
    except:
        print("Title not found, skipping.")
        continue
    
    try:
        item['area'] = driver.find_element(By.XPATH, '//*[@id="content"]/div[1]/div/main/div[3]/div[1]/div/div/span[1]/h4').text
    except:
        item['area'] = None
    
    try:
        item['description'] = driver.find_element(By.CSS_SELECTOR, '[itemprop="description"]').text
    except:
        item['description'] = ""
    
    try:
        item['bedrooms'] = int(driver.find_element(By.CSS_SELECTOR, '[data-q="Number of bedrooms-value"]').text)
    except:
        item['bedrooms'] = None
    
    try:
        price_text = driver.find_element(By.CSS_SELECTOR, '[data-q="ad-price"]').text
        match = re.search(r'£([\d,]+)(?:\.\d{2})?', price_text)  # Capture only the main number
        item['price'] = int(match.group(1).replace(',', '')) if match else None
    except:
        item['price'] = None
    
    try:
        images = driver.find_element(By.CSS_SELECTOR, '[data-q="image-carousel"]').find_elements(By.TAG_NAME, 'img')
        next_button = driver.find_element(By.CSS_SELECTOR, '[data-q="carouselNext"]')
        
        for img in images:
            item['img'].append(img.get_attribute('src'))
            try:
                next_button.click()
                time.sleep(0.05)
            except:
                break
    except:
        item['img'] = []
    
    try:
        location_link = driver.find_element(By.CSS_SELECTOR, '[title="Map"]').get_attribute('src')
        item['location'] = {'latitude': extract_location(location_link)}
    except:
        item['location'] = None
    
    everything[f'listing{j}'] = item
    j += 1
    
    with open(closes_file, 'w') as file:
        json.dump(everything, file, indent=4, ensure_ascii=False)
    
    time.sleep(0.5)

driver.quit()

if os.path.exists(output_file):
    os.remove(output_file)
    print("temp.json deleted since it's not needed anymore")