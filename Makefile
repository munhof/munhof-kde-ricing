.PHONY: test lint doctor plan dry-run

test:
	python -m pytest -q

lint:
	ruff check src tests

doctor:
	python -m plasma_rice doctor

plan:
	python -m plasma_rice plan

dry-run:
	python -m plasma_rice apply --dry-run
