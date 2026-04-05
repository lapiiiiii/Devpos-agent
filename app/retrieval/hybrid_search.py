from typing import List, Dict, Any, Optional, Tuple
import re
from rank_bm25 import BM25Okapi
import logging

logger = logging.getLogger(__name__)


class BM25Retriever:
    def __init__(self, tokenize_mode: str = "default"):
        self.tokenize_mode = tokenize_mode
        self._corpus: List[str] = []
        self._tokenized_corpus: List[List[str]] = []
        self._bm25: Optional[BM25Okapi] = None
        self._metadata: List[Dict[str, Any]] = []

    def index_documents(
        self, documents: List[str], metadata: Optional[List[Dict[str, Any]]] = None
    ):
        self._corpus = documents
        self._metadata = metadata or [{}] * len(documents)

        self._tokenized_corpus = [self._tokenize(doc) for doc in documents]
        self._bm25 = BM25Okapi(self._tokenized_corpus)

        logger.info(f"Indexed {len(documents)} documents with BM25")

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        tokens = re.findall(r"\w+", text)
        return tokens

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self._bm25 or not self._corpus:
            logger.warning("BM25 index not initialized, returning empty results")
            return []

        query_tokens = self._tokenize(query)
        scores = self._bm25.get_scores(query_tokens)

        doc_scores = list(enumerate(scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for i, (doc_idx, score) in enumerate(doc_scores[:top_k]):
            if score > 0:
                results.append(
                    {
                        "id": f"bm25_doc_{doc_idx}",
                        "content": self._corpus[doc_idx],
                        "metadata": self._metadata[doc_idx] if doc_idx < len(self._metadata) else {},
                        "score": float(score),
                        "rank": i + 1,
                    }
                )

        return results


class HybridSearcher:
    def __init__(self, vector_store, bm25_retriever: Optional[BM25Retriever] = None):
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever or BM25Retriever()
        self._use_rerank = True
        self.rrf_k = 60

    async def search(
        self, query: str, top_k: int = 5, alpha: float = 0.5
    ) -> List[Dict[str, Any]]:
        vector_results = await self.vector_store.search(query, top_k=top_k * 2)

        bm25_results = self.bm25_retriever.search(query, top_k=top_k * 2)

        hybrid_results = self._merge_results(
            vector_results, bm25_results, top_k, alpha
        )

        if self._use_rerank and len(hybrid_results) > top_k:
            hybrid_results = self._rerank(query, hybrid_results[: top_k * 2])[:top_k]

        return hybrid_results

    def _merge_results(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        top_k: int,
        alpha: float,
    ) -> List[Dict[str, Any]]:
        scores_map: Dict[str, Dict[str, Any]] = {}

        for result in vector_results:
            doc_id = result["id"]
            vector_score = result.get("score", 0)
            scores_map[doc_id] = {
                **result,
                "vector_score": vector_score,
                "bm25_score": 0,
                "hybrid_score": alpha * vector_score,
            }

        for result in bm25_results:
            doc_id = result["id"]
            bm25_score = result.get("score", 0)

            if doc_id in scores_map:
                scores_map[doc_id]["bm25_score"] = bm25_score
                scores_map[doc_id]["hybrid_score"] = (
                    alpha * scores_map[doc_id]["vector_score"]
                    + (1 - alpha) * bm25_score
                )
            else:
                scores_map[doc_id] = {
                    **result,
                    "vector_score": 0,
                    "bm25_score": bm25_score,
                    "hybrid_score": (1 - alpha) * bm25_score,
                }

        sorted_results = sorted(
            scores_map.values(), key=lambda x: x["hybrid_score"], reverse=True
        )

        return sorted_results[:top_k]

    def _rerank(self, query: str, results: List[Dict]) -> List[Dict]:
        query_terms = set(query.lower().split())

        reranked = []
        for result in results:
            content_lower = result.get("content", "").lower()
            content_terms = set(re.findall(r"\w+", content_lower))

            overlap = len(query_terms & content_terms)
            relevance = overlap / max(len(query_terms), 1)

            result["relevance_score"] = relevance
            result["final_score"] = (
                0.7 * result.get("hybrid_score", 0) + 0.3 * relevance
            )
            reranked.append(result)

        reranked.sort(key=lambda x: x["final_score"], reverse=True)
        return reranked


def reciprocal_rank_fusion(
    result_lists: List[List[Dict]], k: int = 60
) -> List[Dict]:
    scores_map: Dict[str, float] = {}

    for result_list in result_lists:
        for rank, result in enumerate(result_list):
            doc_id = result.get("id", f"doc_{rank}")
            if doc_id not in scores_map:
                scores_map[doc_id] = 0
            scores_map[doc_id] += 1 / (k + rank + 1)

    sorted_ids = sorted(scores_map.keys(), key=lambda x: scores_map[x], reverse=True)

    return [
        {**result, "rrf_score": scores_map[result.get("id", f"doc_{i}")]}
        for i, result in enumerate(result_lists[0])
        if result.get("id") in sorted_ids
    ]
