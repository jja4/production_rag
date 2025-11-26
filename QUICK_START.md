# ⚡ Quick Start Guide - 5 Minutes to Running

Get your production_rag system running in Docker in under 5 minutes!

## 🚀 Super Quick Start

```bash
# 1. Clone and setup
git clone <your-repo>
cd production_rag

# 2. Create environment file
cp .env.example .env

# 3. Start all services
make start

# 4. Wait for services to be ready (30-60 seconds)
# 5. Check health
make health

# 6. Access services
curl http://localhost:8000/docs  # API docs
open http://localhost:7861       # Gradio UI (macOS)
open http://localhost:8080       # Airflow
```

**That's it!** Your RAG system is running. 🎉

---

## 📋 What Gets Started

| Service | URL | Purpose |
|---------|-----|---------|
| **API** | http://localhost:8000 | FastAPI backend |
| **Gradio UI** | http://localhost:7861 | Chat interface |
| **Airflow** | http://localhost:8080 | Data ingestion |
| **OpenSearch** | http://localhost:5601 | Search dashboard |
| **Langfuse** | http://localhost:3000 | Monitoring (Week 6) |

---

## ⚙️ Configuration (If Needed)

### Minimal Setup
```bash
# Your .env file needs these ONLY:
POSTGRES_DATABASE_URL=postgresql+psycopg2://rag_user:rag_password@postgres:5432/rag_db
OPENSEARCH_HOST=http://opensearch:9200
OLLAMA_HOST=http://ollama:11434

# The rest has reasonable defaults from .env.example
```

### For Week 4+ (Hybrid Search)
Add to `.env`:
```bash
JINA_API_KEY=your-api-key-here
```

### For Week 6 (Monitoring)
Add to `.env`:
```bash
LANGFUSE__PUBLIC_KEY=pk-lf-xxxx
LANGFUSE__SECRET_KEY=sk-lf-xxxx
```

---

## 🧪 Quick Tests

```bash
# Test API is working
curl http://localhost:8000/api/v1/health

# Test search (after ingesting papers)
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "max_results": 1}'

# Test RAG (after ingesting papers)
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 1}'
```

---

## 📊 Useful Commands

```bash
# View status
make status

# Check health
make health

# View logs (all)
make logs

# View logs (specific)
make logs-api
make logs-postgres
make logs-opensearch

# Stop services
make stop

# Restart services
make restart

# Reset everything
make reset

# See all available commands
make help
```

---

## 🔗 Environment Variables

All variables in `compose.yml` **automatically map** to Docker container hostnames:

```
POSTGRES_DATABASE_URL=postgresql+psycopg2://postgres:5432  ← Uses postgres container
OPENSEARCH_HOST=http://opensearch:9200                      ← Uses opensearch container
OLLAMA_HOST=http://ollama:11434                             ← Uses ollama container
```

**Don't use localhost** - Docker containers communicate via hostnames!

---

## ✅ First Time Checklist

After running `make start`:

- [ ] All services show "Up": `make status`
- [ ] All services are "healthy": `make health`
- [ ] API responds: `curl http://localhost:8000/api/v1/health`
- [ ] Can access docs: http://localhost:8000/docs

---

## 🆘 Common Issues

| Issue | Fix |
|-------|-----|
| Services not starting | Wait 30-60 seconds, then `make health` |
| Port already in use | `lsof -i :8000` then `kill -9 [PID]` |
| Database connection failed | Check `.env`, wait for PostgreSQL |
| Out of memory | Increase Docker memory to 8GB+ |
| Services keep restarting | Check `make logs` for errors |

**Full troubleshooting**: See `DOCKER_TROUBLESHOOTING.md`

---

## 🎯 Next Steps

1. **Ingest Papers** - Run Airflow DAG at http://localhost:8080
2. **Test Search** - Use API at http://localhost:8000/docs
3. **Learn the System** - Follow notebooks in `notebooks/week1/`
4. **Explore Features** - Week 2 (ingestion), Week 3 (search), Week 4+ (RAG)

---

## 📚 Full Documentation
- **Quick Start**: `QUICK_START.md` - This guide
- **Project**: `README.md` - Full learning path

---

**You're all set!** Start with `make start` and explore at http://localhost:8000/docs 🚀
