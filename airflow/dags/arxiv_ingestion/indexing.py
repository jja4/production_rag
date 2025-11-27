import asyncio
import logging
from datetime import datetime, timedelta, timezone

from opensearchpy import helpers
from src.db.factory import make_database
from src.services.indexing.factory import make_hybrid_indexing_service
from src.services.opensearch.factory import make_opensearch_client_fresh
from src.services.opensearch.index_config import ARXIV_PAPERS_INDEX, ARXIV_PAPERS_MAPPING

logger = logging.getLogger(__name__)


async def _index_papers_with_chunks(papers):
    """Async helper to index papers with chunking and embeddings."""
    indexing_service = make_hybrid_indexing_service()

    papers_data = []
    for paper in papers:
        if hasattr(paper, "__dict__"):
            paper_dict = {
                "id": str(paper.id),
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "categories": paper.categories,
                "published_date": paper.published_date,
                "raw_text": paper.raw_text,
                "sections": paper.sections,
            }
        else:
            paper_dict = paper
        papers_data.append(paper_dict)

    stats = await indexing_service.index_papers_batch(papers=papers_data, replace_existing=True)

    return stats


def index_papers_hybrid(**context):
    """Index papers with chunking and vector embeddings for hybrid search.

    This task:
    1. Fetches recently processed papers from PostgreSQL
    2. Chunks them into overlapping segments (600 words, 100 overlap)
    3. Generates embeddings using Jina AI
    4. Indexes chunks with embeddings into OpenSearch
    """
    try:
        database = make_database()

        ti = context.get("ti")

        fetch_results = None
        if ti:
            fetch_results = ti.xcom_pull(task_ids="fetch_daily_papers", key="fetch_results")

        with database.get_session() as session:
            from src.models.paper import Paper

            if fetch_results and fetch_results.get("papers_stored", 0) > 0:
                from sqlalchemy import desc

                papers = session.query(Paper).order_by(desc(Paper.created_at)).limit(fetch_results["papers_stored"]).all()
            else:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=1)
                papers = session.query(Paper).filter(Paper.created_at >= cutoff_date).all()

            if not papers:
                logger.info("No papers to index for hybrid search")
                return {"papers_indexed": 0, "chunks_created": 0}

            logger.info(f"Indexing {len(papers)} papers for hybrid search")

            stats = asyncio.run(_index_papers_with_chunks(papers))

            logger.info(
                f"Hybrid indexing complete: {stats['papers_processed']} papers, "
                f"{stats['total_chunks_created']} chunks created, "
                f"{stats['total_chunks_indexed']} chunks indexed"
            )

            if ti:
                ti.xcom_push(key="hybrid_index_stats", value=stats)

            return stats

    except Exception as e:
        logger.error(f"Failed to index papers for hybrid search: {e}")
        raise


def verify_hybrid_index(**context):
    """Verify hybrid index health and get statistics."""
    try:
        opensearch_client = make_opensearch_client_fresh()

        stats = opensearch_client.client.indices.stats(index=opensearch_client.index_name)

        count = opensearch_client.client.count(index=opensearch_client.index_name)

        paper_count_query = {"aggs": {"unique_papers": {"cardinality": {"field": "arxiv_id"}}}, "size": 0}

        paper_count_response = opensearch_client.client.search(index=opensearch_client.index_name, body=paper_count_query)

        unique_papers = paper_count_response["aggregations"]["unique_papers"]["value"]

        result = {
            "index_name": opensearch_client.index_name,
            "total_chunks": count["count"],
            "unique_papers": unique_papers,
            "avg_chunks_per_paper": (count["count"] / unique_papers if unique_papers > 0 else 0),
            "index_size_mb": stats["indices"][opensearch_client.index_name]["total"]["store"]["size_in_bytes"] / (1024 * 1024),
        }

        logger.info(
            f"Hybrid index stats: {result['total_chunks']} chunks, "
            f"{result['unique_papers']} papers, "
            f"{result['avg_chunks_per_paper']:.1f} chunks/paper"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to verify hybrid index: {e}")
        raise


def index_papers_bm25(**context):
    """Index papers for BM25 keyword search (Week 3 compatibility).

    This task:
    1. Fetches recently processed papers from PostgreSQL
    2. Indexes full papers (no chunking) into OpenSearch
    3. Uses the arxiv-papers index for simple BM25 search
    
    This is the simpler indexing approach needed for Week 3,
    before introducing chunking and embeddings in later weeks.
    """
    try:
        from opensearchpy import OpenSearch

        database = make_database()

        # Create OpenSearch client for BM25 index
        from src.config import get_settings

        settings = get_settings()
        
        opensearch_client = OpenSearch(
            hosts=[settings.opensearch.host],
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
        )

        # Create index if it doesn't exist
        if not opensearch_client.indices.exists(index=ARXIV_PAPERS_INDEX):
            opensearch_client.indices.create(index=ARXIV_PAPERS_INDEX, body=ARXIV_PAPERS_MAPPING)
            logger.info(f"Created BM25 index: {ARXIV_PAPERS_INDEX}")

        ti = context.get("ti")

        fetch_results = None
        if ti:
            fetch_results = ti.xcom_pull(task_ids="fetch_daily_papers", key="fetch_results")

        with database.get_session() as session:
            from src.models.paper import Paper

            if fetch_results and fetch_results.get("papers_stored", 0) > 0:
                from sqlalchemy import desc

                papers = session.query(Paper).order_by(desc(Paper.created_at)).limit(fetch_results["papers_stored"]).all()
            else:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=1)
                papers = session.query(Paper).filter(Paper.created_at >= cutoff_date).all()

            if not papers:
                logger.info("No papers to index for BM25 search")
                return {"papers_indexed": 0}

            logger.info(f"Indexing {len(papers)} papers for BM25 search")

            # Prepare bulk indexing actions
            actions = []
            for paper in papers:
                paper_doc = {
                    "_index": ARXIV_PAPERS_INDEX,
                    "_id": paper.arxiv_id,
                    "_source": {
                        "arxiv_id": paper.arxiv_id,
                        "title": paper.title,
                        "abstract": paper.abstract,
                        "authors": paper.authors,
                        "categories": paper.categories,
                        "published_date": paper.published_date.isoformat() if paper.published_date else None,
                        "pdf_url": f"https://arxiv.org/pdf/{paper.arxiv_id}.pdf",
                        "raw_text": paper.raw_text or "",
                        "section_titles": paper.sections.get("titles", []) if paper.sections else [],
                    },
                }
                actions.append(paper_doc)

            # Bulk index papers
            success, failed = helpers.bulk(opensearch_client, actions, refresh=True)

            logger.info(f"BM25 indexing complete: {success} papers indexed, {len(failed)} failed")

            stats = {
                "papers_indexed": success,
                "papers_failed": len(failed),
                "index_name": ARXIV_PAPERS_INDEX,
            }

            if ti:
                ti.xcom_push(key="bm25_index_stats", value=stats)

            return stats

    except Exception as e:
        logger.error(f"Failed to index papers for BM25 search: {e}")
        raise


def verify_bm25_index(**context):
    """Verify BM25 index health and get statistics."""
    try:
        from opensearchpy import OpenSearch
        from src.config import get_settings

        settings = get_settings()
        
        opensearch_client = OpenSearch(
            hosts=[settings.opensearch.host],
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
        )

        if not opensearch_client.indices.exists(index=ARXIV_PAPERS_INDEX):
            logger.warning(f"BM25 index does not exist: {ARXIV_PAPERS_INDEX}")
            return {"index_name": ARXIV_PAPERS_INDEX, "exists": False, "document_count": 0}

        stats = opensearch_client.indices.stats(index=ARXIV_PAPERS_INDEX)
        count = opensearch_client.count(index=ARXIV_PAPERS_INDEX)

        result = {
            "index_name": ARXIV_PAPERS_INDEX,
            "exists": True,
            "total_papers": count["count"],
            "index_size_mb": stats["indices"][ARXIV_PAPERS_INDEX]["total"]["store"]["size_in_bytes"] / (1024 * 1024),
        }

        logger.info(f"BM25 index stats: {result['total_papers']} papers, {result['index_size_mb']:.2f} MB")

        return result

    except Exception as e:
        logger.error(f"Failed to verify BM25 index: {e}")
        raise

