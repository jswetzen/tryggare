#!/usr/bin/env python3
"""
Quick Playwright test to verify undo timer countdown functionality
Tests against production deployment (port 8080)
"""
import time
from playwright.sync_api import sync_playwright, expect

def test_undo_timer():
    print("=" * 60)
    print("UNDO TIMER COUNTDOWN TEST")
    print("=" * 60)
    print()

    with sync_playwright() as p:
        # Launch browser
        print("1. Launching browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Collect console messages
        console_messages = []
        errors = []

        def handle_console(msg):
            console_messages.append(f"[{msg.type}] {msg.text}")
            if msg.type == 'error':
                errors.append(msg.text)

        page.on('console', handle_console)

        try:
            # Navigate to production checkin page
            print("2. Navigating to http://localhost:8080/checkin...")
            page.goto('http://localhost:8080/checkin', wait_until='networkidle')
            time.sleep(1)

            # Check if login is needed
            if 'login' in page.url.lower() or page.locator('input[name="username"]').count() > 0:
                print("3. Login required, authenticating...")
                page.fill('input[name="username"]', 'admin')
                page.fill('input[name="password"]', 'admin123')
                page.click('button[type="submit"]')
                page.wait_for_url('**/checkin', timeout=5000)
                time.sleep(1)
            else:
                print("3. Already authenticated, proceeding...")

            print("4. Looking for TestChild2...")

            # Take screenshot before check-in
            page.screenshot(path='/tmp/before_checkin.png')
            print("   Screenshot saved: /tmp/before_checkin.png")

            # Find TestChild2 - try multiple selectors
            test_child_button = None

            # Try finding by text content
            buttons = page.locator('button:has-text("Check In")')
            print(f"   Found {buttons.count()} 'Check In' buttons")

            # Look for TestChild2 in the page
            if page.locator('text=TestChild2').count() > 0:
                print("   ✓ Found TestChild2 in the page")

                # Find the Check In button near TestChild2
                # Try to find the parent container and then the button
                child_row = page.locator('div:has-text("TestChild2")').first
                check_in_btn = child_row.locator('button:has-text("Check In")').first

                if check_in_btn.count() > 0:
                    print("   ✓ Found Check In button for TestChild2")
                    test_child_button = check_in_btn
                else:
                    print("   ✗ Could not find Check In button for TestChild2")
            else:
                print("   ✗ TestChild2 not found in the page")
                print("   Available children:")
                children = page.locator('text=/Child/i').all_text_contents()
                for child in children[:10]:  # First 10
                    print(f"     - {child}")

            if test_child_button is None:
                print("   ⚠ Cannot find TestChild2, will use first available Check In button")
                if buttons.count() > 0:
                    test_child_button = buttons.first
                else:
                    raise Exception("No Check In buttons found on page")

            # Click the check-in button
            print("5. Clicking Check In button...")
            test_child_button.click()
            time.sleep(0.5)

            # Take screenshot after check-in
            page.screenshot(path='/tmp/after_checkin.png')
            print("   Screenshot saved: /tmp/after_checkin.png")

            # Wait 2 seconds and check for countdown
            print("6. Waiting 2 seconds to observe countdown...")
            time.sleep(2)

            # Take screenshot during countdown
            page.screenshot(path='/tmp/countdown.png')
            print("   Screenshot saved: /tmp/countdown.png")

            # Check for undo button with countdown
            print("7. Checking for Undo button with countdown...")

            # Look for undo buttons
            undo_buttons = page.locator('button:has-text("Undo")').all()
            print(f"   Found {len(undo_buttons)} Undo buttons")

            if len(undo_buttons) > 0:
                for i, btn in enumerate(undo_buttons):
                    btn_text = btn.text_content()
                    print(f"   Undo button {i+1}: '{btn_text}'")

                    # Check if countdown is present (e.g., "Undo (28s)")
                    if '(' in btn_text and 's)' in btn_text:
                        print(f"   ✅ SUCCESS: Countdown detected in button text: '{btn_text}'")

                        # Extract the number
                        import re
                        match = re.search(r'\((\d+)s\)', btn_text)
                        if match:
                            seconds = int(match.group(1))
                            print(f"   Timer showing: {seconds} seconds remaining")

                            if seconds <= 28 and seconds >= 26:
                                print(f"   ✅ Timer is counting down correctly (started at ~30s, now at {seconds}s after 2 second wait)")
                            else:
                                print(f"   ⚠ Timer value unexpected (expected 26-28s after 2 second wait, got {seconds}s)")
                    else:
                        print(f"   ⚠ No countdown detected in button text: '{btn_text}'")
                        print(f"   Expected format: 'Undo (Xs)' where X is a number")
            else:
                print("   ❌ FAIL: No Undo buttons found")
                print("   Expected to see Undo button after check-in")

                # Check what buttons are visible
                all_buttons = page.locator('button').all()
                print(f"   All buttons on page ({len(all_buttons)}):")
                for btn in all_buttons[:20]:  # First 20
                    print(f"     - {btn.text_content()}")

            # Report console errors
            print()
            print("8. Console Messages:")
            if errors:
                print(f"   ❌ Found {len(errors)} console errors:")
                for error in errors:
                    print(f"     ERROR: {error}")
            else:
                print("   ✓ No console errors")

            if console_messages:
                print(f"   All console messages ({len(console_messages)}):")
                for msg in console_messages[-10:]:  # Last 10
                    print(f"     {msg}")

        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            page.screenshot(path='/tmp/error.png')
            print("   Error screenshot saved: /tmp/error.png")
            raise

        finally:
            browser.close()

    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    test_undo_timer()
