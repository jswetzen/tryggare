#!/usr/bin/env python
"""
Simple test to verify login workflow and API access
"""

import os
import django

# IMPORTANT: Use local settings (same as running server) not test settings!
# This ensures password hashing is compatible
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from accounts.models import AdminUser

# Create test user with production password hasher
test_username = "simpletest"
test_password = "testpass123"
AdminUser.objects.filter(username=test_username).delete()
user = AdminUser.objects.create_user(username=test_username, password=test_password, name="Simple Test")
print(f"✓ Created user: {user.username} with password hash: {user.password[:30]}...")

# Configure Chrome
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")  # Prevent crashes (may slow down tests)
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

# Disable images for speed
prefs = {"profile.managed_default_content_settings.images": 2}
chrome_options.add_experimental_option("prefs", prefs)

# Enable logging
chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL', 'performance': 'ALL'})

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print("\n1. Navigating to login page...")
    driver.get("http://localhost:5173/login")
    print(f"   URL: {driver.current_url}")

    print("\n2. Filling in credentials...")
    username_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    )
    password_field = driver.find_element(By.ID, "password")
    username_field.send_keys(test_username)
    password_field.send_keys(test_password)

    print("\n3. Submitting login...")
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()

    print("\n4. Waiting for redirect...")
    import time
    time.sleep(3)  # Wait for any redirect
    print(f"   Current URL: {driver.current_url}")

    # Check if we're still on login page or redirected
    if "/login" in driver.current_url:
        print("   ✗ Still on login page - login may have failed")
        # Check for error messages
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "Invalid" in page_text or "error" in page_text.lower():
            print(f"   Error on page: {page_text[:200]}")
    elif "/checkin" in driver.current_url:
        print(f"   ✓ Redirected to checkin page")
    else:
        print(f"   ? Redirected to unexpected page")

    print("\n5. Checking cookies...")
    cookies = driver.get_cookies()
    print(f"   Found {len(cookies)} cookies:")
    for cookie in cookies:
        print(f"   - {cookie['name']}: {cookie.get('value', '')[:20]}... (SameSite={cookie.get('sameSite', 'not set')})")

    # Check for session cookie
    session_cookie = [c for c in cookies if c['name'] == 'sessionid']
    csrf_cookie = [c for c in cookies if c['name'] == 'csrftoken']

    if session_cookie:
        print(f"   ✓ Session cookie found")
    else:
        print(f"   ✗ NO SESSION COOKIE!")

    if csrf_cookie:
        print(f"   ✓ CSRF cookie found")
    else:
        print(f"   ✗ NO CSRF COOKIE!")

    print("\n6. Checking page content...")
    page_source = driver.page_source
    if "Check-In" in page_source or "Check In" in page_source:
        print("   ✓ Check-in page loaded")
    else:
        print("   ✗ Check-in page NOT properly loaded")
        print(f"   Page length: {len(page_source)} chars")

    print("\n7. Checking browser console for errors...")
    logs = driver.get_log('browser')
    errors = [log for log in logs if log['level'] in ['SEVERE', 'ERROR']]
    if errors:
        print(f"   ✗ Found {len(errors)} errors:")
        for log in errors[:5]:  # Show first 5
            msg = log['message']
            if 'favicon' not in msg.lower():  # Skip favicon errors
                print(f"   - {msg[:100]}")
    else:
        print("   ✓ No errors in console")

    print("\n✅ Login test completed successfully!")

except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
finally:
    driver.quit()
    AdminUser.objects.filter(username=test_username).delete()
