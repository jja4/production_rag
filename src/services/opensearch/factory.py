"""Unified factory for OpenSearch client."""

from functools import lru_cache
from typing import Optional

from src.config import Settings, get_settings

from .bm25_client import BM25OpenSearchClient
from .client import OpenSearchClient


@lru_cache(maxsize=1)
def make_opensearch_client(settings: Optional[Settings] = None) -> OpenSearchClient:
    """Factory function to create cached OpenSearch client (hybrid search).

    Uses lru_cache to maintain a singleton instance for efficiency.
    This creates the hybrid search client with chunking support.

    :param settings: Optional settings instance
    :returns: Cached OpenSearchClient instance
    """
    if settings is None:
        settings = get_settings()

    return OpenSearchClient(host=settings.opensearch.host, settings=settings)


@lru_cache(maxsize=1)
def make_bm25_client(settings: Optional[Settings] = None) -> BM25OpenSearchClient:
    """Factory function to create cached BM25 OpenSearch client (Week 3).

    Uses lru_cache to maintain a singleton instance for efficiency.
    This creates the simple BM25 client for keyword search only.

    :param settings: Optional settings instance
    :returns: Cached BM25OpenSearchClient instance
    """
    if settings is None:
        settings = get_settings()

    return BM25OpenSearchClient(host=settings.opensearch.host, settings=settings)


def make_opensearch_client_fresh(settings: Optional[Settings] = None, host: Optional[str] = None) -> OpenSearchClient:
    """Factory function to create a fresh OpenSearch client (not cached).

    Use this when you need a new client instance (e.g., for testing
    or when connection issues occur).

    :param settings: Optional settings instance
    :param host: Optional host override
    :returns: New OpenSearchClient instance
    """
    if settings is None:
        settings = get_settings()

    # Use provided host or settings host
    opensearch_host = host or settings.opensearch.host

    return OpenSearchClient(host=opensearch_host, settings=settings)


def make_bm25_client_fresh(settings: Optional[Settings] = None, host: Optional[str] = None) -> BM25OpenSearchClient:
    """Factory function to create a fresh BM25 OpenSearch client (not cached).

    Use this when you need a new client instance for BM25 search.

    :param settings: Optional settings instance
    :param host: Optional host override
    :returns: New BM25OpenSearchClient instance
    """
    if settings is None:
        settings = get_settings()

    # Use provided host or settings host
    opensearch_host = host or settings.opensearch.host

    return BM25OpenSearchClient(host=opensearch_host, settings=settings)
