import math
import os
from typing import Dict, List

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None
    Settings = None

from openai import OpenAI


class FinancialSituationMemory:
    def __init__(self, name, config):
        if config["backend_url"] == "http://localhost:11434/v1":
            self.embedding = "nomic-embed-text"
            embedding_base_url = config["backend_url"]
        else:
            self.embedding = "text-embedding-3-small"
            # Keep embeddings on OpenAI-compatible endpoint even if main LLM provider is not OpenAI.
            embedding_base_url = config.get(
                "embedding_backend_url",
                os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            )

        self.client = OpenAI(base_url=embedding_base_url)
        self._use_chroma = chromadb is not None
        self._fallback_store: List[Dict] = []

        if self._use_chroma:
            self.chroma_client = chromadb.Client(Settings(allow_reset=True))
            self.situation_collection = self.chroma_client.create_collection(name=name)
        else:
            self.chroma_client = None
            self.situation_collection = None

    def get_embedding(self, text):
        """Get OpenAI embedding for a text"""
        
        response = self.client.embeddings.create(
            model=self.embedding, input=text
        )
        return response.data[0].embedding

    @staticmethod
    def _cosine_similarity(vec_a, vec_b):
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def add_situations(self, situations_and_advice):
        """Add financial situations and their corresponding advice. Parameter is a list of tuples (situation, rec)"""

        situations = []
        advice = []
        ids = []
        embeddings = []

        offset = (
            self.situation_collection.count()
            if self._use_chroma
            else len(self._fallback_store)
        )

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))
            embeddings.append(self.get_embedding(situation))

        if self._use_chroma:
            self.situation_collection.add(
                documents=situations,
                metadatas=[{"recommendation": rec} for rec in advice],
                embeddings=embeddings,
                ids=ids,
            )
        else:
            for situation, recommendation, embedding, item_id in zip(
                situations, advice, embeddings, ids
            ):
                self._fallback_store.append(
                    {
                        "id": item_id,
                        "document": situation,
                        "recommendation": recommendation,
                        "embedding": embedding,
                    }
                )

    def get_memories(self, current_situation, n_matches=1):
        """Find matching recommendations using OpenAI embeddings"""
        query_embedding = self.get_embedding(current_situation)

        if self._use_chroma:
            results = self.situation_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_matches,
                include=["metadatas", "documents", "distances"],
            )

            matched_results = []
            for i in range(len(results["documents"][0])):
                matched_results.append(
                    {
                        "matched_situation": results["documents"][0][i],
                        "recommendation": results["metadatas"][0][i]["recommendation"],
                        "similarity_score": 1 - results["distances"][0][i],
                    }
                )

            return matched_results

        if not self._fallback_store:
            return []

        scored = []
        for record in self._fallback_store:
            similarity = self._cosine_similarity(query_embedding, record["embedding"])
            scored.append(
                {
                    "matched_situation": record["document"],
                    "recommendation": record["recommendation"],
                    "similarity_score": similarity,
                }
            )

        scored.sort(key=lambda item: item["similarity_score"], reverse=True)
        return scored[:n_matches]


if __name__ == "__main__":
    # Example usage
    matcher = FinancialSituationMemory()

    # Example data
    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities. Review fixed-income portfolio duration.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks. Look for value opportunities in established tech companies with strong cash flows.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions. Consider reducing allocation to emerging market debt.",
        ),
        (
            "Market showing signs of sector rotation with rising yields",
            "Rebalance portfolio to maintain target allocations. Consider increasing exposure to sectors benefiting from higher rates.",
        ),
    ]

    # Add the example situations and recommendations
    matcher.add_situations(example_data)

    # Example query
    current_situation = """
    Market showing increased volatility in tech sector, with institutional investors 
    reducing positions and rising interest rates affecting growth stock valuations
    """

    try:
        recommendations = matcher.get_memories(current_situation, n_matches=2)

        for i, rec in enumerate(recommendations, 1):
            print(f"\nMatch {i}:")
            print(f"Similarity Score: {rec['similarity_score']:.2f}")
            print(f"Matched Situation: {rec['matched_situation']}")
            print(f"Recommendation: {rec['recommendation']}")

    except Exception as e:
        print(f"Error during recommendation: {str(e)}")
