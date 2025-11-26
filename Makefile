.PHONY: help start stop restart status logs health setup format lint test test-cov clean docker-help api-logs shell db-query

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ============================================
# Docker Service Management
# ============================================
start: ## Start all services (with rebuild)
	docker compose up --build -d
	@sleep 5
	@$(MAKE) status

start-quick: ## Quick start (no rebuild)
	docker compose up -d
	@sleep 3
	@$(MAKE) status

stop: ## Stop all services
	docker compose stop

restart: ## Restart all services
	docker compose restart
	@sleep 2
	@$(MAKE) status

status: ## Show service status
	@docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"

logs: ## Show service logs (Ctrl+C to exit)
	docker compose logs -f --tail=50

logs-api: ## Show API service logs
	docker compose logs -f --tail=100 api

logs-postgres: ## Show PostgreSQL logs
	docker compose logs -f --tail=50 postgres

logs-opensearch: ## Show OpenSearch logs
	docker compose logs -f --tail=50 opensearch

logs-airflow: ## Show Airflow logs
	docker compose logs -f --tail=50 airflow

# ============================================
# Health & Monitoring
# ============================================
health: ## Check all services health
	@echo "🏥 Service Health Check:"
	@echo "API Health:"; curl -s http://localhost:8000/api/v1/health | jq . || echo "❌ Not responding"
	@echo ""
	@echo "PostgreSQL:"; docker exec rag-postgres pg_isready -U rag_user && echo "✅ OK" || echo "❌ Failed"
	@echo ""
	@echo "OpenSearch:"; docker exec rag-opensearch curl -s http://localhost:9200/_cluster/health | jq .status || echo "❌ Failed"
	@echo ""
	@echo "Redis:"; docker exec rag-redis redis-cli ping || echo "❌ Failed"
	@echo ""
	@echo "Ollama:"; docker exec rag-ollama ollama list > /dev/null && echo "✅ OK" || echo "❌ Failed"

stats: ## Show resource usage (live, Ctrl+C to exit)
	docker stats

# ============================================
# Shell Access
# ============================================
shell-api: ## Enter API container shell
	docker exec -it rag-api bash

shell-postgres: ## Enter PostgreSQL interactive shell
	docker exec -it rag-postgres psql -U rag_user -d rag_db

shell-redis: ## Enter Redis interactive shell
	docker exec -it rag-redis redis-cli

shell-python: ## Enter Python shell in API container
	docker exec -it rag-api python

# ============================================
# Database Operations
# ============================================
db-list: ## List papers in database
	@echo "📚 Papers in Database:"
	@docker exec rag-postgres psql -U rag_user -d rag_db -c "SELECT COUNT(*) as total_papers FROM papers;"
	@echo ""
	@echo "Recent Papers:"
	@docker exec rag-postgres psql -U rag_user -d rag_db -c "SELECT id, title FROM papers ORDER BY created_at DESC LIMIT 5;" 2>/dev/null || echo "No papers yet"

db-count: ## Count papers in database
	docker exec rag-postgres psql -U rag_user -d rag_db -c "SELECT COUNT(*) as total FROM papers;"

db-query: ## Run a SQL query (use: make db-query QUERY="SELECT * FROM papers LIMIT 5;")
	docker exec rag-postgres psql -U rag_user -d rag_db -c "$(QUERY)"

db-backup: ## Backup database
	@echo "💾 Backing up database..."
	@docker exec rag-postgres pg_dump -U rag_user -d rag_db > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup complete"

# ============================================
# Cache Operations
# ============================================
cache-list: ## List cache keys
	docker exec rag-redis redis-cli KEYS "*"

cache-stats: ## Show cache statistics
	docker exec rag-redis redis-cli INFO stats

cache-clear: ## Clear all cache
	@echo "🗑️  Clearing cache..."
	@docker exec rag-redis redis-cli FLUSHDB
	@echo "✅ Cache cleared"

# ============================================
# API Testing
# ============================================
test-health: ## Test API health endpoint
	@echo "Testing API health..."
	curl -s http://localhost:8000/api/v1/health | jq .

test-search: ## Test search endpoint
	@echo "Testing search..."
	curl -s -X POST http://localhost:8000/api/v1/search \
		-H "Content-Type: application/json" \
		-d '{"query": "neural networks", "max_results": 3}' | jq .

test-ask: ## Test RAG ask endpoint
	@echo "Testing RAG ask..."
	curl -s -X POST http://localhost:8000/api/v1/ask \
		-H "Content-Type: application/json" \
		-d '{"query": "What are transformers?", "top_k": 3}' | jq .

# ============================================
# Development
# ============================================
setup: ## Install Python dependencies
	uv sync

format: ## Format code
	uv run ruff format

lint: ## Lint and type check
	uv run ruff check --fix
	uv run mypy src/ --ignore-missing-imports

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov=src --cov-report=html --cov-report=term

# ============================================
# Cleanup
# ============================================
down: ## Take down all services (keep data)
	docker compose down

reset: ## ⚠️ Reset everything (delete all data!)
	@echo "⚠️  This will delete all data!"
	@read -p "Are you sure? (yes/no) " -n 3 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy][Ee][Ss]$$ ]]; then \
		docker compose down -v; \
		docker compose up --build -d; \
		echo "✅ Reset complete"; \
		sleep 5; \
		$(MAKE) status; \
	else \
		echo "Reset cancelled"; \
	fi

clean: ## Clean up unused Docker resources
	@echo "🧹 Cleaning up..."
	docker system prune -f
	@echo "✅ Cleanup complete"

# ============================================
# Useful Links
# ============================================
urls: ## Show service URLs
	@echo ""
	@echo "🌐 Service URLs:"
	@echo "API Documentation       http://localhost:8000/docs"
	@echo "Gradio Chat UI          http://localhost:7861"
	@echo "Airflow Dashboard       http://localhost:8080"
	@echo "OpenSearch Dashboards   http://localhost:5601"
	@echo "Langfuse Monitoring     http://localhost:3000"
	@echo ""

docker-help: ## Show Docker-specific help
	@echo ""
	@echo "🐳 Docker Command Examples:"
	@echo ""
	@echo "Start/Stop:"
	@echo "  make start           # Start all services"
	@echo "  make stop            # Stop all services"
	@echo "  make restart         # Restart all services"
	@echo ""
	@echo "Monitoring:"
	@echo "  make status          # Show service status"
	@echo "  make health          # Check service health"
	@echo "  make logs            # View all logs"
	@echo "  make logs-api        # View API logs"
	@echo "  make stats           # Live resource usage"
	@echo ""
	@echo "Database:"
	@echo "  make db-list         # List papers"
	@echo "  make db-count        # Count papers"
	@echo "  make db-backup       # Backup database"
	@echo "  make shell-postgres  # Access PostgreSQL"
	@echo ""
	@echo "Testing:"
	@echo "  make test-health     # Test API health"
	@echo "  make test-search     # Test search"
	@echo "  make test-ask        # Test RAG"
	@echo ""
	@echo "Access:"
	@echo "  make shell-api       # Enter API container"
	@echo "  make shell-postgres  # Enter PostgreSQL"
	@echo "  make urls            # Show service URLs"
	@echo ""