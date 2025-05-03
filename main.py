import time
import os
import requests
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import InvalidSessionIdException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
import zipfile
import io
import selenium

# === Auto-download profile if missing ===
def download_chrome_profile():
    url = "https://drive.google.com/uc?export=download&id=1CaSJ9G-doS1YsicJF6hSDRMuph_a-t5C"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to download chrome_profile.zip ({response.status_code})")
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        zip_ref.extractall("chrome_profile")
    print("✅ chrome_profile extracted successfully.")

if not os.path.exists("chrome_profile"):
    print("⬇️ Downloading chrome_profile from Google Drive...")
    download_chrome_profile()

# === Settings ===
GROUP_CHATS = ["Z27-ArgoVerseX community"] 
KEYWORDS    = [
    "A new trading opportunity is about to arise.",
    "Trading signal has been released, please execute trades as soon as possible.",
    "All traders, please return to the trading page now and close your positions.",
    "Please note that there are trading opportunities in the crypto contract market. ",
    "Please trade according to the currency name below to avoid unnecessary losses.",
    "All positions will be closed with profit. ",
    "yo"
]

# ✅ Your Telegram credentials (hardcoded)
TELEGRAM_TOKEN   = "8128554938:AAGc62mmSimQccCpefoHEibop87qMKkrx4c"
TELEGRAM_CHAT_ID = "7889873555"

def notify_telegram(group, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"🚨 *Keyword Alert in {group}*\n\n```{message}```",
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ Telegram failed ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"⚠️ Telegram error: {e}")

def start_driver(headless=True):
    options = Options()
    chrome_profile_path = os.path.join(os.path.dirname(__file__), 'chrome_profile')
    options.add_argument(f"--user-data-dir={chrome_profile_path}")
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Retry logic for profile lock
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        except selenium.common.exceptions.SessionNotCreatedException as e:
            print(f"⚠️ Chrome failed to start due to profile lock. Attempt {attempt+1} of {max_attempts}")
            time.sleep(10)
        except Exception as e:
            print(f"⚠️ Unexpected error when starting Chrome: {type(e).__name__}: {e}")
            raise e
    raise Exception("❌ Could not start Chrome after multiple attempts.")

def open_group_chat(driver, group):
    search_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='3']"))
    )
    search_box.click()
    time.sleep(1)
    search_box.send_keys(group)
    time.sleep(2)
    search_box.click()
    search_box.send_keys(Keys.CONTROL, 'a')
    search_box.send_keys(Keys.BACKSPACE)
    time.sleep(0.5)
    search_box.send_keys(group)

    chat = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, f"//span[@title='{group}']"))
    )
    chat.click()
    time.sleep(2)

    try:
        scrollbar_thumb = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, "div[aria-label='Message list'] ~ div div[role='button']"
            ))
        )
        actions = ActionChains(driver)
        for _ in range(10):
            actions.click_and_hold(scrollbar_thumb).move_by_offset(0, -100).release().perform()
            time.sleep(1)
    except Exception as e:
        print(f"⚠️ Scroll failed: {type(e).__name__}: {e}")

def check_group(driver, group):
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='textbox']"))
    )
    spans = driver.find_elements(
        By.XPATH,
        "//div[contains(@class,'message-in') or contains(@class,'message-out')]//span[@dir='ltr']"
    )
    print(f"[DEBUG] Found {len(spans)} message spans in '{group}'")

    recent_texts = [s.text for s in spans[-20:]]

    for text in recent_texts:
        for kw in KEYWORDS:
            if text.strip() == kw.strip():
                print(f"✅ Exact match in '{group}': '{text}'")
                notify_telegram(group, text)
                return

def monitor_whatsapp():
    driver = start_driver(headless=False)
    driver.get("https://web.whatsapp.com")
    time.sleep(15)

    while True:
        for group in GROUP_CHATS:
            try:
                open_group_chat(driver, group)
                check_group(driver, group)
            except InvalidSessionIdException:
                print("⚠️ Session died; restarting browser…")
                driver.quit()
                driver = start_driver(headless=False)
                driver.get("https://web.whatsapp.com")
                time.sleep(15)
            except Exception as e:
                print(f"⚠️ Unhandled error in '{group}': {type(e).__name__}: {e}")
        print("🔁 Waiting 60 seconds…")
        time.sleep(60)

if __name__ == "__main__":
    monitor_whatsapp()
