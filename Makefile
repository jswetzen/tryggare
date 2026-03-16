.PHONY: help rebuild-dev rebuild-prod restart-dev restart-prod test test-e2e test-e2e-dev test-e2e-prod clean-docker status ping wait-dev wait-prod

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
	@echo "Status Commands:"
	@echo "  make status            Show health of all environments"
	@echo "  make ping              Alias for status"
	@echo "  make wait-dev          Wait until dev environment is ready"
	@echo "  make wait-prod         Wait until prod environment is ready"
	@echo ""
	@echo "Docker Cleanup:"
	@echo "  make clean-docker      Clean up Docker/Podman resources"
	@echo ""
	@echo "Backend Test Commands:"
	@echo "  cd backend && make help    Show all backend-specific test commands"
	@echo ""
	@echo "Examples:"
	@echo "  make rebuild-prod && make wait-prod && make test-e2e-prod"
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
	@echo "   Run: make wait-prod && make test-e2e-prod"

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

# Status and health checks
status:
	@echo "=== Environment Status ==="
	@curl -s -o /dev/null -w "Dev frontend  (5173): %{http_code}\n" http://localhost:5173/ || echo "Dev frontend  (5173): UNREACHABLE"
	@curl -s -o /dev/null -w "Dev backend   (8000): %{http_code}\n" http://localhost:8000/api/auth/check/ || echo "Dev backend   (8000): UNREACHABLE"
	@curl -s -o /dev/null -w "Prod          (8080): %{http_code}\n" http://localhost:8080/api/auth/check/ || echo "Prod          (8080): UNREACHABLE"

ping: status

wait-dev:
	@echo "Waiting for dev environment..."
	@for i in $$(seq 1 30); do \
		if curl -s http://localhost:5173/ > /dev/null 2>&1 && \
		   curl -s http://localhost:8000/api/auth/check/ > /dev/null 2>&1; then \
			echo "✓ Dev environment ready"; exit 0; \
		fi; \
		echo "  ... ($$i/30)"; sleep 2; \
	done; echo "✗ Timeout waiting for dev environment"; exit 1

wait-prod:
	@echo "Waiting for prod environment..."
	@for i in $$(seq 1 30); do \
		if curl -s http://localhost:8080/api/auth/check/ > /dev/null 2>&1; then \
			echo "✓ Prod environment ready"; exit 0; \
		fi; \
		echo "  ... ($$i/30)"; sleep 2; \
	done; echo "✗ Timeout waiting for prod environment"; exit 1

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
