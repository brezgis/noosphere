.PHONY: test test-quick test-full

test: test-quick

test-quick:
	python3 -m pytest tests/ -v --tb=short -x -q

test-full:
	python3 -m pytest tests/ -v --tb=short
	npx playwright test
