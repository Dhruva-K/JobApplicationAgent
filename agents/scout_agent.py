"""
Scout Agent: Retrieves job listings from open APIs.
"""

import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

from graph.memory import GraphMemory
from core.config import Config
from core.user_profile import UserProfile
from agents.base_agent import BaseAgent
from graph.schema import NodeType, RelationshipType

logger = logging.getLogger(__name__)


class ScoutAgent(BaseAgent):
    """Agent responsible for discovering and retrieving job listings."""

    def __init__(self, graph_memory: GraphMemory, config: Config):
        """Initialize Scout Agent.

        Args:
            graph_memory: GraphMemory instance for storing jobs
            config: Configuration instance
        """
        super().__init__(name="ScoutAgent", graph_memory=graph_memory, role="scout")
        self.config = config
        self.jsearch_config = config.get_job_api_config("jsearch")
        self.remotive_config = config.get_job_api_config("remotive")

    def search_jobs(
        self,
        keywords: str,
        date_posted: Optional[str],
        employment_type: Optional[str] = None,
        max_results: int = 50,
        api_source: str = "jsearch",
    ) -> List[Dict[str, Any]]:
        """Search for jobs using the specified API.

        Args:
            keywords: Job search keywords
            location: Job location filter
            employment_type: Employment type filter
            max_results: Maximum number of results
            api_source: API to use ("jsearch" or "remotive")

        Returns:
            List of job dictionaries
        """
        if api_source == "jsearch":
            return self._search_jsearch(
                keywords, date_posted, employment_type, max_results
            )
        elif api_source == "remotive":
            return self._search_remotive(
                keywords, date_posted, employment_type, max_results
            )
        else:
            logger.warning(f"Unknown API source: {api_source}, using jsearch")
            return self._search_jsearch(
                keywords, date_posted, employment_type, max_results
            )

    def _search_jsearch(
        self,
        keywords: str,
        date_posted: Optional[str],
        employment_type: Optional[str],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Search jobs using JSearch API.

        Args:
            keywords: Search keywords
            date_posted: Date posted filter
            employment_type: Employment type
            max_results: Maximum results

        Returns:
            List of job dictionaries
        """
        api_key = self.jsearch_config.get("api_key")
        base_url = self.jsearch_config.get("base_url", "https://jsearch.p.rapidapi.com")

        if not api_key:
            logger.warning("JSearch API key not configured, returning empty results")
            return []

        url = f"{base_url}/search"

        params = {
            "query": keywords,
            "page": "1",
            "num_pages": str((max_results // 10) + 1),
        }

        if date_posted:
            params["date_posted"] = date_posted

        if employment_type:
            params["employment_types"] = employment_type

        headers = {
            "x-api-key": api_key,
            # "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }

        try:
            # Retry logic for timeouts
            max_retries = 3
            retry_count = 0
            last_error = None

            while retry_count < max_retries:
                try:
                    # Increase timeout and add retries for 504 errors
                    response = requests.get(
                        url, params=params, headers=headers, timeout=60
                    )
                    response.raise_for_status()
                    data = response.json()

                    jobs = []
                    for job_data in data.get("data", [])[:max_results]:
                        normalized_job = self._normalize_jsearch_job(job_data)
                        if normalized_job:
                            jobs.append(normalized_job)

                    logger.info(f"Retrieved {len(jobs)} jobs from JSearch")
                    return jobs

                except requests.exceptions.Timeout as e:
                    retry_count += 1
                    last_error = e
                    logger.warning(
                        f"JSearch timeout (attempt {retry_count}/{max_retries}): {e}"
                    )
                    if retry_count < max_retries:
                        import time

                        time.sleep(2 * retry_count)  # Exponential backoff
                        continue
                    break

                except requests.exceptions.HTTPError as e:
                    # If 504 Gateway Timeout, retry
                    if e.response.status_code == 504:
                        retry_count += 1
                        last_error = e
                        logger.warning(
                            f"JSearch 504 Gateway Timeout (attempt {retry_count}/{max_retries})"
                        )
                        if retry_count < max_retries:
                            import time

                            time.sleep(3 * retry_count)  # Exponential backoff
                            continue
                    raise  # Re-raise other HTTP errors

            # All retries exhausted
            logger.error(f"JSearch failed after {max_retries} attempts: {last_error}")
            logger.info("Falling back to Remotive API...")
            return self._search_remotive(keywords, None, employment_type, max_results)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from JSearch: {e}")
            logger.info("Falling back to Remotive API...")
            return self._search_remotive(keywords, None, employment_type, max_results)

    def _search_remotive(
        self,
        keywords: str,
        location: Optional[str],
        employment_type: Optional[str],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Search jobs using Remotive API.

        Args:
            keywords: Search keywords
            location: Location filter (not used for Remotive, all jobs are remote)
            employment_type: Employment type
            max_results: Maximum results

        Returns:
            List of job dictionaries
        """
        base_url = self.remotive_config.get("base_url", "https://remotive.com/api")

        url = f"{base_url}/remote-jobs"

        params = {"search": keywords, "limit": str(max_results)}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            jobs = []
            for job_data in data.get("jobs", [])[:max_results]:
                normalized_job = self._normalize_remotive_job(job_data)
                if normalized_job:
                    jobs.append(normalized_job)

            logger.info(f"Retrieved {len(jobs)} jobs from Remotive")
            return jobs

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from Remotive: {e}")
            return []

    def _normalize_jsearch_job(
        self, job_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Normalize JSearch job data to standard format.

        Args:
            job_data: Raw job data from JSearch API

        Returns:
            Normalized job dictionary or None if invalid
        """
        try:
            job_id = job_data.get("job_id", "")
            if not job_id:
                # Generate ID from URL
                url = job_data.get("job_apply_link", "")
                if url:
                    job_id = hashlib.md5(url.encode()).hexdigest()
                else:
                    return None

            # Extract company information
            employer = job_data.get("employer_name", "")
            company_id = (
                hashlib.md5(employer.lower().encode()).hexdigest() if employer else None
            )
            # Extract job highlights (qualifications and responsibilities)
            job_highlights = job_data.get("job_highlights", {})
            qualifications = job_highlights.get("Qualifications", [])
            responsibilities = job_highlights.get("Responsibilities", [])
            normalized = {
                "job_id": job_id,
                "title": job_data.get("job_title", ""),
                "description": job_data.get("job_description", ""),
                "location": job_data.get("job_city", "")
                or job_data.get("job_state", "")
                or "Remote",
                "salary_min": self._extract_salary_min(job_data.get("job_min_salary")),
                "salary_max": self._extract_salary_max(job_data.get("job_max_salary")),
                "employment_type": job_data.get("job_employment_type", "full-time"),
                "posted_date": job_data.get("job_posted_at_datetime_utc", ""),
                "url": job_data.get("job_apply_link", ""),
                "source": "jsearch",
                "company_id": company_id,
                "company_name": employer,
                "qualifications": qualifications,
                "responsibilities": responsibilities,
            }

            return normalized if normalized["title"] else None

        except Exception as e:
            logger.error(f"Error normalizing JSearch job: {e}")
            return None

    def _normalize_remotive_job(
        self, job_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Normalize Remotive job data to standard format.

        Args:
            job_data: Raw job data from Remotive API

        Returns:
            Normalized job dictionary or None if invalid
        """
        try:
            job_id = str(job_data.get("id", ""))
            if not job_id:
                url = job_data.get("url", "")
                if url:
                    job_id = hashlib.md5(url.encode()).hexdigest()
                else:
                    return None

            company_name = job_data.get("company_name", "")
            company_id = (
                hashlib.md5(company_name.lower().encode()).hexdigest()
                if company_name
                else None
            )

            normalized = {
                "job_id": job_id,
                "title": job_data.get("title", ""),
                "description": job_data.get("description", ""),
                "location": "Remote",  # Remotive is remote-only
                "salary_min": None,
                "salary_max": None,
                "employment_type": job_data.get("job_type", "full-time"),
                "posted_date": job_data.get("publication_date", ""),
                "url": job_data.get("url", ""),
                "source": "remotive",
                "company_id": company_id,
                "company_name": company_name,
            }

            return normalized if normalized["title"] else None

        except Exception as e:
            logger.error(f"Error normalizing Remotive job: {e}")
            return None

    def _extract_salary_min(self, salary: Any) -> Optional[float]:
        """Extract minimum salary from various formats."""
        if salary is None:
            return None
        try:
            if isinstance(salary, (int, float)):
                return float(salary)
            if isinstance(salary, str):
                # Try to extract number
                import re

                numbers = re.findall(r"\d+", salary.replace(",", ""))
                if numbers:
                    return float(numbers[0])
        except:
            pass
        return None

    def _extract_salary_max(self, salary: Any) -> Optional[float]:
        """Extract maximum salary from various formats."""
        return self._extract_salary_min(salary)  # Same logic for now

    def store_jobs(self, jobs: List[Dict[str, Any]]) -> List[str]:
        """Store jobs in the graph database.

        Args:
            jobs: List of normalized job dictionaries

        Returns:
            List of stored job IDs
        """
        stored_ids = []

        for job in jobs:
            try:
                # Store job
                job_id = self.graph_memory.create_job(job)
                stored_ids.append(job_id)

                # Store company if available
                if job.get("company_id") and job.get("company_name"):
                    company_data = {
                        "company_id": job["company_id"],
                        "name": job["company_name"],
                    }
                    self.graph_memory.create_company(company_data)
                    self.graph_memory.link_job_to_company(job_id, job["company_id"])

                # Track that this agent monitored this job
                self.graph_memory.driver.session().run(
                    f"""
                    MATCH (a:{NodeType.AGENT} {{agent_id: $agent_id}})
                    MATCH (j:{NodeType.JOB} {{job_id: $job_id}})
                    MERGE (a)-[:{RelationshipType.MONITORED} {{timestamp: $timestamp}}]->(j)
                """,
                    agent_id=self.agent_id,
                    job_id=job_id,
                    timestamp=datetime.now().isoformat(),
                )
                logger.debug(f"Stored job: {job_id}")

            except Exception as e:
                logger.error(f"Error storing job: {e}")
                continue

        logger.info(f"Stored {len(stored_ids)} jobs in graph database")
        return stored_ids

    def run(
        self,
        keywords: str,
        date_posted: Optional[str] = None,
        employment_type: Optional[str] = None,
        max_results: int = 50,
        api_source: str = "jsearch",
    ):
        """
        Execute full job discovery + storage cycle.

        Args:
            keywords: Job search keywords
            date_posted: Date filter for jobs
            employment_type: Optional employment type filter
            max_results: Maximum jobs to fetch from API
            api_source: API source to use
        """
        self.update_status("active")

        logger.info(
            f"[ScoutAgent] Searching jobs for keywords='{keywords}', source={api_source}"
        )

        # Fetch jobs from API
        jobs = self.search_jobs(
            keywords, date_posted, employment_type, max_results, api_source
        )

        if not jobs:
            logger.warning("[ScoutAgent] No jobs found from API.")
            self.update_status("idle")
            return

        logger.info(f"[ScoutAgent] Fetched {len(jobs)} jobs from API")

        # Store all jobs (no filtering here - Matcher will score them)
        stored_ids = self.store_jobs(jobs)
        logger.info(f"[ScoutAgent] Cycle complete: {len(stored_ids)} jobs stored.")
        self.update_status("idle")

    async def _handle_data_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle job search request from another agent.

        Args:
            payload: Request with 'keywords', 'date_posted', 'employment_type', 'max_results'

        Returns:
            Response with job_ids and count
        """
        try:
            keywords = payload.get("keywords", "")
            date_posted = payload.get("date_posted")
            employment_type = payload.get("employment_type")
            max_results = payload.get("max_results", 50)
            api_source = payload.get("api_source", "jsearch")

            if not keywords:
                return {"status": "error", "error": "keywords required"}

            logger.info(f"[ScoutAgent] Processing search request: {keywords}")

            # Search and store jobs
            jobs = self.search_jobs(
                keywords, date_posted, employment_type, max_results, api_source
            )
            stored_ids = self.store_jobs(jobs) if jobs else []

            return {
                "status": "success",
                "job_ids": stored_ids,
                "count": len(stored_ids),
            }
        except Exception as e:
            logger.error(f"[ScoutAgent] Error handling request: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_status_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status update from orchestrator.

        Args:
            payload: Status update details

        Returns:
            Current agent status
        """
        return {"status": "acknowledged", "agent": "scout", "current_status": "idle"}
