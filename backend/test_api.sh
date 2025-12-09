#!/bin/bash
# Backend API Testing Script
# This script tests the Django REST API endpoints

set -e  # Exit on error

BASE_URL="http://localhost:8000"
COOKIES_FILE="/tmp/django_cookies.txt"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Django Backend API Test Suite"
echo "========================================="
echo ""

# Function to print test results
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Clean up old cookies
rm -f $COOKIES_FILE

echo "Test 1: Service Health Check"
echo "-----------------------------"
if curl -s -o /dev/null -w "%{http_code}" $BASE_URL/admin/ | grep -q "200\|302"; then
    print_success "Django server is responding"
else
    print_error "Django server is not responding"
    exit 1
fi
echo ""

echo "Test 2: Unauthenticated API Access (Should Fail)"
echo "-------------------------------------------------"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/api/families/)
if [ "$RESPONSE" = "403" ]; then
    print_success "API correctly requires authentication (403)"
else
    print_error "Expected 403, got $RESPONSE"
fi
echo ""

echo "Test 3: Login Required"
echo "----------------------"
print_info "Please provide your admin credentials:"
read -p "Username: " USERNAME
read -sp "Password: " PASSWORD
echo ""

# Get CSRF token
curl -s -c $COOKIES_FILE $BASE_URL/admin/login/ > /dev/null
CSRF_TOKEN=$(grep csrftoken $COOKIES_FILE | awk '{print $7}')

if [ -z "$CSRF_TOKEN" ]; then
    print_error "Could not get CSRF token"
    exit 1
fi

print_info "CSRF Token: ${CSRF_TOKEN:0:10}..."

# Login via Django admin (simpler than REST API login)
LOGIN_RESPONSE=$(curl -s -b $COOKIES_FILE -c $COOKIES_FILE \
    -X POST $BASE_URL/admin/login/ \
    -H "Referer: $BASE_URL/admin/login/" \
    -d "username=$USERNAME&password=$PASSWORD&csrfmiddlewaretoken=$CSRF_TOKEN" \
    -w "%{http_code}" -o /dev/null)

if [ "$LOGIN_RESPONSE" = "302" ]; then
    print_success "Login successful"
else
    print_error "Login failed (status: $LOGIN_RESPONSE)"
    exit 1
fi
echo ""

echo "Test 4: Authenticated API Access"
echo "---------------------------------"
FAMILIES_RESPONSE=$(curl -s -b $COOKIES_FILE $BASE_URL/api/families/)
if echo "$FAMILIES_RESPONSE" | jq . > /dev/null 2>&1; then
    FAMILY_COUNT=$(echo "$FAMILIES_RESPONSE" | jq 'length')
    print_success "Successfully accessed families API ($FAMILY_COUNT families)"
else
    print_error "Could not access families API or invalid JSON response"
fi
echo ""

echo "Test 5: Create Test Family"
echo "--------------------------"
FAMILY_DATA='{"notes":"Test family created by test script"}'
FAMILY_RESPONSE=$(curl -s -b $COOKIES_FILE -c $COOKIES_FILE \
    -X POST $BASE_URL/api/families/ \
    -H "X-CSRFToken: $CSRF_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$FAMILY_DATA")

if echo "$FAMILY_RESPONSE" | jq . > /dev/null 2>&1; then
    FAMILY_ID=$(echo "$FAMILY_RESPONSE" | jq -r '.id')
    print_success "Created family with ID: $FAMILY_ID"
else
    print_error "Failed to create family"
    echo "$FAMILY_RESPONSE"
fi
echo ""

echo "Test 6: Create Test Parent"
echo "--------------------------"
PARENT_DATA="{
    \"family\": \"$FAMILY_ID\",
    \"name\": \"Test Parent\",
    \"phone_number\": \"555-1234\",
    \"email\": \"test@example.com\",
    \"relationship\": \"Parent\"
}"
PARENT_RESPONSE=$(curl -s -b $COOKIES_FILE -c $COOKIES_FILE \
    -X POST $BASE_URL/api/parents/ \
    -H "X-CSRFToken: $CSRF_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PARENT_DATA")

if echo "$PARENT_RESPONSE" | jq . > /dev/null 2>&1; then
    PARENT_ID=$(echo "$PARENT_RESPONSE" | jq -r '.id')
    print_success "Created parent with ID: $PARENT_ID"
else
    print_error "Failed to create parent"
    echo "$PARENT_RESPONSE"
fi
echo ""

echo "Test 7: Create Test Child"
echo "-------------------------"
CHILD_DATA="{
    \"family\": \"$FAMILY_ID\",
    \"first_name\": \"Test\",
    \"last_name\": \"Child\",
    \"birthdate\": \"2020-01-15\",
    \"allergies\": \"None\",
    \"notes\": \"Test child\"
}"
CHILD_RESPONSE=$(curl -s -b $COOKIES_FILE -c $COOKIES_FILE \
    -X POST $BASE_URL/api/children/ \
    -H "X-CSRFToken: $CSRF_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$CHILD_DATA")

if echo "$CHILD_RESPONSE" | jq . > /dev/null 2>&1; then
    CHILD_ID=$(echo "$CHILD_RESPONSE" | jq -r '.id')
    print_success "Created child with ID: $CHILD_ID"

    # Check if QR token is null (should be initially)
    QR_TOKEN_BEFORE=$(echo "$CHILD_RESPONSE" | jq -r '.qr_token')
    if [ "$QR_TOKEN_BEFORE" = "null" ]; then
        print_success "QR token is null before check-in (expected)"
    else
        print_error "QR token should be null before first check-in"
    fi
else
    print_error "Failed to create child"
    echo "$CHILD_RESPONSE"
fi
echo ""

echo "Test 8: Create Test Event and Session"
echo "--------------------------------------"
EVENT_DATA="{
    \"name\": \"Test Event\",
    \"start_date\": \"2025-11-23\",
    \"end_date\": \"2025-11-24\",
    \"is_multi_day\": true
}"
EVENT_RESPONSE=$(curl -s -b $COOKIES_FILE -c $COOKIES_FILE \
    -X POST $BASE_URL/api/events/ \
    -H "X-CSRFToken: $CSRF_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$EVENT_DATA")

if echo "$EVENT_RESPONSE" | jq . > /dev/null 2>&1; then
    EVENT_ID=$(echo "$EVENT_RESPONSE" | jq -r '.id')
    print_success "Created event with ID: $EVENT_ID"
else
    print_error "Failed to create event"
fi

SESSION_DATA="{
    \"event\": \"$EVENT_ID\",
    \"name\": \"Test Session\",
    \"start_time\": \"2025-11-23T09:00:00Z\",
    \"end_time\": \"2025-11-23T12:00:00Z\",
    \"requires_ticket\": false
}"
SESSION_RESPONSE=$(curl -s -b $COOKIES_FILE -c $COOKIES_FILE \
    -X POST $BASE_URL/api/sessions/ \
    -H "X-CSRFToken: $CSRF_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$SESSION_DATA")

if echo "$SESSION_RESPONSE" | jq . > /dev/null 2>&1; then
    SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.id')
    print_success "Created session with ID: $SESSION_ID"
else
    print_error "Failed to create session"
fi
echo ""

echo "Test 9: Check-In Child"
echo "----------------------"
CHECKIN_DATA="{
    \"child\": \"$CHILD_ID\",
    \"session\": \"$SESSION_ID\"
}"
CHECKIN_RESPONSE=$(curl -s -b $COOKIES_FILE -c $COOKIES_FILE \
    -X POST $BASE_URL/api/checkins/check_in/ \
    -H "X-CSRFToken: $CSRF_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$CHECKIN_DATA")

if echo "$CHECKIN_RESPONSE" | jq . > /dev/null 2>&1; then
    CHECKIN_ID=$(echo "$CHECKIN_RESPONSE" | jq -r '.id')
    print_success "Checked in child, record ID: $CHECKIN_ID"
else
    print_error "Failed to check in child"
    echo "$CHECKIN_RESPONSE"
fi
echo ""

echo "Test 10: Verify QR Token Generated"
echo "-----------------------------------"
CHILD_AFTER_CHECKIN=$(curl -s -b $COOKIES_FILE $BASE_URL/api/children/$CHILD_ID/)
QR_TOKEN=$(echo "$CHILD_AFTER_CHECKIN" | jq -r '.qr_token')

if [ "$QR_TOKEN" != "null" ] && [ -n "$QR_TOKEN" ]; then
    print_success "QR token generated: ${QR_TOKEN:0:10}..."
else
    print_error "QR token was not generated on check-in"
fi
echo ""

echo "Test 11: Test Double Check-In Prevention"
echo "-----------------------------------------"
DOUBLE_CHECKIN=$(curl -s -w "%{http_code}" -o /tmp/double_checkin.json \
    -b $COOKIES_FILE -c $COOKIES_FILE \
    -X POST $BASE_URL/api/checkins/check_in/ \
    -H "X-CSRFToken: $CSRF_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$CHECKIN_DATA")

if [ "$DOUBLE_CHECKIN" = "400" ]; then
    ERROR_MSG=$(jq -r '.error' < /tmp/double_checkin.json)
    print_success "Double check-in prevented: $ERROR_MSG"
else
    print_error "Should have prevented double check-in (got status $DOUBLE_CHECKIN)"
fi
echo ""

echo "Test 12: Get Active Check-Ins"
echo "------------------------------"
ACTIVE_CHECKINS=$(curl -s -b $COOKIES_FILE $BASE_URL/api/checkins/active/)
ACTIVE_COUNT=$(echo "$ACTIVE_CHECKINS" | jq 'length')
if [ "$ACTIVE_COUNT" -gt 0 ]; then
    print_success "Found $ACTIVE_COUNT active check-in(s)"
else
    print_error "Expected at least 1 active check-in"
fi
echo ""

echo "Test 13: Public QR Endpoint (No Auth)"
echo "--------------------------------------"
if [ "$QR_TOKEN" != "null" ] && [ -n "$QR_TOKEN" ]; then
    QR_RESPONSE=$(curl -s $BASE_URL/qr/$QR_TOKEN/)

    if echo "$QR_RESPONSE" | jq . > /dev/null 2>&1; then
        CHILD_NAME=$(echo "$QR_RESPONSE" | jq -r '.first_name')
        IS_CHECKED_IN=$(echo "$QR_RESPONSE" | jq -r '.is_checked_in')

        print_success "QR endpoint returned data for: $CHILD_NAME"

        if [ "$IS_CHECKED_IN" = "true" ]; then
            SESSION_NAME=$(echo "$QR_RESPONSE" | jq -r '.current_session.name')
            print_success "Child is checked in to: $SESSION_NAME"
        else
            print_error "Child should be marked as checked in"
        fi
    else
        print_error "QR endpoint returned invalid JSON"
    fi
else
    print_error "Cannot test QR endpoint without valid token"
fi
echo ""

echo "Test 14: Check-Out Child"
echo "------------------------"
CHECKOUT_DATA='{"picked_up_by":"Test Parent"}'
CHECKOUT_RESPONSE=$(curl -s -b $COOKIES_FILE -c $COOKIES_FILE \
    -X POST $BASE_URL/api/checkins/$CHECKIN_ID/check_out/ \
    -H "X-CSRFToken: $CSRF_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$CHECKOUT_DATA")

if echo "$CHECKOUT_RESPONSE" | jq . > /dev/null 2>&1; then
    CHECKOUT_TIME=$(echo "$CHECKOUT_RESPONSE" | jq -r '.check_out_time')
    if [ "$CHECKOUT_TIME" != "null" ]; then
        print_success "Checked out child at: $CHECKOUT_TIME"
    else
        print_error "Check-out time is null"
    fi
else
    print_error "Failed to check out child"
fi
echo ""

echo "Test 15: Verify Audit Logs"
echo "---------------------------"
AUDIT_LOGS=$(curl -s -b $COOKIES_FILE $BASE_URL/api/audit-logs/)
AUDIT_COUNT=$(echo "$AUDIT_LOGS" | jq 'length')

if [ "$AUDIT_COUNT" -gt 0 ]; then
    print_success "Found $AUDIT_COUNT audit log entries"

    # Check for check-in action
    CHECKIN_LOGS=$(echo "$AUDIT_LOGS" | jq '[.[] | select(.action=="check_in")] | length')
    CHECKOUT_LOGS=$(echo "$AUDIT_LOGS" | jq '[.[] | select(.action=="check_out")] | length')

    print_info "Check-in logs: $CHECKIN_LOGS"
    print_info "Check-out logs: $CHECKOUT_LOGS"
else
    print_error "No audit logs found"
fi
echo ""

echo "========================================="
echo "Test Suite Complete!"
echo "========================================="
echo ""
print_info "Cleaning up test data..."
print_info "You can manually delete the test records from Django admin if needed."
print_info "Test family ID: $FAMILY_ID"
echo ""

# Clean up
rm -f $COOKIES_FILE /tmp/double_checkin.json

print_success "All tests completed!"
