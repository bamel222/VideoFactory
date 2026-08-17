.PHONY: install backend frontend dev test lint docker-dev docker-deploy seed docs

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

backend:
	cd backend && uvicorn app.main:app --reload --port 3001

frontend:
	cd frontend && npm run dev

dev:
	./start.sh

test:
	cd backend && python -m pytest tests -q
	cd frontend && npm test -- --watch=false

lint:
	cd backend && python -m pytest --disable-warnings -q

docker-dev:
	docker compose -f infra/docker-compose.dev.yml up

docker-deploy:
	docker compose -f infra/docker-compose.deploy.yml up -d --build

seed:
	cd backend && python -m app.scripts.seed

docs:
	cd docs && python -m spec
