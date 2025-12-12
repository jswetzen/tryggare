#!/usr/bin/env python
"""
Quick test to verify the QR page loads correctly
Run with: uv run python test_qr_page.py
"""
import os
import sys
import django
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
os.environ['DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:5433/checkins'
sys.path.insert(0, '/workspace/check-ins/backend')
django.setup()

from families.models import Child

print("🧪 Testing QR Page Load\n")
print("=" * 60)

# Find a child with QR token
child = Child.objects.exclude(qr_token__isnull=True).exclude(qr_token='').first()
if not child:
    print("❌ No children with QR tokens found in database")
    sys.exit(1)

print(f"Testing with child: {child.first_name} {child.last_name}")
print(f"QR Token: {child.qr_token}\n")

# Setup Chrome driver
options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    # Load QR page
    url = f'http://localhost:8080/qr/{child.qr_token}'
    print(f"Loading URL: {url}")
    driver.get(url)
    time.sleep(3)

    # Get page source
    page_source = driver.page_source

    print("\nChecking page content...")

    # Look for child name
    if child.first_name in page_source and child.last_name in page_source:
        print(f"✅ Child name found: {child.first_name} {child.last_name}")
    else:
        print(f"❌ Child name NOT found: {child.first_name} {child.last_name}")
        print("   Page title:", driver.title)

    # Check for allergies section
    if child.allergies and child.allergies in page_source:
        print(f"✅ Allergies displayed: {child.allergies}")
    elif 'Allergies' in page_source or 'allergies' in page_source:
        print("✅ Allergies section present")

    # Check for parent info
    parents = child.family.parents.all()
    if parents:
        parent_found = any(parent.name in page_source for parent in parents)
        if parent_found:
            print(f"✅ Parent information displayed")
        else:
            print("⚠️  Parent information not found")

    # Check for error messages
    if 'Failed to load' in page_source or 'error' in page_source.lower():
        print("⚠️  Error message detected on page")

    # Save screenshot
    screenshot_path = '/tmp/qr_page_test.png'
    driver.save_screenshot(screenshot_path)
    print(f"\n📸 Screenshot saved to {screenshot_path}")

    print("\n" + "=" * 60)
    print("✅ QR Page Test Complete")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ Error during test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    driver.quit()
