"""
Matcher Agent: Scores job-candidate fit using LLM-based analysis.
This agent runs AFTER Scout has collected jobs and scores each one.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple

from core.config import Config
from core.user_profile import UserProfile
from graph.memory import GraphMemory
from agents.base_agent import BaseAgent
from llm.llm_client import LLMClient

logger = logging.getLogger(__name__)


class MatcherAgent(BaseAgent):
    """
    Agent responsible for scoring job-candidate matches using LLM analysis.

    Architecture:
    1. Scout Agent collects ALL jobs → stores in database
    2. Matcher Agent runs → scores each job with LLM
    3. Jobs get match_score + match_reason + ranking
    """

    def __init__(
        self,
        graph_memory: GraphMemory,
        config: Config,
        user_profile: Optional[UserProfile] = None,
    ):
        """
        Initialize Matcher Agent.

        Args:
            graph_memory: GraphMemory instance
            config: Configuration object
            user_profile: Optional UserProfile instance (created if not provided)
        """
        super().__init__(name="MatcherAgent", graph_memory=graph_memory, role="matcher")
        self.config = config
        self.user_profile = user_profile or UserProfile(graph_memory)

        # Initialize unified LLM client
        llm_config = config.get_llm_config()
        self.llm_client = LLMClient(llm_config)

        logger.info(
            f"[MatcherAgent] Initialized with {llm_config.get('provider')} LLM: {llm_config.get('model_name')}"
        )

    def score_all_jobs(
        self, user_id: str, job_ids: Optional[List[str]] = None, batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Score all jobs (or specific jobs) for a user using LLM analysis.

        Args:
            user_id: User identifier
            job_ids: Optional list of specific job IDs to score (None = all jobs)
            batch_size: Number of jobs to process in each batch

        Returns:
            Dictionary with scoring results and statistics
        """
        self.update_status("active")

        # Ensure LLM service is available before scoring
        if not self.llm_client.is_available():
            logger.error(f"[MatcherAgent] LLM service not available")
            self.update_status("idle")
            return {
                "error": "LLM service unavailable",
                "hint": "Check API key (for groq/together) or start Ollama server (for local)",
                "provider": self.llm_client.provider,
                "model": self.llm_client.model_name,
            }

        # Get user profile
        profile = self.user_profile.get_profile(user_id)
        if not profile:
            logger.error(f"[MatcherAgent] No profile found for user: {user_id}")
            self.update_status("idle")
            return {"error": "User profile not found"}

        # Get jobs to score
        if job_ids:
            jobs = []
            for job_id in job_ids:
                job = self.graph_memory.get_job(job_id)
                if job:
                    jobs.append(job)
        else:
            # Get all unscored jobs
            jobs = self._get_unscored_jobs(user_id)

        if not jobs:
            logger.info("[MatcherAgent] No jobs to score")
            self.update_status("idle")
            return {"message": "No jobs to score", "scored": 0}

        logger.info(f"[MatcherAgent] Scoring {len(jobs)} jobs for user {user_id}")

        # Score jobs in batches
        scored_count = 0
        failed_count = 0
        scores = []

        for i in range(0, len(jobs), batch_size):
            batch = jobs[i : i + batch_size]
            logger.info(
                f"[MatcherAgent] Processing batch {i//batch_size + 1}/{(len(jobs)-1)//batch_size + 1}"
            )

            for job_idx, job in enumerate(batch):
                job_id = job.get("job_id")
                if not job_id:
                    continue

                try:
                    # Score this job
                    result = self._score_job(user_id, job, profile)

                    if result and "score" in result:
                        # Store score in database
                        self._store_match_score(
                            user_id=user_id,
                            job_id=job_id,
                            score=result["score"],
                            reason=result.get("reason", ""),
                            strengths=result.get("strengths", []),
                            concerns=result.get("concerns", []),
                        )

                        scored_count += 1
                        scores.append(result["score"])

                        logger.info(
                            f"[MatcherAgent] Job {job_id}: score={result['score']}/100"
                        )
                    else:
                        failed_count += 1
                        logger.warning(f"[MatcherAgent] Failed to score job {job_id}")

                    # Add delay between scoring to avoid rate limits (6s for free tier)
                    if job_idx < len(batch) - 1 or i + batch_size < len(jobs):
                        import time

                        logger.info(
                            f"[MatcherAgent] Waiting 6s before next scoring (free tier rate limiting)..."
                        )
                        time.sleep(6.0)

                except Exception as e:
                    failed_count += 1
                    logger.error(f"[MatcherAgent] Error scoring job {job_id}: {e}")

        # Calculate statistics
        avg_score = sum(scores) / len(scores) if scores else 0

        result = {
            "total_jobs": len(jobs),
            "scored": scored_count,
            "failed": failed_count,
            "average_score": avg_score,
            "score_range": {
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
            },
        }

        logger.info(
            f"[MatcherAgent] Scoring complete: {scored_count}/{len(jobs)} jobs scored, "
            f"avg={avg_score:.1f}/100"
        )

        self.update_status("idle")
        return result

    def _score_job(
        self, user_id: str, job: Dict[str, Any], profile: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Score a single job using LLM analysis.

        Args:
            user_id: User identifier
            job: Job dictionary
            profile: User profile dictionary

        Returns:
            Dictionary with score, reason, strengths, concerns
        """
        # Build matching prompt
        prompt = self._build_matching_prompt(user_id, job, profile)

        # Call LLM
        llm_response = self.llm_client.generate(prompt)

        if not llm_response:
            return None

        # Parse LLM response
        return self._parse_llm_score_response(llm_response)

    def _build_matching_prompt(
        self, user_id: str, job: Dict[str, Any], profile: Dict[str, Any]
    ) -> str:
        """
        Build prompt for LLM-based job matching.

        Args:
            user_id: User identifier
            job: Job dictionary
            profile: User profile dictionary

        Returns:
            Formatted prompt string
        """
        # Extract user information
        user_skills = profile.get("skills", [])
        experience_years = profile.get("experience_years", 0)
        education = profile.get("education_level", "Not specified")
        resume_text = profile.get("resume_text", "")

        # Extract job information
        job_title = job.get("title", "Unknown")
        company = job.get("company", {}).get("name", "Unknown Company")
        description = job.get("description", "")
        qualifications = job.get("qualifications", [])
        responsibilities = job.get("responsibilities", [])

        # Build candidate section with resume if available
        candidate_section = f"""CANDIDATE PROFILE:
- Skills: {', '.join(user_skills) if user_skills else 'None listed'}
- Experience: {experience_years} years
- Education: {education}"""

        if resume_text:
            # Include resume text (truncate if too long)
            resume_preview = (
                resume_text[:2000] if len(resume_text) > 2000 else resume_text
            )
            candidate_section += f"""
- Resume:
{resume_preview}"""

        # Build structured prompt
        prompt = f"""You are an expert career advisor analyzing job-candidate fit.

{candidate_section}

JOB POSTING:
- Title: {job_title}
- Company: {company}
- Description: {description[:500]}...

QUALIFICATIONS:
{chr(10).join('- ' + q for q in qualifications[:10]) if qualifications else '- Not specified'}

RESPONSIBILITIES:
{chr(10).join('- ' + r for r in responsibilities[:10]) if responsibilities else '- Not specified'}

TASK:
Analyze the fit between this candidate and job. Provide:
1. Match Score (0-100): How well does the candidate match this job?
2. Strengths: What makes this a good match? (list 2-4 points)
3. Concerns: What are the gaps or risks? (list 2-4 points)
4. Reasoning: Brief explanation of the score

Respond in JSON format:
{{
    "score": 75,
    "strengths": ["Strong Python skills match required tech stack", "Experience aligns with role level"],
    "concerns": ["Missing cloud experience", "No ML background mentioned"],
    "reason": "Good overall match with some skill gaps that can be addressed"
}}

Be realistic and specific. Consider:
- Skill overlap and relevance
- Experience level appropriateness
- Qualification match
- Responsibility alignment
- Career progression fit

JSON Response:"""

        return prompt

    def _parse_llm_score_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse LLM response to extract match score and details.

        Args:
            response: Raw LLM response text

        Returns:
            Dictionary with score, reason, strengths, concerns
        """
        try:
            # Try to find JSON in response
            response = response.strip()

            # Handle markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()

            # Try to parse JSON
            data = json.loads(response)

            # Validate required fields
            if "score" not in data:
                logger.warning("[MatcherAgent] No 'score' in LLM response")
                return None

            # Normalize score to 0-100 range
            score = float(data["score"])
            score = max(0, min(100, score))

            return {
                "score": score,
                "reason": data.get("reason", ""),
                "strengths": data.get("strengths", []),
                "concerns": data.get("concerns", []),
            }

        except json.JSONDecodeError:
            logger.error(
                f"[MatcherAgent] Failed to parse JSON from LLM: {response[:200]}"
            )
            return None
        except Exception as e:
            logger.error(f"[MatcherAgent] Error parsing LLM response: {e}")
            return None

    def _get_unscored_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all jobs that haven't been scored yet for this user.

        Args:
            user_id: User identifier

        Returns:
            List of unscored job dictionaries
        """
        # For now, get all jobs (in future, filter for unscored)
        # This would require adding a query to GraphMemory
        query = """
        MATCH (j:Job)
        WHERE NOT EXISTS {
            MATCH (u:User {user_id: $user_id})-[m:MATCHED]->(j)
            WHERE m.match_score IS NOT NULL
        }
        RETURN j
        LIMIT 100
        """

        try:
            results = self.graph_memory.query(query, {"user_id": user_id})
            jobs = [dict(record["j"]) for record in results]
            return jobs
        except Exception as e:
            logger.error(f"[MatcherAgent] Error fetching unscored jobs: {e}")
            # Fallback: get all jobs
            return self.graph_memory.search_jobs(limit=100)

    def _store_match_score(
        self,
        user_id: str,
        job_id: str,
        score: float,
        reason: str,
        strengths: List[str],
        concerns: List[str],
    ):
        """
        Store match score and details in database.

        Args:
            user_id: User identifier
            job_id: Job identifier
            score: Match score (0-100)
            reason: Explanation of score
            strengths: List of match strengths
            concerns: List of match concerns
        """
        query = """
        MATCH (u:User {user_id: $user_id})
        MATCH (j:Job {job_id: $job_id})
        MERGE (u)-[m:MATCHES]->(j)
        SET m.match_score = $score,
            m.match_reason = $reason,
            m.strengths = $strengths,
            m.concerns = $concerns,
            m.scored_at = datetime()
        """

        self.graph_memory.query(
            query,
            {
                "user_id": user_id,
                "job_id": job_id,
                "score": score,
                "reason": reason,
                "strengths": strengths,
                "concerns": concerns,
            },
        )

    def get_ranked_jobs(
        self, user_id: str, limit: int = 20, min_score: float = 0
    ) -> List[Dict[str, Any]]:
        """
        Get ranked jobs for a user based on match scores.

        Args:
            user_id: User identifier
            limit: Maximum number of jobs to return
            min_score: Minimum match score threshold

        Returns:
            List of jobs ranked by match score (descending)
        """
        query = """
        MATCH (u:User {user_id: $user_id})-[m:MATCHED]->(j:Job)
        WHERE m.match_score >= $min_score
        OPTIONAL MATCH (j)-[:POSTED_BY]->(c:Company)
        RETURN j, m, c
        ORDER BY m.match_score DESC
        LIMIT $limit
        """

        results = self.graph_memory.query(
            query, {"user_id": user_id, "min_score": min_score, "limit": limit}
        )

        ranked_jobs = []
        for record in results:
            job_node = record.get("j", {})
            match_rel = record.get("m", {})
            company_node = record.get("c")

            if not job_node:
                continue

            # job_node and match_rel are now dicts thanks to updated GraphMemory.query()
            job = dict(job_node)

            # Extract match properties from relationship dict
            job["match_score"] = match_rel.get("match_score")
            job["match_reason"] = match_rel.get("match_reason")
            job["strengths"] = match_rel.get("strengths", [])
            job["concerns"] = match_rel.get("concerns", [])

            # Add company if available
            if company_node:
                job["company"] = dict(company_node)

            ranked_jobs.append(job)

        return ranked_jobs

    def run(
        self, user_id: str, job_ids: Optional[List[str]] = None, batch_size: int = 10
    ):
        """
        Main execution method for Matcher Agent.

        Args:
            user_id: User identifier
            job_ids: Optional list of specific job IDs to score
            batch_size: Number of jobs to process in each batch
        """
        logger.info(f"[MatcherAgent] Starting job scoring for user: {user_id}")

        # Score all jobs
        result = self.score_all_jobs(user_id, job_ids, batch_size)

        # Display summary
        logger.info(f"[MatcherAgent] Scoring Results:")
        logger.info(f"  - Total Jobs: {result.get('total_jobs', 0)}")
        logger.info(f"  - Scored: {result.get('scored', 0)}")
        logger.info(f"  - Failed: {result.get('failed', 0)}")
        logger.info(f"  - Average Score: {result.get('average_score', 0):.1f}/100")

        return result

    async def _handle_data_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle job scoring request from another agent.

        Args:
            payload: Request with 'user_id' and optional 'job_ids'

        Returns:
            Response with scoring results
        """
        try:
            user_id = payload.get("user_id")
            job_ids = payload.get("job_ids")
            batch_size = payload.get("batch_size", 10)

            if not user_id:
                return {"status": "error", "error": "user_id required"}

            logger.info(f"[MatcherAgent] Processing scoring request for {user_id}")

            results = self.score_all_jobs(user_id, job_ids, batch_size)

            return {"status": "success", "results": results}
        except Exception as e:
            logger.error(f"[MatcherAgent] Error handling request: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_status_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status update from orchestrator.

        Args:
            payload: Status update details

        Returns:
            Current agent status
        """
        return {
            "status": "acknowledged",
            "agent": "matcher",
            "llm_provider": self.llm_client.provider,
        }
