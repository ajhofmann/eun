.PHONY: install test lint typecheck smoke-moser smoke-zeta5 baseline sweep clean

install:
	uv sync --all-extras --dev

test:
	uv run pytest -q

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

typecheck:
	uv run mypy src

smoke-moser:
	uv run eud generate --family moser --coeff-bound 2 \
		--out data/candidates/moser_box_B2.json
	uv run eud verify data/candidates/moser_box_B2.json

smoke-zeta5:
	uv run eud generate --family zeta5 --R 2.5 --coeff-bound 6 \
		--out data/candidates/zeta5_R2.5.json

baseline:
	uv run eud baseline --n-max 1000 --out data/frontiers/baseline.jsonl

sweep:
	uv run eud search configs/search/biquadratic_rank6.yaml

leaderboard:
	uv run eud leaderboard

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} +
