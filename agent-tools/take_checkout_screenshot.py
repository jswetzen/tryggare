"""
Take the checkout screenshot only (rate limit reset).
"""
import time
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

FRONTEND_URL = "http://localhost:5173"
SCREENSHOTS_DIR = "/workspace/check-ins/docs/screenshots"
USERNAME = "admin"
PASSWORD = "admin123"


def make_driver(width=1280, height=800):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--window-size={width},{height}")
    chrome_options.add_argument("--lang=en-US")
    chrome_options.add_argument("--force-device-scale-factor=1")

    prefs = {"intl.accept_languages": "en-US,en"}
    chrome_options.add_experimental_option("prefs", prefs)

    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_window_size(width, height)
    return driver


def wait_for(driver, by, value, timeout=15):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


print("\n=== Screenshot 3: checkout-desktop.png (1280x800) ===")
driver = make_driver(1280, 800)
try:
    print("  Navigating to login page...")
    driver.get(f"{FRONTEND_URL}/login")
    time.sleep(2)

    print("  Filling in credentials...")
    username_field = wait_for(driver, By.ID, "username", timeout=10)
    password_field = driver.find_element(By.ID, "password")

    username_field.clear()
    username_field.send_keys(USERNAME)
    password_field.clear()
    password_field.send_keys(PASSWORD)

    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_btn.click()

    # Wait for redirect to /checkin
    try:
        WebDriverWait(driver, 15).until(EC.url_contains("/checkin"))
        print(f"  Login successful. Current URL: {driver.current_url}")
    except Exception as e:
        print(f"  Login issue: {e}. URL: {driver.current_url}")
        driver.save_screenshot(f"{SCREENSHOTS_DIR}/checkout-login-debug.png")
        print("  Debug screenshot saved")

    # Navigate to /checkout
    print("  Navigating to /checkout...")
    driver.get(f"{FRONTEND_URL}/checkout")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "main"))
        )
    except Exception:
        pass
    time.sleep(3)

    print(f"  URL: {driver.current_url}")
    print(f"  Title: {driver.title}")

    body_text = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Body preview: {body_text[:400]}")

    path = f"{SCREENSHOTS_DIR}/checkout-desktop.png"
    driver.save_screenshot(path)
    print(f"  Saved: {path}")

finally:
    driver.quit()
