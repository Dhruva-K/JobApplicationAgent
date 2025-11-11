"""
Writer Agent: Generates personalized resumes and cover letters.
"""

import logging
from typing import Dict, List, Optional, Any

from graph.memory import GraphMemory
from llm.llama_client import LLMClient
from llm.prompts import PromptTemplates

logger = logging.getLogger(__name__)


class WriterAgent:
    """Agent responsible for generating personalized documents."""
    
    def __init__(self, graph_memory: GraphMemory, llm_client: LLMClient):
        """Initialize Writer Agent.
        
        Args:
            graph_memory: GraphMemory instance
            llm_client: LLM client for document generation
        """
        self.graph_memory = graph_memory
        self.llm_client = llm_client
    
    def generate_cover_letter(
        self,
        user_id: str,
        job_id: str,
        applicant_name: Optional[str] = None
    ) -> Optional[str]:
        """Generate a personalized cover letter.
        
        Args:
            user_id: User identifier
            job_id: Job identifier
            applicant_name: Optional applicant name (defaults to user name)
            
        Returns:
            Generated cover letter text or None if generation fails
        """
        # Get user profile
        user_profile = self._get_user_profile(user_id)
        if not user_profile:
            logger.warning(f"User profile not found: {user_id}")
            return None
        
        # Get job information
        job = self.graph_memory.get_job(job_id)
        if not job:
            logger.warning(f"Job not found: {job_id}")
            return None
        
        # Get job skills
        job_skills_data = self.graph_memory.get_job_skills(job_id)
        required_skills = [skill.get("name", "") for skill in job_skills_data if skill.get("is_mandatory", True)]
        
        # Get user skills
        user_skills = self.graph_memory.get_user_skills(user_id)
        user_skill_names = [skill.get("name", "") for skill in user_skills]
        
        # Prepare prompt
        applicant_name = applicant_name or user_profile.get("name", "Applicant")
        
        prompt = PromptTemplates.format_cover_letter(
            job_title=job.get("title", ""),
            company_name=job.get("company_name", "the company"),
            job_description=job.get("description", ""),
            required_skills=required_skills,
            applicant_name=applicant_name,
            user_skills=user_skill_names,
            user_experience=self._format_experience(user_profile),
            user_education=user_profile.get("education_level", "")
        )
        
        try:
            cover_letter = self.llm_client.generate(prompt, temperature=0.8)
            logger.info(f"Generated cover letter for user {user_id} and job {job_id}")
            return cover_letter.strip()
        except Exception as e:
            logger.error(f"Error generating cover letter: {e}")
            return None
    
    def generate_resume_section(
        self,
        user_id: str,
        job_id: str,
        section_type: str,
        specific_instructions: str = ""
    ) -> Optional[str]:
        """Generate a tailored resume section.
        
        Args:
            user_id: User identifier
            job_id: Job identifier
            section_type: Type of section (e.g., "Summary", "Experience", "Skills")
            specific_instructions: Additional instructions for the section
            
        Returns:
            Generated resume section text or None if generation fails
        """
        # Get user profile
        user_profile = self._get_user_profile(user_id)
        if not user_profile:
            logger.warning(f"User profile not found: {user_id}")
            return None
        
        # Get job information
        job = self.graph_memory.get_job(job_id)
        if not job:
            logger.warning(f"Job not found: {job_id}")
            return None
        
        # Get job skills
        job_skills_data = self.graph_memory.get_job_skills(job_id)
        required_skills = [skill.get("name", "") for skill in job_skills_data]
        
        # Get user skills
        user_skills = self.graph_memory.get_user_skills(user_id)
        user_skill_names = [skill.get("name", "") for skill in user_skills]
        
        # Prepare prompt
        prompt = PromptTemplates.format_resume_section(
            job_title=job.get("title", ""),
            job_description=job.get("description", ""),
            required_skills=required_skills,
            user_skills=user_skill_names,
            user_experience=self._format_experience(user_profile),
            user_education=user_profile.get("education_level", ""),
            section_type=section_type,
            specific_instructions=specific_instructions
        )
        
        try:
            section = self.llm_client.generate(prompt, temperature=0.7)
            logger.info(f"Generated {section_type} section for user {user_id} and job {job_id}")
            return section.strip()
        except Exception as e:
            logger.error(f"Error generating resume section: {e}")
            return None
    
    def generate_resume_summary(
        self,
        user_id: str,
        job_id: str
    ) -> Optional[str]:
        """Generate a tailored resume summary/objective.
        
        Args:
            user_id: User identifier
            job_id: Job identifier
            
        Returns:
            Generated resume summary or None if generation fails
        """
        # Get user profile
        user_profile = self._get_user_profile(user_id)
        if not user_profile:
            logger.warning(f"User profile not found: {user_id}")
            return None
        
        # Get job information
        job = self.graph_memory.get_job(job_id)
        if not job:
            logger.warning(f"Job not found: {job_id}")
            return None
        
        # Get job skills
        job_skills_data = self.graph_memory.get_job_skills(job_id)
        required_skills = [skill.get("name", "") for skill in job_skills_data]
        
        # Get user skills
        user_skills = self.graph_memory.get_user_skills(user_id)
        user_skill_names = [skill.get("name", "") for skill in user_skills]
        
        # Prepare prompt
        prompt = PromptTemplates.format_resume_summary(
            job_title=job.get("title", ""),
            job_description=job.get("description", ""),
            required_skills=required_skills,
            user_skills=user_skill_names,
            user_experience=self._format_experience(user_profile),
            years_experience=user_profile.get("experience_years", 0)
        )
        
        try:
            summary = self.llm_client.generate(prompt, temperature=0.7)
            logger.info(f"Generated resume summary for user {user_id} and job {job_id}")
            return summary.strip()
        except Exception as e:
            logger.error(f"Error generating resume summary: {e}")
            return None
    
    def generate_complete_resume(
        self,
        user_id: str,
        job_id: str,
        sections: List[str] = None
    ) -> Dict[str, str]:
        """Generate a complete tailored resume.
        
        Args:
            user_id: User identifier
            job_id: Job identifier
            sections: List of sections to generate (default: ["Summary", "Skills", "Experience"])
            
        Returns:
            Dictionary mapping section names to generated content
        """
        if sections is None:
            sections = ["Summary", "Skills", "Experience"]
        
        resume = {}
        
        for section in sections:
            try:
                content = self.generate_resume_section(user_id, job_id, section)
                if content:
                    resume[section] = content
            except Exception as e:
                logger.error(f"Error generating section {section}: {e}")
                continue
        
        logger.info(f"Generated complete resume with {len(resume)} sections")
        return resume
    
    def _get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from graph.
        
        Args:
            user_id: User identifier
            
        Returns:
            User profile dictionary or None
        """
        try:
            # Query Neo4j for user data
            query = """
            MATCH (u:User {user_id: $user_id})
            RETURN u as user
            """
            
            with self.graph_memory.driver.session(database=self.graph_memory.database) as session:
                result = session.run(query, user_id=user_id)
                record = result.single()
                if record:
                    return dict(record["user"])
            return None
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    def _format_experience(self, user_profile: Dict[str, Any]) -> str:
        """Format user experience for prompts.
        
        Args:
            user_profile: User profile dictionary
            
        Returns:
            Formatted experience string
        """
        experience_years = user_profile.get("experience_years", 0)
        education = user_profile.get("education_level", "")
        
        parts = []
        if experience_years:
            parts.append(f"{experience_years} years of experience")
        if education:
            parts.append(f"Education: {education}")
        
        return "; ".join(parts) if parts else "No specific experience details"

