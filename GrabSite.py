import os
import re
import time
import ctypes
import threading
from colorama import init, Fore, Style
from getpass import getpass
import shutil
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from requests import Session
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from datetime import datetime
import requests

# Initialize colorama
init(autoreset=True)

# Define constants and globals
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
]
TARGET_EXTENSIONS = ['.js', '.css', '.gif', '.png', '.jpg', '.jpeg', '.svg', '.webp', '.woff', '.woff2', '.ttf', '.eot']
RETRY_LIMIT = 5
num_threads = 256  # Increased number of threads for faster downloads
start_time = None

# Initialize globals
download_queue = []
stop_event = threading.Event()
session = Session()

# Function to sanitize filenames
def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

# Clear the console screen
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Center the text in the console
def center_text(text, width=None):
    lines = text.split('\n')
    if width is None:
        width = shutil.get_terminal_size().columns
    centered_lines = [(line.center(width) + '\n') for line in lines]
    return ''.join(centered_lines)

# Function to apply a gradient to text (for general use)
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
            gradient_line += f'\033[38;2;{r};{g};{b}m{char}'
        gradient_lines.append(gradient_line + Style.RESET_ALL)
    return '\n'.join(gradient_lines)

# Function to apply a gradient to the username
def gradient_username(username, rank):
    if rank == "Founder":
        start_rgb = (255, 0, 0)  # Red gradient for Founder
        end_rgb = (255, 0, 0)
    elif rank == "Admin":
        start_rgb = (128, 0, 128)  # Purple gradient for Admin
        end_rgb = (186, 85, 211)
    else:
        start_rgb = (0, 255, 0)  # Green gradient for User
        end_rgb = (0, 255, 0)

    gradient_text = ''
    username_length = len(username)
    for i, char in enumerate(username):
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * (i / username_length))
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * (i / username_length))
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * (i / username_length))
        gradient_text += f'\033[38;2;{r};{g};{b}m{char}'
    return gradient_text + Style.RESET_ALL

# Function to print the Fartbin ASCII art with the appropriate gradient
def print_fartbin_art(rank):
    if rank == "Founder":
        start_rgb = (255, 0, 0)  # Red gradient for Founder
        end_rgb = (255, 0, 0)
    elif rank == "Admin":
        start_rgb = (128, 0, 128)  # Purple gradient for Admin
        end_rgb = (186, 85, 211)
    else:
        start_rgb = (0, 255, 0)  # Green gradient for User
        end_rgb = (0, 255, 0)

    fartbin_art = '''
┌─┐┌─┐┬─┐┌┬┐┌┐ ┬┌┐┌
├┤ ├─┤├┬┘ │ ├┴┐││││
└  ┴ ┴┴└─ ┴ └─┘┴┘└┘
  made by @fartboy
  [/tracer]
    '''
    terminal_width = shutil.get_terminal_size().columns
    centered_fartbin_art = center_text(fartbin_art, terminal_width)
    gradient_fartbin_art = gradient_text(centered_fartbin_art, start_rgb, end_rgb)
    print(gradient_fartbin_art)

# Function to print the download ASCII art
def print_download_art(url, username):
    download_art = f'''
╔═╗╔╦╗╔╦╗╔═╗╔═╗╦╔═  ╔═╗╔═╗╔╗╔╔╦╗
╠═╣ ║  ║ ╠═╣║  ╠╩╗  ╚═╗║╣ ║║║ ║
╩ ╩ ╩  ╩ ╩ ╩╚═╝╩ ╩  ╚═╝╚═╝╝╚╝ ╩
╚═══════════╦═════════════════════════════╦═════════╝
╔════════════════╩═════════════════════════════╩════════════════╗
║ HOST:    [ {url} ]
║ TIME:    [ In Progress ]
║ REQUESTED BY: [ {username} ]
║ SENT ON: [ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ]
╠═══════════════════════════════════════════════════════════════
    '''
    terminal_width = shutil.get_terminal_size().columns
    centered_download_art = center_text(download_art, terminal_width)
    print(centered_download_art)

# Function to update the TIME field in download art
def update_download_art(url, username, status):
    download_art = f'''
╔═╗╔╦╗╔╦╗╔═╗╔═╗╦╔═  ╔═╗╔═╗╔╗╔╔╦╗
╠═╣ ║  ║ ╠═╣║  ╠╩╗  ╚═╗║╣ ║║║ ║
╩ ╩ ╩  ╩ ╩ ╩╚═╝╩ ╩  ╚═╝╚═╝╝╚╝ ╩
╚═══════════╦═════════════════════════════╦═════════╝
╔════════════════╩═════════════════════════════╩════════════════╗
║ HOST:    [ {url} ]
║ TIME:    [ {status} ]
║ REQUESTED BY: [ {username} ]
║ SENT ON: [ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ]
╠═══════════════════════════════════════════════════════════════
    '''
    terminal_width = shutil.get_terminal_size().columns
    centered_download_art = center_text(download_art, terminal_width)
    clear_screen()
    print(centered_download_art)

# Function to get the HWID
def get_hwid():
    serial_number = ctypes.create_unicode_buffer(1024)
    ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p("C:\\"), None, 0, None, None, None, None, 0
    )
    return serial_number.value

# Login function
def login():
    first_login = False
    if os.path.exists("Fartbin.license"):
        with open("Fartbin.license", "r") as f:
            saved_username, saved_password, saved_hwid = f.read().strip().split(',')
        username = input("Enter your username: ")
        if username == saved_username:
            password = getpass("Enter your password: ")
            if password == saved_password:
                hwid = get_hwid()
                if saved_hwid != hwid:
                    print("HWID mismatch. Access denied.")
                    exit()
                rank = "Founder" if username == "drips" else "Admin" if username in ["Toxic", "Toxic146"] else "User"
                return username, rank, first_login
            else:
                print("Incorrect password.")
                exit()
        else:
            print("Username not found.")
            exit()
    else:
        first_login = True
        username = input("Enter your username: ")
        password = getpass("Enter your password: ")
        hwid = get_hwid()
        with open("Fartbin.license", "w") as f:
            f.write(f"{username},{password},{hwid}")
        rank = "Founder" if username == "drips" else "Admin" if username in ["Toxic", "Toxic146"] else "User"
        return username, rank, first_login

# Display after login function
def display_after_login(username, rank):
    clear_screen()
    print_fartbin_art(rank)
    print(f"run 'help' for the commands\n")
    print(f"{gradient_username(username, rank)} ● Tracer X Fartbin ►►")

# Function to download the site
def download_site(url, download_folder, username, rank):
    global start_time
    clear_screen()
    print_download_art(url, username)
    start_time = time.time()
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
        page_source = driver.page_source
    except Exception as e:
        print(f"{Fore.RED}Failed to fetch {url}: {e}{Style.RESET_ALL}")
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
        download_queue.append((resource_url, resource_folder))
    print(f"{Fore.CYAN}Resources have been queued for download to {download_folder}{Style.RESET_ALL}")
    update_title()
    worker()
    update_download_art(url, username, "Done")
    time.sleep(1)
    clear_screen()
    display_after_login(username, rank)

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
        print(f"{Fore.GREEN}{datetime.now()} - {local_path}: Successfully Downloaded{Style.RESET_ALL}")
    except requests.exceptions.RequestException as e:
        if retry_count < RETRY_LIMIT:
            print(f"{Fore.YELLOW}{datetime.now()} - Retrying download for {local_path}: Attempt {retry_count + 1}{Style.RESET_ALL}")
            time.sleep(2)
            download_file(url, folder, retry_count + 1)
        else:
            print(f"{Fore.RED}{datetime.now()} - {local_path}: Failed to download ({e}){Style.RESET_ALL}")
    return local_path

def update_title():
    while not stop_event.is_set():
        elapsed_time = time.time() - start_time
        site_count = len([f for f in os.listdir(os.getcwd()) if os.path.isdir(f) and re.match(r'[a-z0-9.-]+\.[a-z]{2,}$', f)])
        title = f"/fartcord | D: {site_count} | {elapsed_time:.2f}s"
        print(f"\033]0;{title}\007", end='', flush=True)
        time.sleep(0.01)

def worker():
    while True:
        url, folder = download_queue.get()
        if url is None:
            break
        try:
            download_file(url, folder)
        except Exception as e:
            print(f"{Fore.RED}{datetime.now()} - Error downloading {url}: {e}{Style.RESET_ALL}")
        download_queue.task_done()

# Main function
def main():
    username, rank, first_login = login()
    display_after_login(username, rank)

    while True:
        command = input(f"{gradient_username(username, rank)} ● Tracer X Fartbin ►► ").strip().lower()
        clear_screen()
        if command == 'help':
            print_fartbin_art(rank)
            print("Available commands:")
            print("download  - Download a website")
            print("clear - Clear the screen")
        elif command == 'download':
            url = input("What site does one want to steal?: ").strip()
            if not url.startswith("http"):
                url = "https://" + url
            parsed_url = urlparse(url)
            download_folder = sanitize_filename(parsed_url.netloc)
            download_site(url, download_folder, username, rank)
        elif command == 'clear':
            display_after_login(username, rank)
        else:
            print("Invalid command. Please try again.")

if __name__ == "__main__":
    main()
