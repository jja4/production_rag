# OpenSearch index configuration for arXiv papers (BM25-focused)
# This module provides constants expected by the Week 3 notebook.

ARXIV_PAPERS_INDEX = "arxiv-papers"

# Minimal mapping suitable for BM25 full-text search and faceted filters.
ARXIV_PAPERS_MAPPING = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        }
    },
    "mappings": {
        "properties": {
            "arxiv_id": {"type": "keyword"},
            "title": {
                "type": "text",
                "analyzer": "standard",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
            },
            "abstract": {"type": "text", "analyzer": "standard"},
            "authors": {"type": "keyword"},
            "categories": {"type": "keyword"},
            "published_date": {"type": "date", "format": "yyyy-MM-dd||yyyy-MM-dd'T'HH:mm:ss||epoch_millis"},
            "pdf_url": {"type": "keyword"},
            "raw_text": {"type": "text", "analyzer": "standard"},
            "section_titles": {"type": "text", "analyzer": "standard"},
            "chunk_id": {"type": "keyword"}
        }
    }
}
