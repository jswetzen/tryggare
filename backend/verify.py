#!/usr/bin/env python
"""Complete backend verification - run this before committing"""
import os
import sys

# Setup paths
backend_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_path)

print("=" * 60)
print("FULL BACKEND VERIFICATION")
print("=" * 60)
print()

# Run model tests
print("PART 1: MODEL TESTS")
print("-" * 60)
print()
try:
    exec(open(os.path.join(backend_path, 'test_models.py')).read())
except Exception as e:
    print(f"✗ Model tests failed: {e}")
    sys.exit(1)

print()
print("=" * 60)
print()

# Run API tests
print("PART 2: API TESTS")
print("-" * 60)
print()
try:
    exec(open(os.path.join(backend_path, 'test_api.py')).read())
except Exception as e:
    print(f"✗ API tests failed: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("✅ ALL VERIFICATIONS PASSED!")
print("=" * 60)
print()
print("Backend is ready to:")
print("  ✓ Commit to git")
print("  ✓ Deploy to production")
print("  ✓ Integrate with frontend")
print()
