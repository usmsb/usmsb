# USMSB SDK - Docker Build and Management Commands

.PHONY: help build build-frontend build-backend dev prod up down logs clean test

# Default target
help:
	@echo "USMSB SDK Docker Commands"
	@echo "=========================="
	@echo ""
	@echo "Production:"
	@echo "  make build          - Build all production images"
	@echo "  make build-frontend - Build frontend image only"
	@echo "  make build-backend  - Build backend image only"
	@echo "  make prod           - Start production stack"
	@echo "  make prod-stop      - Stop production stack"
	@echo ""
	@echo "Development:"
	@echo "  make dev            - Start development stack with hot-reload"
	@echo "  make dev-stop       - Stop development stack"
	@echo "  make dev-logs       - View development logs"
	@echo ""
	@echo "Utilities:"
	@echo "  make down           - Stop all containers"
	@echo "  make logs           - View all logs"
	@echo "  make clean          - Remove all containers and volumes"
	@echo "  make test           - Run tests"
	@echo "  make shell-backend  - Open shell in backend container"
	@echo "  make shell-frontend - Open shell in frontend container"

# Production builds
build: build-frontend build-backend
	@echo "All images built successfully!"

build-frontend:
	docker build -f frontend/Dockerfile -t usmsb/frontend:latest ./frontend
	@echo "Frontend image built: usmsb/frontend:latest"

build-backend:
	docker build -f Dockerfile --target backend -t usmsb/backend:latest .
	@echo "Backend image built: usmsb/backend:latest"

build-full-node:
	docker build -f Dockerfile --target full-node -t usmsb/full-node:latest .
	@echo "Full node image built: usmsb/full-node:latest"

# Production deployment
prod:
	docker-compose up -d
	@echo "Production stack started!"
	@echo "Frontend: http://localhost"
	@echo "Backend API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

prod-stop:
	docker-compose down

# Development deployment
dev:
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Development stack started!"
	@echo "Frontend: http://localhost:5173"
	@echo "Backend API: http://localhost:8000"

dev-stop:
	docker-compose -f docker-compose.dev.yml down

dev-logs:
	docker-compose -f docker-compose.dev.yml logs -f

# Distributed mode (separate frontend/backend)
distributed:
	docker-compose --profile distributed up -d
	@echo "Distributed stack started!"

distributed-stop:
	docker-compose --profile distributed down

# With monitoring stack
monitoring:
	docker-compose --profile monitoring up -d
	@echo "Monitoring stack started!"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000"

# With IPFS storage
storage:
	docker-compose --profile storage up -d
	@echo "Storage stack started!"
	@echo "IPFS API: http://localhost:5001"
	@echo "IPFS Gateway: http://localhost:8081"

# With Ethereum node
ethereum:
	docker-compose --profile ethereum up -d
	@echo "Ethereum node started!"
	@echo "RPC: http://localhost:8545"
	@echo "WebSocket: http://localhost:8546"

# Utilities
down:
	docker-compose down
	docker-compose -f docker-compose.dev.yml down

logs:
	docker-compose logs -f

clean: down
	docker-compose down -v
	docker-compose -f docker-compose.dev.yml down -v
	docker system prune -f
	@echo "Cleaned up all containers and volumes!"

test:
	docker build -f Dockerfile --target backend -t usmsb/backend:test .
	docker run --rm usmsb/backend:test pytest

shell-backend:
	docker exec -it usmsb-backend /bin/bash

shell-frontend:
	docker exec -it usmsb-frontend /bin/sh

# Quick start
quickstart: build prod
	@echo ""
	@echo "====================================="
	@echo "  USMSB SDK is running!"
	@echo "====================================="
	@echo "  Frontend: http://localhost"
	@echo "  API:      http://localhost:8000"
	@echo "  Docs:     http://localhost:8000/docs"
	@echo "====================================="
