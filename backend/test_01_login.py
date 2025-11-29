#!/usr/bin/env python
"""Test 1: Login only"""
import os, django
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

# Create user
AdminUser.objects.filter(username="test1").delete()
AdminUser.objects.create_user(username="test1", password="test123", name="Test 1")

# Setup Chrome
opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1920,1080")
opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

try:
    print("\n=== TEST 1: LOGIN ===")
    driver.get("http://localhost:5173/login")

    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "username")))
    driver.find_element(By.ID, "username").send_keys("test1")
    driver.find_element(By.ID, "password").send_keys("test123")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    import time
    time.sleep(3)
    print(f"After submit - URL: {driver.current_url}")

    # Check for errors
    body_text = driver.find_element(By.TAG_NAME, "body").text
    if "Invalid" in body_text or "error" in body_text.lower():
        print(f"ERROR ON PAGE: {body_text[:200]}")

    # Check browser logs
    logs = driver.get_log('browser')
    for log in logs:
        if log['level'] in ['SEVERE', 'ERROR'] and 'favicon' not in log['message'].lower():
            print(f"BROWSER ERROR: {log['message'][:150]}")

    if "/checkin" not in driver.current_url:
        raise Exception(f"Login failed - still at {driver.current_url}")

    # Check cookies
    cookies = {c['name']: c for c in driver.get_cookies()}
    assert 'sessionid' in cookies, "No session cookie!"
    assert 'csrftoken' in cookies, "No CSRF cookie!"

    print(f"✅ LOGIN SUCCESS - URL: {driver.current_url}")
    print(f"✅ Session cookie: {cookies['sessionid']['value'][:20]}...")
    print(f"✅ CSRF cookie: {cookies['csrftoken']['value'][:20]}...")

finally:
    driver.quit()
    AdminUser.objects.filter(username="test1").delete()
