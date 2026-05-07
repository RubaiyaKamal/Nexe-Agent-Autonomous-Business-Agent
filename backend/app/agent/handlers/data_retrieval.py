import logging

from app.config import get_settings
from app.models.task import Task

logger = logging.getLogger(__name__)


class HandlerError(Exception):
    pass


class DataRetrievalHandler:
    def __init__(self) -> None:
        self._api_key = get_settings().tavily_api_key

    def execute(self, task: Task, context: dict) -> dict:
        logger.info("DataRetrievalHandler invoked for task %s", task.id)

        if not self._api_key:
            logger.warning("TAVILY_API_KEY not set — returning stub; add it to .env to enable real search")
            return {
                "retrieved": False,
                "query": task.description,
                "results": [],
                "source": "stub",
                "warning": "TAVILY_API_KEY not configured",
            }

        query = self._build_query(task, context)
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=self._api_key)
            response = client.search(query, max_results=5)
            results = [
                {
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.0),
                }
                for r in response.get("results", [])
            ]
            logger.info("Tavily returned %d results for query: %s", len(results), query)
            return {
                "retrieved": True,
                "query": query,
                "results": results,
                "source": "tavily",
                "result_count": len(results),
            }
        except Exception as exc:
            raise HandlerError(f"data_retrieval failed: {exc}") from exc

    def _build_query(self, task: Task, context: dict) -> str:
        # Prefer an explicit 'query' key passed via context; fall back to task description
        return context.get("query") or task.description
