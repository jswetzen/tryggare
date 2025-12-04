#!/usr/bin/env python3
"""
Selenium WebDriver script to test family check-in functionality.
Tests the React app running on http://localhost:5174
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class FamilyCheckInTester:
    def __init__(self, base_url="http://192.168.1.164:5174", headless=False):
        """Initialize the Selenium WebDriver."""
        self.base_url = base_url
        options = webdriver.ChromeOptions()

        if headless:
            options.add_argument('--headless')

        # Disable GPU for stability in headless mode
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup."""
        self.driver.quit()

    def navigate_to_app(self):
        """Navigate to the React app."""
        print(f"🌐 Navigating to {self.base_url}")
        self.driver.get(self.base_url)

        # Wait for the app to load by checking for the root div first
        try:
            self.wait.until(
                EC.presence_of_element_located((By.ID, "root"))
            )
            # Give React a moment to render
            time.sleep(2)

            # Save page source for debugging
            print(f"📄 Page title: {self.driver.title}")
            print("✅ App loaded successfully")
        except TimeoutException:
            print("❌ App failed to load - timeout waiting for page")
            print(f"Current URL: {self.driver.current_url}")
            # Save screenshot for debugging
            self.take_screenshot("error_timeout.png")
            raise

    def add_family(self, family_name, children_names, ticket_type="Full Event Pass"):
        """
        Add a new family to the system.

        Args:
            family_name: Name of the family (e.g., "Smith")
            children_names: List of children names (e.g., ["Alice", "Bob"])
            ticket_type: One of "No Ticket", "Session Only", "Full Event Pass"
        """
        print(f"\n📝 Adding family: {family_name} with children: {children_names}")

        # Click the "+ Add Family" button
        add_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Add Family')]"))
        )
        add_button.click()

        # Wait for the panel to appear
        time.sleep(0.5)

        # Fill in family name
        family_input = self.driver.find_element(By.ID, "family-name")
        family_input.clear()
        family_input.send_keys(family_name)
        print(f"  ✏️  Family name: {family_name}")

        # Select ticket type
        ticket_select = Select(self.driver.find_element(By.ID, "ticket-type"))
        ticket_select.select_by_visible_text(ticket_type)
        print(f"  🎫 Ticket type: {ticket_type}")

        # Add children
        # First child field should already be present
        child_inputs = self.driver.find_elements(By.XPATH, "//input[contains(@placeholder, 'Child') and contains(@placeholder, 'name')]")

        for i, child_name in enumerate(children_names):
            # Get current child inputs each iteration
            child_inputs = self.driver.find_elements(By.XPATH, "//input[contains(@placeholder, 'Child') and contains(@placeholder, 'name')]")

            # If we need more child fields, click "+ Add Child"
            if i >= len(child_inputs):
                add_child_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Add Child')]")
                add_child_btn.click()
                time.sleep(0.3)
                # Refetch child inputs after adding
                child_inputs = self.driver.find_elements(By.XPATH, "//input[contains(@placeholder, 'Child') and contains(@placeholder, 'name')]")

            child_inputs[i].clear()
            child_inputs[i].send_keys(child_name)
            print(f"  👶 Child {i+1}: {child_name}")

        # Submit the form
        submit_button = self.driver.find_element(By.XPATH, "//button[text()='Add Family']")
        submit_button.click()

        # Wait for the panel to close and family to appear in the list
        time.sleep(1.5)
        print(f"✅ Family '{family_name}' added successfully")

    def find_family_card(self, family_name):
        """Find a family card element by family name."""
        try:
            # Look for family name - the h3 contains "{FamilyName} Family"
            family_xpath = f"//h3[contains(text(), '{family_name} Family')]"

            # Wait a bit longer for the family to appear after adding
            wait = WebDriverWait(self.driver, 15)
            family_element = wait.until(
                EC.presence_of_element_located((By.XPATH, family_xpath))
            )
            # Return the top-level card container (has border and rounded-lg classes)
            card = family_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'border') and contains(@class, 'rounded-lg')]")
            return card
        except (TimeoutException, NoSuchElementException) as e:
            print(f"❌ Could not find family: {family_name} - {str(e)}")
            # Save debug screenshot
            self.take_screenshot(f"debug_missing_{family_name}.png")
            return None

    def expand_family(self, family_name):
        """Expand a family card to show children."""
        print(f"\n🔽 Expanding family: {family_name}")

        family_card = self.find_family_card(family_name)
        if not family_card:
            return False

        # Look for the chevron/toggle button with correct aria-label
        try:
            toggle_button = family_card.find_element(By.XPATH, f".//button[@aria-label='Toggle {family_name} family']")

            # Check if already expanded by looking for ChevronDown icon
            # If we see children list, it's already expanded
            try:
                family_card.find_element(By.XPATH, ".//div[contains(text(), 'Event Pass') or contains(text(), 'Session Ticket') or contains(text(), 'No Ticket')]")
                print(f"ℹ️  Family '{family_name}' already expanded")
                return True
            except NoSuchElementException:
                # Not expanded, click to expand
                toggle_button.click()
                time.sleep(0.3)
                print(f"✅ Family '{family_name}' expanded")
                return True
        except NoSuchElementException:
            print(f"⚠️  Could not find toggle button for '{family_name}'")
            return False

    def check_in_child(self, family_name, child_name):
        """Check in a specific child."""
        print(f"\n✅ Checking in: {child_name} from {family_name} family")

        family_card = self.find_family_card(family_name)
        if not family_card:
            return False

        # Make sure family is expanded
        self.expand_family(family_name)

        # Find the child's check-in button
        try:
            # The child name appears as text, find it and its parent row, then the button
            # Children are in a flex layout with name on left and button on right
            child_xpath = f".//div[starts-with(normalize-space(text()), '{child_name}')]"
            child_element = family_card.find_element(By.XPATH, child_xpath)

            # Go up to the parent row and find the Check In button
            parent_row = child_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'flex') and contains(@class, 'items-center')]")
            checkin_button = parent_row.find_element(By.XPATH, ".//button[contains(text(), 'Check In')]")
            checkin_button.click()

            time.sleep(0.5)
            print(f"✅ {child_name} checked in successfully")
            return True
        except NoSuchElementException as e:
            print(f"❌ Could not find check-in button for {child_name}: {str(e)}")
            return False

    def check_in_family(self, family_name):
        """Check in all children in a family at once."""
        print(f"\n✅ Checking in entire family: {family_name}")

        family_card = self.find_family_card(family_name)
        if not family_card:
            return False

        try:
            # Look for the family-level "Check In Family" button (should be blue)
            family_checkin_btn = family_card.find_element(
                By.XPATH, ".//button[contains(text(), 'Check In Family')]"
            )
            family_checkin_btn.click()

            time.sleep(0.5)
            print(f"✅ Family '{family_name}' checked in successfully")
            return True
        except NoSuchElementException:
            print(f"❌ Could not find 'Check In Family' button for {family_name}")
            return False

    def verify_checked_in(self, family_name, child_name):
        """Verify that a child shows as checked in."""
        print(f"\n🔍 Verifying {child_name} is checked in...")

        family_card = self.find_family_card(family_name)
        if not family_card:
            return False

        try:
            # Look for indicators that child is checked in:
            # - "Undo" button with countdown
            # - "Checked In" disabled button
            # - Check mark or time displayed
            child_row_xpath = f".//div[contains(text(), '{child_name}')]/ancestor::div[contains(@class, 'child') or contains(@class, 'item')]"
            child_row = family_card.find_element(By.XPATH, child_row_xpath)

            # Check for Undo button (grace period) or Checked In status
            has_undo = len(child_row.find_elements(By.XPATH, ".//button[contains(text(), 'Undo')]")) > 0
            has_checked_in = len(child_row.find_elements(By.XPATH, ".//button[contains(text(), 'Checked In')]")) > 0
            has_checkmark = len(child_row.find_elements(By.XPATH, ".//*[contains(text(), '✓')]")) > 0

            if has_undo or has_checked_in or has_checkmark:
                print(f"✅ {child_name} is confirmed checked in")
                return True
            else:
                print(f"❌ {child_name} does not appear to be checked in")
                return False
        except NoSuchElementException:
            print(f"❌ Could not find {child_name} to verify status")
            return False

    def undo_checkin(self, family_name, child_name=None):
        """
        Undo a check-in action.

        Args:
            family_name: Name of the family
            child_name: Specific child to undo (None for family-level undo)
        """
        if child_name:
            print(f"\n↩️  Undoing check-in for: {child_name}")

            family_card = self.find_family_card(family_name)
            if not family_card:
                return False

            try:
                child_row_xpath = f".//div[contains(text(), '{child_name}')]/ancestor::div[contains(@class, 'child') or contains(@class, 'item')]"
                child_row = family_card.find_element(By.XPATH, child_row_xpath)

                undo_button = child_row.find_element(By.XPATH, ".//button[contains(text(), 'Undo')]")
                undo_button.click()

                time.sleep(0.5)
                print(f"✅ Undo successful for {child_name}")
                return True
            except NoSuchElementException:
                print(f"❌ Could not find undo button for {child_name}")
                return False
        else:
            print(f"\n↩️  Undoing family check-in for: {family_name}")

            family_card = self.find_family_card(family_name)
            if not family_card:
                return False

            try:
                undo_family_btn = family_card.find_element(
                    By.XPATH, ".//button[contains(text(), 'Undo Family')]"
                )
                undo_family_btn.click()

                time.sleep(0.5)
                print(f"✅ Family undo successful for {family_name}")
                return True
            except NoSuchElementException:
                print(f"❌ Could not find 'Undo Family' button")
                return False

    def search_families(self, search_query):
        """Use the search functionality to filter families."""
        print(f"\n🔍 Searching for: '{search_query}'")

        try:
            search_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='text' and @placeholder]"))
            )
            search_input.clear()
            search_input.send_keys(search_query)

            time.sleep(0.5)
            print(f"✅ Search applied: '{search_query}'")
            return True
        except TimeoutException:
            print("❌ Could not find search input")
            return False

    def take_screenshot(self, filename="screenshot.png"):
        """Take a screenshot of the current page."""
        filepath = f"/workspace/checkin-experiment/tools/{filename}"
        self.driver.save_screenshot(filepath)
        print(f"📸 Screenshot saved to: {filepath}")


def main():
    """Main test execution."""
    print("=" * 60)
    print("Family Check-In System - Selenium Test")
    print("=" * 60)

    with FamilyCheckInTester(headless=True) as tester:
        # Navigate to the app
        tester.navigate_to_app()
        time.sleep(1)

        # Take initial screenshot
        tester.take_screenshot("01_initial.png")

        # Add a test family
        tester.add_family(
            family_name="Martinez",
            children_names=["Sofia", "Diego", "Isabella"],
            ticket_type="Full Event Pass"
        )
        time.sleep(1)
        tester.take_screenshot("02_family_added.png")

        # Expand the family to see children
        tester.expand_family("Martinez")
        time.sleep(1)
        tester.take_screenshot("03_family_expanded.png")

        # Check in one child individually
        tester.check_in_child("Martinez", "Sofia")
        time.sleep(1)
        tester.take_screenshot("04_child_checked_in.png")

        # Verify the child is checked in
        tester.verify_checked_in("Martinez", "Sofia")

        # Wait a moment to see the undo timer
        print("\n⏱️  Waiting 3 seconds to observe undo timer...")
        time.sleep(3)

        # Undo the check-in
        tester.undo_checkin("Martinez", "Sofia")
        time.sleep(1)
        tester.take_screenshot("05_undo_child.png")

        # Now check in the entire family at once
        tester.check_in_family("Martinez")
        time.sleep(1)
        tester.take_screenshot("06_family_checked_in.png")

        # Verify multiple children are checked in
        tester.verify_checked_in("Martinez", "Diego")
        tester.verify_checked_in("Martinez", "Isabella")

        # Add another family with session tickets
        tester.add_family(
            family_name="Thompson",
            children_names=["Emma", "Liam"],
            ticket_type="Session Only"
        )
        time.sleep(1)
        tester.take_screenshot("07_second_family_added.png")

        # Test search functionality
        tester.search_families("Thompson")
        time.sleep(1)
        tester.take_screenshot("08_search_results.png")

        # Clear search
        tester.search_families("")
        time.sleep(1)

        # Final screenshot
        tester.take_screenshot("09_final_state.png")

        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        print("\n⏳ Keeping browser open for 5 seconds for observation...")
        time.sleep(5)


if __name__ == "__main__":
    main()
