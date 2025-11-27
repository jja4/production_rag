"""Simple BM25 OpenSearch client for Week 3 keyword search."""

import logging
from typing import Any, Dict, List, Optional

from opensearchpy import OpenSearch, helpers
from src.config import Settings

from .index_config import ARXIV_PAPERS_INDEX, ARXIV_PAPERS_MAPPING
from .query_builder import QueryBuilder

logger = logging.getLogger(__name__)


class BM25OpenSearchClient:
    """Simple OpenSearch client for BM25 keyword search (Week 3).
    
    This client uses the arxiv-papers index for full papers without chunking.
    """

    def __init__(self, host: str, settings: Settings):
        self.host = host
        self.settings = settings
        self.index_name = ARXIV_PAPERS_INDEX  # Uses "arxiv-papers" directly

        self.client = OpenSearch(
            hosts=[host],
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
        )

        logger.info(f"BM25 OpenSearch client initialized with host: {host}, index: {self.index_name}")

    def health_check(self) -> bool:
        """Check if OpenSearch cluster is healthy."""
        try:
            health = self.client.cluster.health()
            return health["status"] in ["green", "yellow"]
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics for the BM25 index."""
        try:
            if not self.client.indices.exists(index=self.index_name):
                return {"index_name": self.index_name, "exists": False, "document_count": 0}

            stats_response = self.client.indices.stats(index=self.index_name)
            index_stats = stats_response["indices"][self.index_name]["total"]

            return {
                "index_name": self.index_name,
                "exists": True,
                "document_count": index_stats["docs"]["count"],
                "deleted_count": index_stats["docs"]["deleted"],
                "size_in_bytes": index_stats["store"]["size_in_bytes"],
            }

        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {"index_name": self.index_name, "exists": False, "document_count": 0, "error": str(e)}

    def create_index(self, force: bool = False) -> bool:
        """Create the BM25 index.
        
        :param force: If True, delete and recreate the index
        :returns: True if created, False if already exists
        """
        try:
            if force and self.client.indices.exists(index=self.index_name):
                self.client.indices.delete(index=self.index_name)
                logger.info(f"Deleted existing BM25 index: {self.index_name}")

            if not self.client.indices.exists(index=self.index_name):
                self.client.indices.create(index=self.index_name, body=ARXIV_PAPERS_MAPPING)
                logger.info(f"Created BM25 index: {self.index_name}")
                return True

            logger.info(f"BM25 index already exists: {self.index_name}")
            return False

        except Exception as e:
            logger.error(f"Error creating BM25 index: {e}")
            raise

    def search_papers(
        self, query: str, size: int = 10, from_: int = 0, categories: Optional[List[str]] = None, latest: bool = False
    ) -> Dict[str, Any]:
        """Search for papers using BM25 scoring.
        
        :param query: Search query string
        :param size: Number of results to return
        :param from_: Offset for pagination
        :param categories: Optional list of categories to filter by
        :param latest: Sort by date instead of relevance
        :returns: Search results with papers
        """
        try:
            builder = QueryBuilder(
                query=query,
                size=size,
                from_=from_,
                categories=categories,
                latest_papers=latest,
                search_chunks=False,  # Search full papers, not chunks
            )
            search_body = builder.build()

            response = self.client.search(index=self.index_name, body=search_body)

            results = {"total": response["hits"]["total"]["value"], "hits": []}

            for hit in response["hits"]["hits"]:
                paper = hit["_source"]
                paper["score"] = hit["_score"]

                if "highlight" in hit:
                    paper["highlights"] = hit["highlight"]

                results["hits"].append(paper)

            logger.info(f"BM25 search for '{query[:50]}...' returned {results['total']} results")
            return results

        except Exception as e:
            logger.error(f"BM25 search error: {e}")
            return {"total": 0, "hits": []}

    def index_paper(self, paper_data: Dict[str, Any]) -> bool:
        """Index a single paper.
        
        :param paper_data: Paper document dictionary
        :returns: True if successful
        """
        try:
            response = self.client.index(
                index=self.index_name,
                id=paper_data.get("arxiv_id"),
                body=paper_data,
                refresh=True,
            )

            return response["result"] in ["created", "updated"]

        except Exception as e:
            logger.error(f"Error indexing paper: {e}")
            return False

    def bulk_index_papers(self, papers: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk index multiple papers.
        
        :param papers: List of paper dictionaries
        :returns: Statistics
        """
        try:
            actions = []
            for paper in papers:
                action = {
                    "_index": self.index_name,
                    "_id": paper.get("arxiv_id"),
                    "_source": paper,
                }
                actions.append(action)

            success, failed = helpers.bulk(self.client, actions, refresh=True)

            logger.info(f"Bulk indexed {success} papers, {len(failed)} failed")
            return {"success": success, "failed": len(failed)}

        except Exception as e:
            logger.error(f"Bulk paper indexing error: {e}")
            raise

    def delete_paper(self, arxiv_id: str) -> bool:
        """Delete a paper by arxiv_id.
        
        :param arxiv_id: ArXiv ID of the paper
        :returns: True if deletion was successful
        """
        try:
            response = self.client.delete(index=self.index_name, id=arxiv_id, refresh=True)
            logger.info(f"Deleted paper {arxiv_id}")
            return response["result"] == "deleted"

        except Exception as e:
            logger.error(f"Error deleting paper: {e}")
            return False

    def get_paper(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """Get a single paper by arxiv_id.
        
        :param arxiv_id: ArXiv ID of the paper
        :returns: Paper document or None
        """
        try:
            response = self.client.get(index=self.index_name, id=arxiv_id)
            return response["_source"]

        except Exception as e:
            logger.error(f"Error getting paper: {e}")
            return None
