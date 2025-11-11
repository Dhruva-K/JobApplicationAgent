"""
Embedding generation utilities using SentenceTransformers.
"""

import logging
from typing import List, Union
from sentence_transformers import SentenceTransformer
import torch

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings using SentenceTransformers."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", device: str = "cpu"):
        """Initialize embedding generator.
        
        Args:
            model_name: Name of the SentenceTransformer model
            device: Device to run on ("cpu" or "cuda")
        """
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() and device == "cuda" else "cpu"
        
        try:
            self.model = SentenceTransformer(model_name, device=self.device)
            logger.info(f"Loaded embedding model: {model_name} on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for text(s).
        
        Args:
            texts: Single text string or list of texts
            normalize: Whether to normalize embeddings to unit length
            
        Returns:
            Single embedding vector or list of embedding vectors
        """
        if isinstance(texts, str):
            texts = [texts]
        
        try:
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=normalize
            )
            
            if len(texts) == 1:
                return embeddings[0].tolist()
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        emb1 = self.encode(text1)
        emb2 = self.encode(text2)
        
        # Compute cosine similarity
        import numpy as np
        dot_product = np.dot(emb1, emb2)
        return float(dot_product)  # Already normalized, so dot product = cosine similarity
    
    def find_most_similar(self, query: str, candidates: List[str], top_k: int = 5) -> List[tuple]:
        """Find most similar texts to a query.
        
        Args:
            query: Query text
            candidates: List of candidate texts
            top_k: Number of top results to return
            
        Returns:
            List of (text, similarity_score) tuples, sorted by similarity
        """
        query_emb = self.encode(query)
        candidate_embs = self.encode(candidates)
        
        import numpy as np
        similarities = np.dot(candidate_embs, query_emb)
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        return [(candidates[i], float(similarities[i])) for i in top_indices]

