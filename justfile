dev:
    docker compose -f infra/docker-compose.yml up

build:
    docker compose -f infra/docker-compose.yml build

test: test-back test-front

test-back:
    cd backend && uv run pytest tests/

test-front:
    cd frontend && npm run test

lint: lint-back lint-front

lint-back:
    cd backend && uv run ruff check . && uv run ruff format --check . && uv run pyright

lint-front:
    cd frontend && npm run lint

eval:
    cd backend && uv run python ../evals/eval_runner.py

k8s-apply:
    kubectl apply -f infra/k8s/

format:
    cd backend && uv run ruff format .

install:
    cd backend && uv sync

clean:
    find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
    find . -type d -name ".pytest_cache" -not -path "./.venv/*" -exec rm -rf {} +
    find . -type f -name "*.pyc" -not -path "./.venv/*" -delete
