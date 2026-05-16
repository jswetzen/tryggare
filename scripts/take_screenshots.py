"""
Screenshot capture script using Selenium.
Takes screenshots of the check-in app for documentation purposes.
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
QR_CODE = "8YDNIP"  # Noah Dahl's QR code


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


def login(driver, timeout=20):
    """Login and wait for redirect to /checkin."""
    print(f"  Navigating to login page...")
    driver.get(f"{FRONTEND_URL}/login")
    time.sleep(2)

    print(f"  Filling in credentials...")
    username_field = wait_for(driver, By.ID, "username", timeout=10)
    password_field = driver.find_element(By.ID, "password")

    username_field.clear()
    username_field.send_keys(USERNAME)
    password_field.clear()
    password_field.send_keys(PASSWORD)

    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_btn.click()

    # Wait longer for redirect
    try:
        WebDriverWait(driver, timeout).until(EC.url_contains("/checkin"))
        print(f"  Login successful. Current URL: {driver.current_url}")
        return True
    except Exception:
        print(f"  Login redirect not detected within {timeout}s. URL: {driver.current_url}")
        # Try to check if we're actually logged in
        if "login" not in driver.current_url.lower():
            print(f"  But URL doesn't contain 'login', so we may be logged in")
            return True
        # Take a debug screenshot
        driver.save_screenshot(f"{SCREENSHOTS_DIR}/login-debug.png")
        print(f"  Debug screenshot saved")
        return False


def wait_for_page_content(driver, timeout=12):
    """Wait for dynamic page content to load."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "main"))
        )
    except Exception:
        pass
    time.sleep(2.5)


os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
print(f"Screenshots will be saved to: {SCREENSHOTS_DIR}")

results = {}

# ===== SCREENSHOT 1: Check-in page at desktop 1280x800 =====
print("\n=== Screenshot 1: checkin-desktop.png (1280x800) ===")
driver = make_driver(1280, 800)
try:
    login(driver)
    driver.get(f"{FRONTEND_URL}/checkin")
    wait_for_page_content(driver)

    print(f"  URL: {driver.current_url}")
    print(f"  Title: {driver.title}")

    path = f"{SCREENSHOTS_DIR}/checkin-desktop.png"
    driver.save_screenshot(path)
    print(f"  Saved: {path}")
    results["checkin-desktop.png"] = ("SUCCESS", path)
except Exception as e:
    print(f"  ERROR: {e}")
    results["checkin-desktop.png"] = ("FAILED", str(e))
finally:
    driver.quit()

time.sleep(2)

# ===== SCREENSHOT 2: Check-in page at mobile 390x844 =====
print("\n=== Screenshot 2: checkin-mobile.png (390x844) ===")
driver = make_driver(390, 844)
try:
    login(driver)
    driver.get(f"{FRONTEND_URL}/checkin")
    wait_for_page_content(driver)

    print(f"  URL: {driver.current_url}")

    path = f"{SCREENSHOTS_DIR}/checkin-mobile.png"
    driver.save_screenshot(path)
    print(f"  Saved: {path}")
    results["checkin-mobile.png"] = ("SUCCESS", path)
except Exception as e:
    print(f"  ERROR: {e}")
    results["checkin-mobile.png"] = ("FAILED", str(e))
finally:
    driver.quit()

time.sleep(2)

# ===== SCREENSHOT 3: Checkout page (desktop 1280x800) =====
print("\n=== Screenshot 3: checkout-desktop.png (1280x800) ===")
driver = make_driver(1280, 800)
try:
    login(driver, timeout=25)

    # Navigate to /checkout
    print("  Navigating to /checkout...")
    driver.get(f"{FRONTEND_URL}/checkout")
    wait_for_page_content(driver)

    print(f"  URL: {driver.current_url}")
    print(f"  Title: {driver.title}")

    body_text = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Body preview: {body_text[:300]}")

    path = f"{SCREENSHOTS_DIR}/checkout-desktop.png"
    driver.save_screenshot(path)
    print(f"  Saved: {path}")
    results["checkout-desktop.png"] = ("SUCCESS", path)
except Exception as e:
    print(f"  ERROR: {e}")
    try:
        driver.save_screenshot(f"{SCREENSHOTS_DIR}/checkout-desktop-error.png")
    except Exception:
        pass
    results["checkout-desktop.png"] = ("FAILED", str(e))
finally:
    driver.quit()

time.sleep(2)

# ===== SCREENSHOT 4: QR page for Noah Dahl =====
print(f"\n=== Screenshot 4: qr-page.png (390x844) - Noah Dahl QR: {QR_CODE} ===")
driver = make_driver(390, 844)
try:
    url = f"{FRONTEND_URL}/qr/{QR_CODE}"
    print(f"  Navigating to {url}...")
    driver.get(url)
    wait_for_page_content(driver)

    print(f"  URL: {driver.current_url}")
    print(f"  Title: {driver.title}")

    body_text = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Body preview: {body_text[:200]}")

    path = f"{SCREENSHOTS_DIR}/qr-page.png"
    driver.save_screenshot(path)
    print(f"  Saved: {path}")
    results["qr-page.png"] = ("SUCCESS", path)
except Exception as e:
    print(f"  ERROR: {e}")
    results["qr-page.png"] = ("FAILED", str(e))
finally:
    driver.quit()

print("\n\n=== RESULTS ===")
for name, (status, info) in results.items():
    print(f"  {status}: {name} - {info}")
