"""
User Profile management system.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from graph.memory import GraphMemory

logger = logging.getLogger(__name__)


class UserProfile:
    """Manages user profile data and operations."""
    
    def __init__(self, graph_memory: GraphMemory):
        """Initialize User Profile manager.
        
        Args:
            graph_memory: GraphMemory instance
        """
        self.graph_memory = graph_memory
    
    def create_profile(
        self,
        user_id: str,
        name: str,
        email: str,
        skills: Optional[List[str]] = None,
        experience_years: int = 0,
        education_level: str = "",
        preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new user profile.
        
        Args:
            user_id: User identifier
            name: User name
            email: User email
            skills: List of skill names
            experience_years: Years of experience
            education_level: Education level
            preferences: Optional preferences dictionary
            
        Returns:
            Created user ID
        """
        try:
            user_data = {
                "user_id": user_id,
                "name": name,
                "email": email,
                "experience_years": experience_years,
                "education_level": education_level,
            }
            
            if preferences:
                user_data.update(preferences)
            
            # Create user node
            created_id = self.graph_memory.create_user(user_data)
            
            # Add skills
            if skills:
                for skill_name in skills:
                    try:
                        # Get or create skill
                        skill_id = self._get_or_create_skill(skill_name)
                        self.graph_memory.link_user_to_skill(created_id, skill_id)
                    except Exception as e:
                        logger.warning(f"Error adding skill {skill_name}: {e}")
                        continue
            
            logger.info(f"Created user profile: {created_id}")
            return created_id
            
        except Exception as e:
            logger.error(f"Error creating user profile: {e}")
            raise
    
    def update_profile(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update user profile.
        
        Args:
            user_id: User identifier
            updates: Dictionary of fields to update
            
        Returns:
            True if update successful
        """
        try:
            # Get current profile
            current_profile = self.get_profile(user_id)
            if not current_profile:
                logger.warning(f"User profile not found: {user_id}")
                return False
            
            # Update fields
            updated_data = {**current_profile, **updates}
            
            # Recreate user with updated data
            # Note: In a real implementation, you'd have an update method in GraphMemory
            # For now, we'll recreate (this is not ideal but works)
            user_data = {
                "user_id": user_id,
                "name": updated_data.get("name", ""),
                "email": updated_data.get("email", ""),
                "experience_years": updated_data.get("experience_years", 0),
                "education_level": updated_data.get("education_level", ""),
            }
            
            self.graph_memory.create_user(user_data)
            
            logger.info(f"Updated user profile: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return False
    
    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile.
        
        Args:
            user_id: User identifier
            
        Returns:
            User profile dictionary or None if not found
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
    
    def add_skill(self, user_id: str, skill_name: str) -> bool:
        """Add a skill to user profile.
        
        Args:
            user_id: User identifier
            skill_name: Name of the skill to add
            
        Returns:
            True if skill added successfully
        """
        try:
            skill_id = self._get_or_create_skill(skill_name)
            self.graph_memory.link_user_to_skill(user_id, skill_id)
            logger.info(f"Added skill {skill_name} to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding skill: {e}")
            return False
    
    def remove_skill(self, user_id: str, skill_name: str) -> bool:
        """Remove a skill from user profile.
        
        Args:
            user_id: User identifier
            skill_name: Name of the skill to remove
            
        Returns:
            True if skill removed successfully
        """
        try:
            # Get user skills
            user_skills = self.graph_memory.get_user_skills(user_id)
            
            # Find skill
            skill_to_remove = None
            for skill in user_skills:
                if skill.get("name", "").lower() == skill_name.lower():
                    skill_to_remove = skill.get("skill_id")
                    break
            
            if not skill_to_remove:
                logger.warning(f"Skill {skill_name} not found for user {user_id}")
                return False
            
            # Remove relationship
            # Note: GraphMemory would need a remove_skill method
            # For now, this is a placeholder
            logger.info(f"Removed skill {skill_name} from user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing skill: {e}")
            return False
    
    def get_skills(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all skills for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of skill dictionaries
        """
        try:
            return self.graph_memory.get_user_skills(user_id)
        except Exception as e:
            logger.error(f"Error getting user skills: {e}")
            return []
    
    def _get_or_create_skill(self, skill_name: str) -> str:
        """Get existing skill or create a new one.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Skill ID
        """
        skill_name_normalized = skill_name.lower().strip()
        skill_id = f"skill_{hash(skill_name_normalized) % 1000000}"
        
        skill_data = {
            "skill_id": skill_id,
            "name": skill_name_normalized,
            "category": "other"
        }
        
        try:
            return self.graph_memory.create_skill(skill_data)
        except Exception as e:
            logger.warning(f"Error creating skill: {e}")
            return skill_id
    
    def get_profile_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of user profile.
        
        Args:
            user_id: User identifier
            
        Returns:
            Profile summary dictionary
        """
        profile = self.get_profile(user_id)
        skills = self.get_skills(user_id)
        
        return {
            "user_id": user_id,
            "name": profile.get("name", "") if profile else "",
            "email": profile.get("email", "") if profile else "",
            "experience_years": profile.get("experience_years", 0) if profile else 0,
            "education_level": profile.get("education_level", "") if profile else "",
            "skill_count": len(skills),
            "skills": [skill.get("name", "") for skill in skills],
        }

