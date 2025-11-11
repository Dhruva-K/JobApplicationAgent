"""
Extractor Agent: Extracts structured information from job descriptions.
"""

import logging
import json
from typing import Dict, List, Optional, Any

from graph.memory import GraphMemory
from llm.llama_client import LLMClient
from llm.prompts import PromptTemplates

logger = logging.getLogger(__name__)


class ExtractorAgent:
    """Agent responsible for extracting structured information from job descriptions."""
    
    def __init__(self, graph_memory: GraphMemory, llm_client: LLMClient):
        """Initialize Extractor Agent.
        
        Args:
            graph_memory: GraphMemory instance for storing extracted data
            llm_client: LLM client for information extraction
        """
        self.graph_memory = graph_memory
        self.llm_client = llm_client
    
    def extract_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Extract structured information from a job description.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary containing extracted information or None if extraction fails
        """
        # Get job from graph
        job = self.graph_memory.get_job(job_id)
        if not job:
            logger.warning(f"Job not found: {job_id}")
            return None
        
        job_description = job.get("description", "")
        if not job_description:
            logger.warning(f"Job description not available for: {job_id}")
            return None
        
        # Extract information using LLM
        try:
            prompt = PromptTemplates.format_extract_job_info(job_description)
            response = self.llm_client.generate_json(prompt)
            
            if "error" in response:
                logger.error(f"LLM extraction error: {response.get('error')}")
                return None
            
            # Store extracted skills
            extracted_data = self._process_extracted_data(job_id, response)
            
            logger.info(f"Extracted information for job: {job_id}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting job info: {e}")
            return None
    
    def _process_extracted_data(self, job_id: str, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Process and store extracted data in the graph.
        
        Args:
            job_id: Job identifier
            extracted: Extracted data dictionary
            
        Returns:
            Processed extracted data
        """
        # Extract and store skills
        required_skills = extracted.get("required_skills", [])
        preferred_skills = extracted.get("preferred_skills", [])
        
        all_skills = list(set(required_skills + preferred_skills))
        
        skill_ids = []
        for skill_name in all_skills:
            if not skill_name or not isinstance(skill_name, str):
                continue
            
            try:
                skill_id = self._get_or_create_skill(skill_name)
                skill_ids.append(skill_id)
                
                # Link to job
                is_mandatory = skill_name in required_skills
                self.graph_memory.link_job_to_skill(
                    job_id,
                    skill_id,
                    required_level=extracted.get("experience_level", "intermediate"),
                    is_mandatory=is_mandatory
                )
            except Exception as e:
                logger.warning(f"Error processing skill {skill_name}: {e}")
                continue
        
        # Update job with extracted information
        extracted_data = {
            "extracted_skills": all_skills,
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "experience_level": extracted.get("experience_level", ""),
            "education_required": extracted.get("education_required", ""),
            "responsibilities": extracted.get("responsibilities", []),
            "employment_type": extracted.get("employment_type", ""),
            "salary_range": extracted.get("salary_range", ""),
        }
        
        return extracted_data
    
    def _get_or_create_skill(self, skill_name: str) -> str:
        """Get existing skill or create a new one.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Skill ID
        """
        # Normalize skill name
        skill_name_normalized = skill_name.lower().strip()
        skill_id = f"skill_{hash(skill_name_normalized) % 1000000}"
        
        # Try to find existing skill by name
        # For now, create with the hash-based ID
        skill_data = {
            "skill_id": skill_id,
            "name": skill_name_normalized,
            "category": self._categorize_skill(skill_name)
        }
        
        try:
            return self.graph_memory.create_skill(skill_data)
        except Exception as e:
            logger.warning(f"Error creating skill: {e}")
            return skill_id
    
    def _categorize_skill(self, skill_name: str) -> str:
        """Categorize a skill based on its name.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Skill category
        """
        skill_lower = skill_name.lower()
        
        # Programming languages
        programming_languages = ["python", "java", "javascript", "c++", "c#", "go", "rust", "ruby", "php", "swift", "kotlin"]
        if any(lang in skill_lower for lang in programming_languages):
            return "programming_language"
        
        # Frameworks
        frameworks = ["react", "angular", "vue", "django", "flask", "spring", "express", "rails", "laravel"]
        if any(fw in skill_lower for fw in frameworks):
            return "framework"
        
        # Databases
        databases = ["sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "oracle"]
        if any(db in skill_lower for db in databases):
            return "database"
        
        # Cloud/DevOps
        cloud = ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins", "ci/cd"]
        if any(c in skill_lower for c in cloud):
            return "cloud_devops"
        
        # Tools
        tools = ["git", "jira", "confluence", "slack", "agile", "scrum"]
        if any(tool in skill_lower for tool in tools):
            return "tool"
        
        # Soft skills
        soft_skills = ["communication", "leadership", "teamwork", "problem solving", "analytical"]
        if any(soft in skill_lower for soft in soft_skills):
            return "soft_skill"
        
        return "other"
    
    def extract_skills_only(self, job_description: str) -> List[str]:
        """Extract only skills from a job description (faster method).
        
        Args:
            job_description: Job description text
            
        Returns:
            List of skill names
        """
        try:
            prompt = PromptTemplates.format_extract_skills(job_description)
            response = self.llm_client.generate_json(prompt)
            
            if isinstance(response, list):
                return response
            elif isinstance(response, dict) and "skills" in response:
                return response["skills"]
            else:
                # Try to parse as JSON array from string
                if isinstance(response, dict) and "raw_response" in response:
                    try:
                        parsed = json.loads(response["raw_response"])
                        if isinstance(parsed, list):
                            return parsed
                    except:
                        pass
                
                logger.warning("Unexpected response format from skill extraction")
                return []
                
        except Exception as e:
            logger.error(f"Error extracting skills: {e}")
            return []
    
    def batch_extract(self, job_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Extract information for multiple jobs.
        
        Args:
            job_ids: List of job identifiers
            
        Returns:
            Dictionary mapping job_id to extracted data
        """
        results = {}
        
        for job_id in job_ids:
            try:
                extracted = self.extract_job_info(job_id)
                if extracted:
                    results[job_id] = extracted
            except Exception as e:
                logger.error(f"Error extracting info for job {job_id}: {e}")
                continue
        
        logger.info(f"Extracted information for {len(results)}/{len(job_ids)} jobs")
        return results

