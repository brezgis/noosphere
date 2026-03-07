.PHONY: test test-quick

test:
	python3 -m pytest tests/ -v --tb=short

test-quick:
	python3 -m pytest tests/ -v --tb=short -x -q
