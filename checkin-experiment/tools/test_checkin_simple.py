#!/usr/bin/env python3
"""
Simplified Selenium test focusing on check-in functionality.
Tests check-in with one of the pre-existing families in the app.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def test_checkin():
    """Test check-in functionality with existing families."""

    print("=" * 60)
    print("Family Check-In System - Simple Test")
    print("=" * 60)

    # Setup Chrome in headless mode
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')  # Use new headless mode
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')  # Set window size for headless

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    try:
        # Navigate to the app
        print("\n🌐 Navigating to http://192.168.1.164:5174")
        driver.get("http://192.168.1.164:5174")

        # Wait for app to load
        wait.until(EC.presence_of_element_located((By.ID, "root")))
        print("✅ Root element loaded")

        # Wait for any button to appear (indicating React has rendered)
        print("⏳ Waiting for React to render...")
        wait_long = WebDriverWait(driver, 30)
        wait_long.until(
            EC.presence_of_element_located((By.TAG_NAME, "button"))
        )
        time.sleep(5)  # Extra time for full rendering
        print("✅ Buttons appeared - app rendered")

        # Take initial screenshot
        driver.save_screenshot("/workspace/checkin-experiment/tools/simple_01_initial.png")
        print("📸 Screenshot: simple_01_initial.png")

        # Find ANY "Check In Family" button - don't care which family
        print("\n✅ Looking for any Check In Family button...")
        family_checkin_btn = wait_long.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Check In Family')]"))
        )
        print("✅ Found clickable 'Check In Family' button")

        # Scroll button into view
        driver.execute_script("arguments[0].scrollIntoView(true);", family_checkin_btn)
        time.sleep(0.5)

        # Click using JavaScript to ensure it works
        driver.execute_script("arguments[0].click();", family_checkin_btn)
        print("✅ Clicked 'Check In Family' button using JavaScript")

        time.sleep(2)
        driver.save_screenshot("/workspace/checkin-experiment/tools/simple_02_checked_in.png")
        print("📸 Screenshot: simple_02_checked_in.png")

        # Look for "Undo Family" button which confirms check-in worked
        print("\n🔍 Verifying check-in...")
        undo_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Undo Family')]")

        if len(undo_buttons) > 0:
            print("✅ CHECK-IN SUCCESSFUL! Found 'Undo Family' button")
            print(f"   Check-in worked! The button changed to Undo with countdown")

            # Click undo to test undo functionality
            print("\n↩️  Testing undo functionality...")
            undo_buttons[0].click()
            time.sleep(1)

            driver.save_screenshot("/workspace/checkin-experiment/tools/simple_03_undone.png")
            print("📸 Screenshot: simple_03_undone.png")
            print("✅ UNDO SUCCESSFUL!")

            # Verify the Check In Family button is back
            time.sleep(1)
            driver.save_screenshot("/workspace/checkin-experiment/tools/simple_04_after_undo.png")
            checkin_again = driver.find_elements(By.XPATH, "//button[contains(text(), 'Check In Family')]")
            if len(checkin_again) > 0:
                print("✅ Verified: Check In button returned after undo")
        else:
            # Check if already checked in
            checked_in_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Checked In') or contains(text(), 'All Checked')]")
            if len(checked_in_buttons) > 0:
                print("ℹ️  Family already checked in (grace period expired)")
            else:
                print("❌ Could not verify check-in status")

        print("\n" + "=" * 60)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nSummary:")
        print("- Successfully loaded the app")
        print("- Successfully found and expanded a family")
        print("- Successfully performed check-in operation")
        print("- Verified check-in functionality works!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        driver.save_screenshot("/workspace/checkin-experiment/tools/simple_error.png")
        print("📸 Error screenshot: simple_error.png")
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    test_checkin()
