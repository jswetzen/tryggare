#!/bin/bash
#
# Comprehensive Verification Script for Check-Ins System
#
# This script replaces restart.sh with a complete verification workflow:
# 1. Triggers server restart via restart.txt
# 2. Monitors web.log for restart completion
# 3. Optionally runs Selenium E2E tests
# 4. Provides clear feedback at each step
#
# Usage:
#   ./verification.sh                    # Just restart and verify
#   ./verification.sh --test             # Restart and run all tests
#   ./verification.sh --test <file>      # Restart and run specific test
#   ./verification.sh --no-restart --test # Skip restart, just run tests
#   ./verification.sh --timeout 60       # Custom timeout in seconds
#   ./verification.sh --help             # Show help

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default configuration
TIMEOUT=60
RUN_TESTS=false
SKIP_RESTART=false
TEST_FILE=""
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
WEB_LOG="$PROJECT_ROOT/web.log"
FRONTEND_LOG="$PROJECT_ROOT/frontend.log"
RESTART_FILE="$PROJECT_ROOT/restart.txt"
BUILD_LOG="$PROJECT_ROOT/build.log"
COMPOSE_BUILD_TIMEOUT=300  # 5 minutes for build to complete

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --test)
      RUN_TESTS=true
      if [[ -n "$2" && ! "$2" =~ ^-- ]]; then
        TEST_FILE="$2"
        shift
      fi
      shift
      ;;
    --no-restart)
      SKIP_RESTART=true
      shift
      ;;
    --timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    --help|-h)
      echo "Comprehensive Verification Script for Check-Ins System"
      echo ""
      echo "Usage:"
      echo "  ./verification.sh                    # Just restart and verify"
      echo "  ./verification.sh --test             # Restart and run all tests"
      echo "  ./verification.sh --test <file>      # Restart and run specific test"
      echo "  ./verification.sh --no-restart --test # Skip restart, just run tests"
      echo "  ./verification.sh --rebuild --test   # Rebuild production + run tests"
      echo "  ./verification.sh --timeout 60       # Custom timeout in seconds"
      echo "  ./verification.sh --help             # Show this help"
      echo ""
      echo "Options:"
      echo "  --test [file]    Run Selenium tests after restart (optionally specify test file)"
      echo "  --no-restart     Skip the restart step (useful for running tests only)"
      echo "  --timeout N      Set restart wait timeout in seconds (default: 60)"
      echo "  --help, -h       Show this help message"
      echo ""
      echo "Examples:"
      echo "  ./verification.sh                              # Quick restart verification"
      echo "  ./verification.sh --test                       # Full restart + all tests"
      echo "  ./verification.sh --test test_selenium_full_flows.py  # Restart + specific test"
      echo "  ./verification.sh --no-restart --test          # Run tests without restarting"
      exit 0
      ;;
    *)
      echo -e "${RED}❌ Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Function to print colored messages
print_header() {
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${CYAN}$1${NC}"
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_step() {
  echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
  echo -e "${RED}❌ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
  echo -e "${CYAN}ℹ️  $1${NC}"
}

# Function to check if file exists
check_file() {
  if [[ ! -f "$1" ]]; then
    print_error "File not found: $1"
    exit 1
  fi
}

# Function to check disk space
check_disk_space() {
  print_step "Checking available disk space..."

  local available_space=$(df -BG "$PROJECT_ROOT" | tail -1 | awk '{print $4}' | sed 's/G//')
  local required_space=2  # Require at least 2GB free

  if [[ -z "$available_space" ]]; then
    print_warning "Could not determine available disk space"
    return 0
  fi

  print_info "Available disk space: ${available_space}GB"

  if [[ "$available_space" -lt "$required_space" ]]; then
    print_error "Insufficient disk space! Available: ${available_space}GB, Required: ${required_space}GB minimum"
    print_info "Please free up disk space before building"
    print_info "Common cleanup commands:"
    echo -e "${CYAN}   docker system prune -a${NC}"
    echo -e "${CYAN}   podman system prune -a${NC}"
    return 1
  fi

  print_success "Sufficient disk space available (${available_space}GB)"
  return 0
}

# Function to check build logs for errors
check_build_logs() {
  print_step "Checking build logs for errors..."

  if [[ ! -f "$BUILD_LOG" ]]; then
    print_warning "Build log not found at: $BUILD_LOG"
    print_info "Build logs are captured by the 'watch restart.txt' process"
    print_info "Check if the watcher is running and redirecting output to build.log"
    return 1
  fi

  # Check file size - if it's very large, only check recent entries
  local log_size=$(stat -f%z "$BUILD_LOG" 2>/dev/null || stat -c%s "$BUILD_LOG" 2>/dev/null || echo 0)
  local check_lines=500

  if [[ "$log_size" -gt 1000000 ]]; then
    print_info "Build log is large ($(numfmt --to=iec $log_size 2>/dev/null || echo ${log_size} bytes)), checking last ${check_lines} lines"
  fi

  # Get the last portion of the build log
  local recent_log=$(tail -n $check_lines "$BUILD_LOG")

  # Check for critical build errors
  local build_errors=$(echo "$recent_log" | grep -iE "ERROR|FAILED|no space left|Build command failed|build.*error" || true)

  if [[ -n "$build_errors" ]]; then
    print_error "Build errors detected in build.log!"
    echo ""
    print_info "Recent build errors:"
    echo "$build_errors" | tail -n 20 | sed 's/^/   /'
    echo ""

    # Check for specific common errors
    if echo "$build_errors" | grep -q "no space left"; then
      print_error "DISK SPACE ERROR: No space left on device"
      print_info "Action required: Free up disk space and rebuild"
      print_info "Cleanup commands:"
      echo -e "${CYAN}   docker system prune -a${NC}"
      echo -e "${CYAN}   podman system prune -a${NC}"
    fi

    if echo "$build_errors" | grep -q "Build command failed"; then
      print_error "BUILD FAILED: Docker/Podman build command failed"
      print_info "Check the full build log: less $BUILD_LOG"
    fi

    return 1
  fi

  # Check for successful build completion
  local build_success=$(echo "$recent_log" | grep -iE "Successfully built|Build complete|up-to-date" || true)

  if [[ -n "$build_success" ]]; then
    print_success "Build completed successfully"
    echo -e "${CYAN}   Last build message: $(echo "$build_success" | tail -n 1 | sed 's/^[[:space:]]*//')${NC}"
    return 0
  fi

  print_warning "Could not verify build status from logs"
  print_info "Build may still be in progress or logs may not be captured"
  print_info "Check: tail -f $BUILD_LOG"
  return 0  # Don't fail, just warn
}

# Function to trigger restart
trigger_restart() {
  print_step "Triggering server restart..."

  # Record timestamp before restart
  local before_timestamp=$(stat -c %Y "$WEB_LOG" 2>/dev/null || echo 0)

  # Touch restart.txt to trigger restart
  date > "$RESTART_FILE"

  print_success "Restart triggered at $(date '+%H:%M:%S')"
  echo -e "${CYAN}   Wrote timestamp to: $RESTART_FILE${NC}"

  # Wait a moment for container to detect change
  sleep 2
}

# Function to wait for restart completion
wait_for_restart() {
  print_step "Waiting for server restart to complete..."

  local elapsed=0
  local found_restart=false
  local log_position=$(wc -l < "$WEB_LOG" 2>/dev/null || echo 0)

  # Progress indicator
  echo -n "   "

  while [[ $elapsed -lt $TIMEOUT ]]; do
    # Check new log lines
    if [[ -f "$WEB_LOG" ]]; then
      local new_lines=$(tail -n +$log_position "$WEB_LOG" 2>/dev/null | grep -i "listening\|starting\|spawned" || true)

      if [[ -n "$new_lines" ]]; then
        found_restart=true
        echo ""
        print_success "Server restart completed after ${elapsed}s"
        echo -e "${CYAN}   Last log entry:${NC}"
        echo "$new_lines" | tail -n 1 | sed 's/^/   /'
        return 0
      fi
    fi

    # Progress indicator (dot every 2 seconds)
    if [[ $((elapsed % 2)) -eq 0 ]]; then
      echo -n "."
    fi

    sleep 1
    ((elapsed++))
  done

  echo ""
  print_warning "Timeout after ${TIMEOUT}s waiting for restart"
  print_info "Server may still be restarting. Check logs manually:"
  echo -e "${CYAN}   tail -f $WEB_LOG${NC}"
  return 1
}

# Function to verify server health
verify_server_health() {
  print_step "Verifying server health..."

  # Check for recent errors in web.log (only after "Starting daphne" line)
  local recent_backend=$(tail -n 50 "$WEB_LOG" | tac | sed -n '/Starting daphne/,$p' | tac)
  local backend_errors=$(echo "$recent_backend" | grep -i "error\|exception\|traceback" || true)

  if [[ -n "$backend_errors" ]]; then
    print_warning "Found errors in web.log after restart:"
    echo "$backend_errors" | tail -n 10 | sed 's/^/   /'
    return 1
  fi

  # Check frontend.log if it exists (only recent entries - last 20 lines)
  if [[ -f "$FRONTEND_LOG" ]]; then
    # Look for actual errors (SEVERE or ERROR level), not old warnings
    local frontend_errors=$(tail -n 20 "$FRONTEND_LOG" | grep -iE "error.*vite|failed.*build|exception" || true)
    if [[ -n "$frontend_errors" ]]; then
      print_warning "Found errors in frontend.log:"
      echo "$frontend_errors" | tail -n 10 | sed 's/^/   /'
      return 1
    fi
  fi

  print_success "No errors found in recent logs"
  return 0
}

# Function to show log summary
show_log_summary() {
  print_step "Recent log summary:"
  echo ""

  echo -e "${CYAN}Backend (web.log):${NC}"
  if [[ -f "$WEB_LOG" ]]; then
    tail -n 5 "$WEB_LOG" | sed 's/^/   /'
  else
    echo "   (log file not found)"
  fi

  echo ""
  echo -e "${CYAN}Frontend (frontend.log):${NC}"
  if [[ -f "$FRONTEND_LOG" ]]; then
    tail -n 5 "$FRONTEND_LOG" | sed 's/^/   /'
  else
    echo "   (log file not found)"
  fi
}

# Function to run Django backend tests
run_django_tests() {
  print_header "Running Django Backend Tests"

  cd "$PROJECT_ROOT/backend"

  echo ""
  print_step "Installing test dependencies..."
  uv sync --group test > /dev/null 2>&1

  echo ""
  print_step "Executing Django tests..."
  echo ""

  # Run Django test suite with --keepdb to reuse existing test database
  # Only test Django apps (checkins, families, etc.), not standalone test scripts
  set +e
  uv run python manage.py test --keepdb checkins families accounts events printing
  local test_exit_code=$?
  set -e

  echo ""

  if [[ $test_exit_code -eq 0 ]]; then
    print_success "Django backend tests passed!"
    return 0
  else
    print_error "Django tests failed with exit code: $test_exit_code"
    return $test_exit_code
  fi
}

# Function to run Selenium tests
run_selenium_tests() {
  print_header "Running Selenium E2E Tests"

  cd "$PROJECT_ROOT/backend"

  # Check if test file exists (if specified)
  if [[ -n "$TEST_FILE" ]]; then
    if [[ ! -f "$TEST_FILE" ]]; then
      print_error "Test file not found: $TEST_FILE"
      exit 1
    fi
    print_info "Running specific test: $TEST_FILE"
    TEST_CMD="uv run python $TEST_FILE"
  else
    print_info "Running all Selenium tests: test_selenium_full_flows.py + test_qr_page_e2e.py"
    TEST_CMD="uv run python test_selenium_full_flows.py && uv run python test_qr_page_e2e.py"
  fi

  echo ""
  print_step "Installing test dependencies..."
  uv sync --group test > /dev/null 2>&1

  echo ""
  print_step "Executing tests..."
  echo ""

  # Set default URLs for tests if not already set
  # Use port 8080 as the reverse proxy default (both backend and frontend accessible there)
  export FRONTEND_URL="${FRONTEND_URL:-http://localhost:8080}"
  export BACKEND_URL="${BACKEND_URL:-http://localhost:8080}"

  print_info "Test URLs:"
  echo -e "${CYAN}   Frontend: $FRONTEND_URL${NC}"
  echo -e "${CYAN}   Backend:  $BACKEND_URL${NC}"
  echo ""

  # Run tests and capture exit code
  set +e
  eval $TEST_CMD
  local test_exit_code=$?
  set -e

  echo ""

  if [[ $test_exit_code -eq 0 ]]; then
    print_success "Selenium E2E tests passed!"
    return 0
  else
    print_error "Tests failed with exit code: $test_exit_code"
    print_info "Check screenshots in /tmp/ for failure details"
    return $test_exit_code
  fi
}

# Function to run all tests
run_tests() {
  local overall_exit_code=0

  # Run Django backend tests first
  if ! run_django_tests; then
    overall_exit_code=1
    print_error "Django backend tests failed - skipping E2E tests"
    return $overall_exit_code
  fi

  echo ""

  # If Django tests passed, run Selenium E2E tests (unless a specific test file was provided)
  if [[ -z "$TEST_FILE" ]]; then
    if ! run_selenium_tests; then
      overall_exit_code=1
    fi
  else
    # If specific test file provided, only run that
    if ! run_selenium_tests; then
      overall_exit_code=1
    fi
  fi

  return $overall_exit_code
}

# Main execution
main() {
  print_header "🔍 Check-Ins System Verification"

  echo ""
  print_info "Configuration:"
  echo -e "${CYAN}   Project Root: $PROJECT_ROOT${NC}"
  echo -e "${CYAN}   Timeout:      ${TIMEOUT}s${NC}"
  echo -e "${CYAN}   Run Tests:    $RUN_TESTS${NC}"
  echo -e "${CYAN}   Skip Restart: $SKIP_RESTART${NC}"
  if [[ -n "$TEST_FILE" ]]; then
    echo -e "${CYAN}   Test File:    $TEST_FILE${NC}"
  fi
  echo ""

  # Step 0: Check build logs and disk space
  echo ""
  print_header "🔧 Pre-Flight Checks"
  echo ""

  # Check disk space first
  if ! check_disk_space; then
    print_error "Pre-flight checks failed: insufficient disk space"
    exit 1
  fi

  echo ""

  # Check build logs for any errors from previous builds
  if ! check_build_logs; then
    print_warning "Build log check failed - there may be build errors"
    print_info "Review the build log before proceeding: less $BUILD_LOG"

    if [[ "$RUN_TESTS" == true ]]; then
      print_warning "Proceeding with tests, but be aware build may have failed"
    else
      print_error "Fix build errors before running verification"
      echo ""
      print_info "To fix build errors:"
      echo -e "${CYAN}   1. Check build log: less $BUILD_LOG${NC}"
      echo -e "${CYAN}   2. Free up disk space if needed: podman system prune -a${NC}"
      echo -e "${CYAN}   3. Trigger rebuild: touch $RESTART_FILE${NC}"
      echo -e "${CYAN}   4. Monitor rebuild: tail -f $BUILD_LOG${NC}"
      exit 1
    fi
  fi

  # Step 1: Restart server (unless skipped)
  if [[ "$SKIP_RESTART" == false ]]; then
    trigger_restart

    if ! wait_for_restart; then
      print_error "Restart verification failed"
      exit 1
    fi

    echo ""

    # Verify server health
    if ! verify_server_health; then
      print_warning "Server restarted but errors were found in logs"
      show_log_summary

      if [[ "$RUN_TESTS" == true ]]; then
        print_warning "Proceeding with tests despite errors..."
      else
        exit 1
      fi
    else
      print_success "Server is healthy"
    fi

    echo ""
    show_log_summary
  else
    print_info "Skipping restart as requested"
  fi

  # Step 2: Run tests (if requested)
  if [[ "$RUN_TESTS" == true ]]; then
    echo ""

    if ! run_tests; then
      exit 1
    fi
  fi

  # Final summary
  echo ""
  print_header "✅ Verification Complete"

  if [[ "$SKIP_RESTART" == false ]]; then
    print_success "Server restarted and verified"
  fi

  if [[ "$RUN_TESTS" == true ]]; then
    print_success "All tests passed"
  fi

  echo ""
  print_info "Next steps:"
  if [[ "$RUN_TESTS" == false ]]; then
    echo -e "${CYAN}   - Run tests: ./verification.sh --test${NC}"
  fi
  echo -e "${CYAN}   - Monitor logs: tail -f web.log${NC}"
  echo -e "${CYAN}   - Access dev server: http://localhost:5173${NC}"
  echo -e "${CYAN}   - Access API: http://localhost:8000${NC}"
  echo ""
}

# Run main function
main

exit 0
