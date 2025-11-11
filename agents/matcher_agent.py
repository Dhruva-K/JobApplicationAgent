"""
Matcher Agent: Computes candidate-job fit using skill overlap and semantic similarity.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple

from graph.memory import GraphMemory
from llm.llama_client import LLMClient
from llm.prompts import PromptTemplates
from utils.embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class MatcherAgent:
    """Agent responsible for matching candidates to jobs."""
    
    def __init__(
        self,
        graph_memory: GraphMemory,
        llm_client: LLMClient,
        embedding_generator: EmbeddingGenerator
    ):
        """Initialize Matcher Agent.
        
        Args:
            graph_memory: GraphMemory instance
            llm_client: LLM client for advanced matching
            embedding_generator: Embedding generator for semantic similarity
        """
        self.graph_memory = graph_memory
        self.llm_client = llm_client
        self.embedding_generator = embedding_generator
    
    def match_jobs(
        self,
        user_id: str,
        job_ids: Optional[List[str]] = None,
        min_score: float = 0.6,
        use_semantic: bool = True
    ) -> List[Dict[str, Any]]:
        """Match user to jobs.
        
        Args:
            user_id: User identifier
            job_ids: Optional list of specific job IDs to match against
            min_score: Minimum match score threshold
            use_semantic: Whether to use semantic similarity
            
        Returns:
            List of matched jobs with scores, sorted by score descending
        """
        # Get user skills
        user_skills = self.graph_memory.get_user_skills(user_id)
        user_skill_names = [skill.get("name", "") for skill in user_skills]
        
        if not user_skill_names:
            logger.warning(f"No skills found for user: {user_id}")
            return []
        
        # Get jobs to match
        if job_ids:
            jobs = [self.graph_memory.get_job(jid) for jid in job_ids if self.graph_memory.get_job(jid)]
        else:
            # Get all jobs (with limit)
            jobs = self.graph_memory.search_jobs(limit=100)
        
        matches = []
        
        for job in jobs:
            job_id = job.get("job_id")
            if not job_id:
                continue
            
            # Get job skills
            job_skills_data = self.graph_memory.get_job_skills(job_id)
            job_skill_names = [skill.get("name", "") for skill in job_skills_data]
            
            if not job_skill_names:
                # Try to extract skills if not already extracted
                logger.debug(f"No skills found for job {job_id}, skipping")
                continue
            
            # Calculate match score
            match_score = self._calculate_match_score(
                user_skill_names,
                job_skill_names,
                job,
                use_semantic
            )
            
            if match_score >= min_score:
                matches.append({
                    "job_id": job_id,
                    "job": job,
                    "match_score": match_score,
                    "matched_skills": self._get_matched_skills(user_skill_names, job_skill_names),
                    "missing_skills": self._get_missing_skills(user_skill_names, job_skill_names),
                })
        
        # Sort by match score descending
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        
        # Store matches in graph
        for match in matches:
            try:
                self.graph_memory.create_match(
                    user_id,
                    match["job_id"],
                    match["match_score"]
                )
            except Exception as e:
                logger.warning(f"Error storing match: {e}")
        
        logger.info(f"Found {len(matches)} matches for user {user_id}")
        return matches
    
    def _calculate_match_score(
        self,
        user_skills: List[str],
        job_skills: List[str],
        job: Dict[str, Any],
        use_semantic: bool
    ) -> float:
        """Calculate match score between user and job.
        
        Args:
            user_skills: List of user skill names
            job_skills: List of job skill names
            job: Job dictionary
            use_semantic: Whether to use semantic similarity
            
        Returns:
            Match score (0.0 to 1.0)
        """
        # Exact skill match score
        user_skills_lower = [s.lower().strip() for s in user_skills]
        job_skills_lower = [s.lower().strip() for s in job_skills]
        
        matched_exact = set(user_skills_lower) & set(job_skills_lower)
        exact_score = len(matched_exact) / len(job_skills_lower) if job_skills_lower else 0.0
        
        # Semantic similarity score (if enabled)
        semantic_score = 0.0
        if use_semantic and job_skills_lower:
            try:
                # Create skill descriptions for embedding
                user_skills_text = " ".join(user_skills_lower)
                job_skills_text = " ".join(job_skills_lower)
                
                semantic_score = self.embedding_generator.similarity(
                    user_skills_text,
                    job_skills_text
                )
                # Normalize to 0-1 range (cosine similarity is already -1 to 1, but we want 0-1)
                semantic_score = (semantic_score + 1) / 2
            except Exception as e:
                logger.warning(f"Error calculating semantic similarity: {e}")
        
        # Combine scores (weighted average)
        if use_semantic:
            # 70% exact match, 30% semantic
            combined_score = 0.7 * exact_score + 0.3 * semantic_score
        else:
            combined_score = exact_score
        
        return min(1.0, max(0.0, combined_score))
    
    def _get_matched_skills(self, user_skills: List[str], job_skills: List[str]) -> List[str]:
        """Get list of skills that match between user and job.
        
        Args:
            user_skills: User skill names
            job_skills: Job skill names
            
        Returns:
            List of matched skill names
        """
        user_skills_lower = [s.lower().strip() for s in user_skills]
        job_skills_lower = [s.lower().strip() for s in job_skills]
        
        matched = set(user_skills_lower) & set(job_skills_lower)
        
        # Return original case from job_skills
        matched_original = []
        for skill in job_skills:
            if skill.lower().strip() in matched:
                matched_original.append(skill)
        
        return matched_original
    
    def _get_missing_skills(self, user_skills: List[str], job_skills: List[str]) -> List[str]:
        """Get list of job skills that user doesn't have.
        
        Args:
            user_skills: User skill names
            job_skills: Job skill names
            
        Returns:
            List of missing skill names
        """
        user_skills_lower = [s.lower().strip() for s in user_skills]
        job_skills_lower = [s.lower().strip() for s in job_skills]
        
        missing = set(job_skills_lower) - set(user_skills_lower)
        
        # Return original case from job_skills
        missing_original = []
        for skill in job_skills:
            if skill.lower().strip() in missing:
                missing_original.append(skill)
        
        return missing_original
    
    def match_with_llm(
        self,
        user_id: str,
        job_id: str
    ) -> Optional[Dict[str, Any]]:
        """Use LLM for advanced matching evaluation.
        
        Args:
            user_id: User identifier
            job_id: Job identifier
            
        Returns:
            Match evaluation dictionary or None
        """
        # Get user skills
        user_skills = self.graph_memory.get_user_skills(user_id)
        user_skill_names = [skill.get("name", "") for skill in user_skills]
        
        # Get job
        job = self.graph_memory.get_job(job_id)
        if not job:
            return None
        
        job_skills_data = self.graph_memory.get_job_skills(job_id)
        job_skill_names = [skill.get("name", "") for skill in job_skills_data]
        
        # Use LLM for evaluation
        try:
            prompt = PromptTemplates.format_match_evaluation(
                candidate_skills=user_skill_names,
                job_skills=job_skill_names,
                job_title=job.get("title", ""),
                job_description=job.get("description", "")
            )
            
            response = self.llm_client.generate_json(prompt)
            
            if "error" in response:
                logger.warning(f"LLM matching error: {response.get('error')}")
                return None
            
            return response
            
        except Exception as e:
            logger.error(f"Error in LLM matching: {e}")
            return None
    
    def get_top_matches(
        self,
        user_id: str,
        top_k: int = 10,
        min_score: float = 0.6
    ) -> List[Dict[str, Any]]:
        """Get top K job matches for a user.
        
        Args:
            user_id: User identifier
            top_k: Number of top matches to return
            min_score: Minimum match score
            
        Returns:
            List of top matched jobs
        """
        matches = self.match_jobs(user_id, min_score=min_score)
        return matches[:top_k]

