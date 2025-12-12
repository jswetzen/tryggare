#!/usr/bin/env python
"""
Test that the undo timer countdown updates automatically without user interaction
"""

import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

# Initialize driver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

def login():
    """Login to the application"""
    print("Logging in...")
    driver.get("http://192.168.1.164:8080/login")

    # Wait for login page
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    )

    # Login
    driver.find_element(By.ID, "username").send_keys("admin")
    driver.find_element(By.ID, "password").send_keys("admin123")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Wait for navigation
    WebDriverWait(driver, 10).until(
        EC.url_contains("/checkin")
    )
    print("✓ Logged in successfully")

def extract_countdown_seconds(text):
    """Extract seconds from 'Undo (30s)' text"""
    match = re.search(r'\((\d+)s\)', text)
    if match:
        return int(match.group(1))
    return None

try:
    login()

    # Navigate to check-in page
    print("\nNavigating to check-in page...")
    driver.get("http://192.168.1.164:8080/checkin")

    # Wait for page to load
    time.sleep(2)

    # Find and click first family to expand
    print("Expanding first family...")
    family_toggle_buttons = driver.find_elements(By.CSS_SELECTOR, "[data-testid^='family-toggle-button-']")
    if not family_toggle_buttons:
        print("✗ No family toggle buttons found")
        driver.save_screenshot("/tmp/no_families.png")
        exit(1)

    family_toggle_buttons[0].click()
    time.sleep(1)

    # Find first child check-in button
    print("Looking for check-in button...")
    checkin_buttons = driver.find_elements(By.CSS_SELECTOR, "[data-testid^='child-check-in-button-']")
    if not checkin_buttons:
        print("✗ No check-in buttons found")
        driver.save_screenshot("/tmp/no_buttons.png")
        exit(1)

    # Click to check in a child
    print("Checking in child...")
    checkin_buttons[0].click()
    time.sleep(1)

    # Find undo button
    print("\nLooking for undo button...")
    undo_buttons = driver.find_elements(By.CSS_SELECTOR, "button")
    undo_button = None
    for button in undo_buttons:
        if "Undo" in button.text:
            undo_button = button
            break

    if not undo_button:
        print("✗ Undo button not found")
        driver.save_screenshot("/tmp/no_undo.png")
        exit(1)

    print(f"✓ Found undo button: '{undo_button.text}'")

    # Extract initial countdown
    initial_text = undo_button.text
    initial_seconds = extract_countdown_seconds(initial_text)

    if initial_seconds is None:
        print(f"✗ Could not parse countdown from: {initial_text}")
        driver.save_screenshot("/tmp/parse_error.png")
        exit(1)

    print(f"Initial countdown: {initial_seconds}s")

    # Wait 3 seconds WITHOUT any user interaction
    print("\nWaiting 3 seconds without interaction...")
    time.sleep(3)

    # Check countdown again
    # Re-find the button in case DOM updated
    undo_buttons = driver.find_elements(By.CSS_SELECTOR, "button")
    undo_button = None
    for button in undo_buttons:
        if "Undo" in button.text:
            undo_button = button
            break

    if not undo_button:
        print("✗ Undo button disappeared")
        driver.save_screenshot("/tmp/undo_gone.png")
        exit(1)

    final_text = undo_button.text
    final_seconds = extract_countdown_seconds(final_text)

    if final_seconds is None:
        print(f"✗ Could not parse countdown from: {final_text}")
        driver.save_screenshot("/tmp/parse_error_final.png")
        exit(1)

    print(f"Final countdown: {final_seconds}s")

    # Verify countdown decreased
    seconds_passed = initial_seconds - final_seconds
    print(f"\nCountdown decreased by: {seconds_passed}s")

    if seconds_passed >= 2:  # Allow for 2-4 second decrease (accounting for timing variations)
        print(f"✓ SUCCESS: Timer countdown is working! Decreased from {initial_seconds}s to {final_seconds}s")
        driver.save_screenshot("/tmp/timer_success.png")
        exit(0)
    else:
        print(f"✗ FAILURE: Timer did not decrease properly")
        print(f"  Expected at least 2 second decrease, got {seconds_passed}s")
        print(f"  Initial: '{initial_text}'")
        print(f"  Final: '{final_text}'")
        driver.save_screenshot("/tmp/timer_failure.png")
        exit(1)

except Exception as e:
    print(f"\n✗ Test failed with error: {e}")
    import traceback
    traceback.print_exc()
    driver.save_screenshot("/tmp/test_error.png")
    exit(1)

finally:
    driver.quit()
