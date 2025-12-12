.PHONY: help rebuild-dev rebuild-prod restart-dev restart-prod test test-e2e test-e2e-dev test-e2e-prod clean-docker

# Default target
help:
	@echo "Conference Check-In System - Main Commands"
	@echo ""
	@echo "Build & Restart Commands:"
	@echo "  make rebuild-dev       Trigger dev environment rebuild"
	@echo "  make rebuild-prod      Trigger production environment rebuild"
	@echo "  make restart-dev       Restart dev containers (hot reload should work)"
	@echo "  make restart-prod      Restart production containers"
	@echo ""
	@echo "Test Commands:"
	@echo "  make test              Run all tests (delegates to backend/)"
	@echo "  make test-e2e          Run E2E tests against dev"
	@echo "  make test-e2e-dev      Run E2E tests against dev"
	@echo "  make test-e2e-prod     Run E2E tests against production"
	@echo ""
	@echo "Docker Cleanup:"
	@echo "  make clean-docker      Clean up Docker/Podman resources"
	@echo ""
	@echo "Backend Test Commands:"
	@echo "  cd backend && make help    Show all backend-specific test commands"
	@echo ""
	@echo "Examples:"
	@echo "  make rebuild-prod && sleep 10 && make test-e2e-prod"
	@echo "  make restart-dev"
	@echo "  cd backend && make test-auth"

# Build and restart commands
rebuild-dev:
	@echo "Triggering development environment rebuild..."
	@echo "rebuild-$$(date +%s)" > restart.txt
	@echo "✓ Rebuild triggered - check build.dev.log for progress"
	@echo "  tail -f build.dev.log"

rebuild-prod:
	@echo "Triggering production environment rebuild..."
	@echo "rebuild-$$(date +%s)" > restart.txt
	@echo "✓ Rebuild triggered - check build.prod.log for progress"
	@echo "  tail -f build.prod.log"
	@echo ""
	@echo "⏳ Waiting for rebuild to complete (this may take 30-60 seconds)..."
	@echo "   You can run 'make test-e2e-prod' after the build completes"

restart-dev:
	@echo "Restarting development environment (hot reload)..."
	@echo "restart-$$(date +%s)" > restart.txt
	@echo "✓ Restart triggered"

restart-prod:
	@echo "Restarting production environment..."
	@echo "restart-$$(date +%s)" > restart.txt
	@echo "✓ Restart triggered"

# Test commands (delegate to backend Makefile)
test:
	@echo "Running all tests..."
	@cd backend && $(MAKE) test

test-e2e: test-e2e-dev

test-e2e-dev:
	@echo "Running E2E tests against development environment..."
	@cd backend && $(MAKE) test-e2e-dev

test-e2e-prod:
	@echo "Running E2E tests against production environment..."
	@cd backend && $(MAKE) test-e2e-prod

# Docker cleanup
clean-docker:
	@echo "Cleaning up Docker/Podman resources..."
	@echo "⚠️  This will remove unused containers, networks, images, and volumes"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		podman system prune -a --volumes || docker system prune -a --volumes; \
		echo "✓ Cleanup complete"; \
	else \
		echo "Cancelled"; \
	fi
