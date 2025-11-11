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

logger = logging.getLogger(__name__)


class ScoutAgent:
    """Agent responsible for discovering and retrieving job listings."""
    
    def __init__(self, graph_memory: GraphMemory, config: Config):
        """Initialize Scout Agent.
        
        Args:
            graph_memory: GraphMemory instance for storing jobs
            config: Configuration instance
        """
        self.graph_memory = graph_memory
        self.config = config
        self.jsearch_config = config.get_job_api_config("jsearch")
        self.remotive_config = config.get_job_api_config("remotive")
    
    def search_jobs(
        self,
        keywords: str,
        location: Optional[str] = None,
        employment_type: Optional[str] = None,
        max_results: int = 50,
        api_source: str = "jsearch"
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
            return self._search_jsearch(keywords, location, employment_type, max_results)
        elif api_source == "remotive":
            return self._search_remotive(keywords, location, employment_type, max_results)
        else:
            logger.warning(f"Unknown API source: {api_source}, using jsearch")
            return self._search_jsearch(keywords, location, employment_type, max_results)
    
    def _search_jsearch(
        self,
        keywords: str,
        location: Optional[str],
        employment_type: Optional[str],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Search jobs using JSearch API.
        
        Args:
            keywords: Search keywords
            location: Location filter
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
        
        if location:
            params["location"] = location
        
        if employment_type:
            params["employment_types"] = employment_type
        
        headers = {
            "x-api-key": api_key,
            # "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            jobs = []
            for job_data in data.get("data", [])[:max_results]:
                normalized_job = self._normalize_jsearch_job(job_data)
                if normalized_job:
                    jobs.append(normalized_job)
            
            logger.info(f"Retrieved {len(jobs)} jobs from JSearch")
            return jobs
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from JSearch: {e}")
            return []
    
    def _search_remotive(
        self,
        keywords: str,
        location: Optional[str],
        employment_type: Optional[str],
        max_results: int
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
        
        params = {
            "search": keywords,
            "limit": str(max_results)
        }
        
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
    
    def _normalize_jsearch_job(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
            company_id = hashlib.md5(employer.lower().encode()).hexdigest() if employer else None
            
            normalized = {
                "job_id": job_id,
                "title": job_data.get("job_title", ""),
                "description": job_data.get("job_description", ""),
                "location": job_data.get("job_city", "") or job_data.get("job_state", "") or "Remote",
                "salary_min": self._extract_salary_min(job_data.get("job_min_salary")),
                "salary_max": self._extract_salary_max(job_data.get("job_max_salary")),
                "employment_type": job_data.get("job_employment_type", "full-time"),
                "posted_date": job_data.get("job_posted_at_datetime_utc", ""),
                "url": job_data.get("job_apply_link", ""),
                "source": "jsearch",
                "company_id": company_id,
                "company_name": employer,
            }
            
            return normalized if normalized["title"] else None
            
        except Exception as e:
            logger.error(f"Error normalizing JSearch job: {e}")
            return None
    
    def _normalize_remotive_job(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
            company_id = hashlib.md5(company_name.lower().encode()).hexdigest() if company_name else None
            
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
                numbers = re.findall(r'\d+', salary.replace(',', ''))
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
                
                logger.debug(f"Stored job: {job_id}")
                
            except Exception as e:
                logger.error(f"Error storing job: {e}")
                continue
        
        logger.info(f"Stored {len(stored_ids)} jobs in graph database")
        return stored_ids
    
    def search_and_store(
        self,
        keywords: str,
        location: Optional[str] = None,
        employment_type: Optional[str] = None,
        max_results: int = 50,
        api_source: str = "jsearch"
    ) -> List[Dict[str, Any]]:
        """Search for jobs and store them in the graph database.
        
        Args:
            keywords: Job search keywords
            location: Job location filter
            employment_type: Employment type filter
            max_results: Maximum number of results
            api_source: API to use
            
        Returns:
            List of stored job dictionaries
        """
        # Search for jobs
        jobs = self.search_jobs(keywords, location, employment_type, max_results, api_source)
        
        # Store in graph
        stored_ids = self.store_jobs(jobs)
        
        # Return jobs that were successfully stored
        return [job for job in jobs if job.get("job_id") in stored_ids]

