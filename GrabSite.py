import requests
from bs4 import BeautifulSoup
import os
import re
import logging
import time
import random
from datetime import datetime
from urllib.parse import urlparse, urljoin
from threading import Thread, Event
from queue import Queue
import base64
import shutil
import ctypes
from colorama import Fore, Style, init
from getpass import getpass
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import subprocess
import git

init(autoreset=True)

logging.basicConfig(level=logging.INFO, format='%(message)s')

RETRY_LIMIT = 5
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
]
TARGET_EXTENSIONS = ['.js', '.css', '.gif', '.png', '.jpg', '.jpeg', '.svg', '.webp', '.woff', '.woff2', '.ttf', '.eot']
CAPTCHA_INDICATORS = [
    'Bot Verification', 'recaptcha-container', 'g-recaptcha', 'cf-challenge',
    'Please complete the security check to access', 'Checking your browser before accessing',
    'document.getElementById(\'challenge-form\')', 'Turnstile verification', 'data-sitekey'
]

COMMON_FOLDERS = ['assets', 'static', 'js', 'css', 'images', 'img', 'media', 'files', 'scripts', 'styles']

session = requests.Session()
session.headers.update({
    "User-Agent": random.choice(USER_AGENTS),
    "Referer": "https://www.google.com"
})
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session.mount('http://', adapter)
session.mount('https://', adapter)

download_queue = Queue()
start_time = None
num_threads = 64  # Increased number of threads for faster downloads

whitelist = []
blacklist = []

def center_text(text, width):
    lines = text.split('\n')
    centered_lines = [(line.center(width) + '\n') for line in lines]
    return ''.join(centered_lines)

def rgb_to_ansi(r, g, b):
    return f'\033[38;2;{r};{g};{b}m'

def gradient_text(text, start_rgb, end_rgb):
    lines = text.split('\n')
    gradient_lines = []
    for i, line in enumerate(lines):
        line_length = len(line)
        gradient_line = ''
        for j, char in enumerate(line):
            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * (j / line_length))
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * (j / line_length))
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * (j / line_length))
            gradient_line += rgb_to_ansi(r, g, b) + char
        gradient_lines.append(gradient_line + Style.RESET_ALL)
    return '\n'.join(gradient_lines)

def print_fartbin_art():
    start_rgb = (128, 0, 128)
    end_rgb = (186, 85, 211)
    fartbin_art = '''
┌─┐┌─┐┬─┐┌┬┐┌┐ ┬┌┐┌
├┤ ├─┤├┬┘ │ ├┴┐││││
└  ┴ ┴┴└─ ┴ └─┘┴┘└┘
'''
    terminal_width = shutil.get_terminal_size().columns
    centered_fartbin_art = center_text(fartbin_art, terminal_width)
    gradient_fartbin_art = gradient_text(centered_fartbin_art, start_rgb, end_rgb)
    return gradient_fartbin_art

def detect_captcha(html_content):
    return any(indicator in html_content for indicator in CAPTCHA_INDICATORS)

def wait_for_captcha():
    input("CAPTCHA detected. Please solve the CAPTCHA in your browser and press Enter to continue...")

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def download_file(url, folder, retry_count=0):
    parsed_url = urlparse(url)
    local_filename = os.path.basename(parsed_url.path)
    if not local_filename:
        local_filename = 'index.html'
    local_folder = os.path.join(folder, os.path.dirname(parsed_url.path.lstrip('/')))
    local_path = os.path.join(local_folder, sanitize_filename(local_filename))
    if not os.path.exists(local_folder):
        os.makedirs(local_folder)
    try:
        with session.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logging.info(f"{Fore.GREEN}{datetime.now()} - {local_path}: Successfully Downloaded{Style.RESET_ALL}")
    except requests.exceptions.RequestException as e:
        if retry_count < RETRY_LIMIT:
            logging.warning(f"{Fore.YELLOW}{datetime.now()} - Retrying download for {local_path}: Attempt {retry_count + 1}{Style.RESET_ALL}")
            time.sleep(2)
            download_file(url, folder, retry_count + 1)
        else:
            logging.error(f"{Fore.RED}{datetime.now()} - {local_path}: Failed to download ({e}){Style.RESET_ALL}")
    return local_path

def worker():
    while True:
        url, folder = download_queue.get()
        if url is None:
            break
        try:
            download_file(url, folder)
        except Exception as e:
            logging.error(f"{Fore.RED}{datetime.now()} - Error downloading {url}: {e}{Style.RESET_ALL}")
        download_queue.task_done()

def update_title(stop_event):
    global start_time
    while not stop_event.is_set():
        elapsed_time = time.time() - start_time if start_time else 0
        site_count = len([f for f in os.listdir(os.getcwd()) if os.path.isdir(f) and re.match(r'[a-z0-9.-]+\.[a-z]{2,}$', f)])
        title = f"/fartcord | D: {site_count} | {elapsed_time:.2f}s"
        print(f"\033]0;{title}\007", end='', flush=True)
        time.sleep(0.01)

def get_website_source(url, download_folder):
    global start_time
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
    options = Options()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-devtools')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=' + random.choice(USER_AGENTS))
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.get(url)
        start_time = time.time()
        html_content = driver.page_source
        if detect_captcha(html_content):
            options.headless = False
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.get(url)
            wait_for_captcha()
            html_content = driver.page_source
        cookies = driver.get_cookies()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
        page_source = driver.page_source
    except Exception as e:
        logging.error(f"{Fore.RED}Failed to fetch {url}: {e}{Style.RESET_ALL}")
        if driver:
            driver.quit()
        return
    finally:
        if driver:
            driver.quit()
    soup = BeautifulSoup(page_source, 'html.parser')
    main_page_path = os.path.join(download_folder, 'index.html')
    with open(main_page_path, 'w', encoding='utf-8', errors='surrogateescape') as f:
        f.write(page_source)
    resources = set()
    for tag in soup.find_all(['script', 'link', 'img', 'a', 'source', 'iframe', 'video', 'audio']):
        src_attr = 'src' if tag.name in ['script', 'img', 'source', 'iframe', 'video', 'audio'] else 'href'
        resource_url = tag.get(src_attr)
        if resource_url and any(resource_url.endswith(ext) for ext in TARGET_EXTENSIONS):
            resources.add(resource_url)
    inline_scripts = soup.find_all('script')
    inline_styles = soup.find_all('style')
    inline_resources = re.findall(r'url\(["\']?(.*?)["\']?\)', str(inline_scripts + inline_styles))
    resources.update(inline_resources)
    for resource in resources:
        resource_url = urljoin(url, resource)
        resource_path = sanitize_filename(urlparse(resource_url).path.lstrip('/'))
        resource_folder = os.path.join(download_folder, os.path.dirname(resource_path))
        if not os.path.exists(resource_folder):
            os.makedirs(resource_folder, exist_ok=True)
        download_queue.put((resource_url, resource_folder))
    github_links = re.findall(r'https://github\.com/[A-Za-z0-9._%+-/]+', page_source)
    if github_links:
        with open(os.path.join(download_folder, 'github_repos.txt'), 'w', encoding='utf-8') as f:
            for link in github_links:
                f.write(link + '\n')
    logging.info(f"{Fore.CYAN}Resources have been queued for download to {download_folder}{Style.RESET_ALL}")

def is_obfuscated(content):
    patterns = [
        r'eval\((.*?)\)',
        r'function\s*\(.*?\)\s*\{.*?\}',
        r'\\x[0-9A-Fa-f]{2}',
        r'\\u[0-9A-Fa-f]{4}',
        r'([0-9a-fA-F]{2}\s*){8,}',
        r'base64',
        r'atob\(["\'].*?["\']\)',
        r'["\']\.join\(["\']',
        r'\["[a-z0-9]+"\]\s*\(.*?\)',
        r'unescape\(["\'].*?["\']\)'
    ]
    return any(re.search(pattern, content) for pattern in patterns)

def deobfuscate_js(content):
    original_content = content
    content = re.sub(r'eval\((.*?)\)', r'\1', content)
    content = re.sub(r'\\x([0-9A-Fa-f]{2})', lambda m: chr(int(m.group(1), 16)), content)
    content = re.sub(r'\\u([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), content)
    content = re.sub(r'([0-9a-fA-F]{2}\s*){8,}', lambda m: bytes.fromhex(m.group(0).replace(' ', '')).decode('utf-8', 'ignore'), content)
    content = re.sub(r'atob\(["\'](.*?)["\']\)', lambda m: decode_base64(m.group(1)), content)
    content = re.sub(r'["\']\.join\(["\']', '', content)
    content = re.sub(r'\["[a-z0-9]+"\]\s*\((.*?)\)', r'\1', content)
    content = re.sub(r'unescape\(["\'](.*?)["\']\)', lambda m: decode_unescape(m.group(1)), content)
    content = re.sub(r'\\([0-7]{1,3})', lambda m: chr(int(m.group(1), 8)), content)
    return content if content != original_content else None

def decode_base64(encoded_str):
    try:
        return base64.b64decode(encoded_str).decode('utf-8', errors='surrogateescape')
    except Exception as e:
        logging.error(f"Failed to decode base64 string: {e}")
        return encoded_str

def decode_unescape(encoded_str):
    try:
        return bytes(encoded_str, "utf-8").decode("unicode_escape", errors='surrogateescape')
    except Exception as e:
        logging.error(f"Failed to decode unescape string: {e}")
        return encoded_str

def scan_and_queue_file(file_path, base_url):
    with open(file_path, 'r', encoding='utf-8', errors='surrogateescape') as f:
        content = f.read()
    resource_urls = re.findall(r'url\(["\']?(.*?)["\']?\)', content)
    resource_urls += re.findall(r'src=["\'](.*?)["\']', content)
    resource_urls += re.findall(r'href=["\'](.*?)["\']', content)
    for resource_url in resource_urls:
        full_url = urljoin(base_url, resource_url)
        resource_path = sanitize_filename(urlparse(full_url).path.lstrip('/'))
        resource_folder = os.path.join(os.path.dirname(file_path), os.path.dirname(resource_path))
        if not os.path.exists(resource_folder):
            os.makedirs(resource_folder, exist_ok=True)
        if '://' not in full_url:
            full_url = urljoin(base_url, resource_url)
        download_queue.put((full_url, resource_folder))

def scan_common_folders(download_folder, base_url):
    for root, dirs, files in os.walk(download_folder):
        for dir_name in dirs:
            if dir_name.lower() in COMMON_FOLDERS:
                full_path = os.path.join(root, dir_name)
                for subdir, _, subfiles in os.walk(full_path):
                    for file in subfiles:
                        scan_and_queue_file(os.path.join(subdir, file), base_url)

def get_hwid():
    serial_number = ctypes.c_uint()
    ctypes.windll.kernel32.GetVolumeInformationW(
        "C:\\", None, 0, ctypes.byref(serial_number), None, None, None, 0
    )
    return str(serial_number.value)

def login():
    global first_login
    first_login = False
    if os.path.exists("Fartbin.license"):
        with open("Fartbin.license", "r") as f:
            try:
                saved_username, saved_password, saved_hwid = f.read().strip().split(',')
            except ValueError:
                saved_username, saved_password, saved_hwid = None, None, None
            if saved_hwid != get_hwid():
                print("HWID mismatch. Access denied.")
                exit()
    else:
        first_login = True
        with open("Fartbin.license", "w", encoding='utf-8', errors='surrogateescape') as f:
            username = input("Enter your username: ")
            if username in blacklist:
                print("Access denied.")
                exit()
            password = getpass("Enter your password: ")
            hwid = get_hwid()
            if username in ["drips", "dddrrriiipppsss"] and password == "234@":
                rank = "Founder"
            elif password == "1234@":
                rank = "Owner"
            else:
                print("Invalid credentials.")
                exit()
            f.write(f"{username},{password},{hwid}")
            return username, rank, first_login
    with open("Fartbin.license", "r", encoding='utf-8', errors='surrogateescape') as f:
        saved_username, saved_password, saved_hwid = f.read().strip().split(',')
    if saved_username in ["drips", "dddrrriiipppsss"]:
        rank = "Founder"
    elif saved_username in ["~$cars", "KKunx"]:
        rank = "Owner"
    else:
        rank = "User"
    if saved_hwid != get_hwid():
        print("HWID mismatch. Access denied.")
        exit()
    return saved_username, rank, first_login

def manage_whitelist():
    while True:
        print("Whitelist Management:")
        print("1. Add user")
        print("2. Remove user")
        print("3. View whitelist")
        print("4. Back to menu")
        option = input("Select an option: ")
        if option == '1':
            user_to_add = input("Enter username to whitelist: ")
            whitelist.append(user_to_add)
            print(f"{user_to_add} has been whitelisted.")
        elif option == '2':
            user_to_remove = input("Enter username to remove from whitelist: ")
            if user_to_remove in whitelist:
                whitelist.remove(user_to_remove)
                print(f"{user_to_remove} has been removed from the whitelist.")
            else:
                print(f"{user_to_remove} is not in the whitelist.")
        elif option == '3':
            print("Whitelisted users:")
            for user in whitelist:
                print(user)
        elif option == '4':
            break
        else:
            print("Invalid option. Please try again.")

def manage_blacklist():
    while True:
        print("Blacklist Management:")
        print("1. Add user")
        print("2. Remove user")
        print("3. View blacklist")
        print("4. Back to menu")
        option = input("Select an option: ")
        if option == '1':
            user_to_add = input("Enter username to blacklist: ")
            blacklist.append(user_to_add)
            print(f"{user_to_add} has been blacklisted.")
        elif option == '2':
            user_to_remove = input("Enter username to remove from blacklist: ")
            if user_to_remove in blacklist:
                blacklist.remove(user_to_remove)
                print(f"{user_to_remove} has been removed from the blacklist.")
            else:
                print(f"{user_to_remove} is not in the blacklist.")
        elif option == '3':
            print("Blacklisted users:")
            for user in blacklist:
                print(user)
        elif option == '4':
            break
        else:
            print("Invalid option. Please try again.")

def check_for_updates():
    repo_url = "https://github.com/yourusername/yourrepo.git"
    local_repo_path = os.getcwd()

    try:
        repo = git.Repo(local_repo_path)
        origin = repo.remotes.origin
        origin.fetch()

        local_commit = repo.head.commit
        remote_commit = repo.heads.master.commit

        if local_commit != remote_commit:
            logging.info("New update available. Running update script.")
            subprocess.run(["python", "update.py"])
    except Exception as e:
        logging.error(f"Failed to check for updates: {e}")

def main_menu(username, rank):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(print_fartbin_art())
    print(f"Welcome{' back' if not first_login else ''}, {'\033[38;2;255;215;0m\033[5m' + username + '\033[0m' if rank == 'Founder' else '\033[38;2;255;0;0m' + username + '\033[0m' if rank == 'Owner' else username}")
    if rank in ["Founder", "Owner"]:
        while True:
            print("What would you like to do?")
            print("\033[32m1. Download site\033[0m")
            print("\033[32m2. Whitelist\033[0m")
            print("\033[31m3. Blacklist\033[0m")
            option = input("Select an option: ")
            if option == '1':
                break
            elif option == '2':
                manage_whitelist()
            elif option == '3':
                manage_blacklist()
            else:
                print("Invalid option. Please try again.")

def main():
    global start_time
    check_for_updates()
    os.system('cls' if os.name == 'nt' else 'clear')
    print(print_fartbin_art())
    username, rank, first_login = login()
    main_menu(username, rank)
    url = input("Enter the URL of the website: ")
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url
    parsed_url = urlparse(url)
    domain_name = parsed_url.netloc
    download_folder = os.path.join(os.getcwd(), domain_name)
    os.system('cls' if os.name == 'nt' else 'clear')
    print(print_fartbin_art())
    stop_event = Event()
    start_time = time.time()
    title_thread = Thread(target=update_title, args=(stop_event,))
    title_thread.start()
    get_website_source(url, download_folder)
    for root, _, files in os.walk(download_folder):
        for file in files:
            file_path = os.path.join(root, file)
            if file.endswith('.js'):
                with open(file_path, 'r', encoding='utf-8', errors='surrogateescape') as f:
                    js_content = f.read()
                if is_obfuscated(js_content):
                    deobfuscated_content = deobfuscate_js(js_content)
                    if deobfuscated_content:
                        with open(file_path, 'w', encoding='utf-8', errors='surrogateescape') as f:
                            f.write(deobfuscated_content)
                        logging.info(f"{Fore.GREEN}{datetime.now()} - Deobfuscated JavaScript content and saved to {file_path}{Style.RESET_ALL}")
            scan_and_queue_file(file_path, url)
    scan_common_folders(download_folder, url)
    threads = []
    for i in range(num_threads):
        t = Thread(target=worker)
        t.start()
        threads.append(t)
    download_queue.join()
    for i in range(num_threads):
        download_queue.put((None, None))
    for t in threads:
        t.join()
    stop_event.set()
    title_thread.join()
    end_time = time.time()
    elapsed_time = end_time - start_time
    site_count = len([f for f in os.listdir(os.getcwd()) if os.path.isdir(f) and re.match(r'[a-z0-9.-]+\.[a-z]{2,}$', f)])
    print(f"\033]0;/fartcord | D: {site_count} | {elapsed_time:.2f}s\007", end='', flush=True)
    logging.info(f"{Fore.CYAN}Completed downloading all resources for {url}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
