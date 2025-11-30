"""
User Profile management system.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import os

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
        preferences: Optional[Dict[str, Any]] = None,
        resume_text: Optional[str] = None,
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
            resume_text: Optional resume text content

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

            if resume_text:
                user_data["resume_text"] = resume_text

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

    def update_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
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

            # Handle skills separately if provided
            skills_to_update = updates.pop("skills", None)

            # Update user properties using GraphMemory's update method
            if updates:
                success = self.graph_memory.update_user(user_id, updates)
                if not success:
                    logger.error(f"Failed to update user {user_id}")
                    return False

            # Update skills if provided
            if skills_to_update is not None:
                # Get current skills
                current_skills = self.get_skills(user_id)
                current_skill_names = {
                    s.get("name", "").lower() for s in current_skills
                }
                new_skill_names = {s.lower() for s in skills_to_update}

                # Remove skills no longer in the list
                skills_to_remove = current_skill_names - new_skill_names
                for skill_name in skills_to_remove:
                    self.remove_skill(user_id, skill_name)

                # Add new skills
                skills_to_add = new_skill_names - current_skill_names
                for skill_name in skills_to_add:
                    self.add_skill(user_id, skill_name)

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

            with self.graph_memory.driver.session(
                database=self.graph_memory.database
            ) as session:
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

            # Remove relationship using Cypher
            query = """
            MATCH (u:User {user_id: $user_id})-[r:HAS_SKILL]->(s:Skill {skill_id: $skill_id})
            DELETE r
            """
            with self.graph_memory.driver.session(
                database=self.graph_memory.database
            ) as session:
                session.run(query, user_id=user_id, skill_id=skill_to_remove)

            logger.info(f"Removed skill {skill_name} from user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error removing skill: {e}")
            return False

    def update_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user job search preferences.

        Args:
            user_id: User identifier
            preferences: Dictionary of preferences to update

        Returns:
            True if update successful
        """
        try:
            profile = self.get_profile(user_id)
            if not profile:
                logger.warning(f"User profile not found: {user_id}")
                return False

            # Update only the preference fields
            query = """
            MATCH (u:User {user_id: $user_id})
            SET u += $preferences
            """
            with self.graph_memory.driver.session(
                database=self.graph_memory.database
            ) as session:
                session.run(query, user_id=user_id, preferences=preferences)

            logger.info(f"Updated preferences for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return False

    def delete_profile(self, user_id: str) -> bool:
        """Delete a user profile and all associated data.

        Args:
            user_id: User identifier

        Returns:
            True if deletion successful
        """
        try:
            query = """
            MATCH (u:User {user_id: $user_id})
            OPTIONAL MATCH (u)-[r]-()
            DELETE r, u
            """
            with self.graph_memory.driver.session(
                database=self.graph_memory.database
            ) as session:
                result = session.run(query, user_id=user_id)
                result.consume()

            logger.info(f"Deleted user profile: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting profile: {e}")
            return False

    def list_all_profiles(self) -> List[Dict[str, Any]]:
        """List all user profiles in the system.

        Returns:
            List of profile summaries
        """
        try:
            query = """
            MATCH (u:User)
            RETURN u.user_id as user_id,
                   u.name as name,
                   u.email as email,
                   u.experience_years as experience_years
            """

            profiles = []
            with self.graph_memory.driver.session(
                database=self.graph_memory.database
            ) as session:
                result = session.run(query)
                for record in result:
                    profiles.append(dict(record))

            return profiles

        except Exception as e:
            logger.error(f"Error listing profiles: {e}")
            return []

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
            "category": "other",
        }

        try:
            return self.graph_memory.create_skill(skill_data)
        except Exception as e:
            logger.warning(f"Error creating skill: {e}")
            return skill_id

    def upload_resume(self, user_id: str, resume_path: str) -> bool:
        """Parse and store resume content from file.

        Args:
            user_id: User identifier
            resume_path: Path to resume file (PDF or DOCX)

        Returns:
            True if successful
        """
        try:
            resume_text = self._parse_resume(resume_path)
            if not resume_text:
                logger.error(f"Failed to parse resume from {resume_path}")
                return False

            # Update user profile with resume text
            return self.graph_memory.update_user(user_id, {"resume_text": resume_text})

        except Exception as e:
            logger.error(f"Error uploading resume: {e}")
            return False

    def _parse_resume(self, file_path: str) -> Optional[str]:
        """Parse resume text from PDF or DOCX file.

        Args:
            file_path: Path to resume file

        Returns:
            Extracted text or None if failed
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"Resume file not found: {file_path}")
                return None

            extension = path.suffix.lower()

            if extension == ".pdf":
                return self._parse_pdf(file_path)
            elif extension in [".docx", ".doc"]:
                return self._parse_docx(file_path)
            else:
                logger.error(f"Unsupported file format: {extension}")
                return None

        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            return None

    def _parse_pdf(self, file_path: str) -> Optional[str]:
        """Extract text from PDF file."""
        try:
            import PyPDF2

            text = []
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text.append(page.extract_text())

            return "\\n".join(text).strip()

        except ImportError:
            logger.error("PyPDF2 not installed. Run: pip install PyPDF2")
            return None
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            return None

    def _parse_docx(self, file_path: str) -> Optional[str]:
        """Extract text from DOCX file."""
        try:
            import docx

            doc = docx.Document(file_path)
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)

            return "\\n".join(text).strip()

        except ImportError:
            logger.error("python-docx not installed. Run: pip install python-docx")
            return None
        except Exception as e:
            logger.error(f"Error parsing DOCX: {e}")
            return None

    def get_resume(self, user_id: str) -> Optional[str]:
        """Get resume text for a user.

        Args:
            user_id: User identifier

        Returns:
            Resume text or None if not available
        """
        profile = self.get_profile(user_id)
        return profile.get("resume_text") if profile else None

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

    def get_search_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's job search preferences for filtering.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with search preferences
        """
        profile = self.get_profile(user_id)
        skills = self.get_skills(user_id)

        if not profile:
            logger.warning(f"No profile found for user {user_id}")
            return {}

        # Build search keywords from skills and profile
        skill_names = [s.get("name", "") for s in skills]

        preferences = {
            "keywords": skill_names[:5],  # Top 5 skills for search
            "min_experience": max(0, profile.get("experience_years", 0) - 2),
            "max_experience": profile.get("experience_years", 0) + 3,
            "education_level": profile.get("education_level", ""),
            "preferred_roles": profile.get("preferred_roles", []),
            "locations": profile.get("preferred_locations", []),
            "remote_only": profile.get("remote_only", False),
            "employment_types": profile.get("employment_types", ["INTERN", "FULLTIME"]),
            "required_skills": skill_names,
            "salary_min": profile.get("salary_min"),
            "exclude_companies": profile.get("exclude_companies", []),
        }

        return preferences

    @staticmethod
    def interactive_setup(graph_memory: GraphMemory) -> Optional[str]:
        """Interactive CLI setup for creating a user profile.

        Args:
            graph_memory: GraphMemory instance

        Returns:
            Created user_id or None if failed
        """
        user_profile = UserProfile(graph_memory)

        print("\n" + "=" * 60)
        print("USER PROFILE SETUP")
        print("=" * 60 + "\n")

        # Collect user info
        user_id = input("Enter your user ID (e.g., 'dhruva_001'): ").strip()

        # Check if profile already exists
        existing = user_profile.get_profile(user_id)
        if existing:
            overwrite = (
                input(f"⚠️  Profile '{user_id}' already exists. Overwrite? (y/n): ")
                .strip()
                .lower()
            )
            if overwrite != "y":
                print("Setup cancelled.")
                return None

        name = input("Enter your full name: ").strip()
        email = input("Enter your email: ").strip()

        # Experience
        exp_years = input("Years of experience (0 for student/entry-level): ").strip()
        exp_years = int(exp_years) if exp_years.isdigit() else 0

        # Education
        education = input(
            "Education level (e.g., 'Bachelor', 'Master', 'High School'): "
        ).strip()

        # Skills
        print("\nEnter your skills (comma-separated):")
        print("Example: python, java, product management, data analytics, sql")
        skills_input = input("Skills: ").strip()
        skills = [s.strip() for s in skills_input.split(",") if s.strip()]

        # Preferences
        print("\n" + "-" * 60)
        print("JOB SEARCH PREFERENCES")
        print("-" * 60 + "\n")

        # Employment types
        print("Employment types (comma-separated):")
        print("Options: INTERN, FULLTIME, PARTTIME, CONTRACT")
        emp_types = (
            input("Employment types [INTERN,FULLTIME]: ").strip() or "INTERN,FULLTIME"
        )
        employment_types = [et.strip().upper() for et in emp_types.split(",")]

        # Remote preference
        remote_only = input("Remote only? (y/n): ").strip().lower() == "y"

        # Locations
        if not remote_only:
            locations_input = input(
                "Preferred locations (comma-separated, or Enter to skip): "
            ).strip()
            locations = [
                loc.strip() for loc in locations_input.split(",") if loc.strip()
            ]
        else:
            locations = []

        # Salary
        salary_input = input("Minimum salary (or Enter to skip): ").strip()
        salary_min = (
            float(salary_input)
            if salary_input.replace(".", "").replace(",", "").isdigit()
            else None
        )

        # Excluded companies
        exclude_input = input(
            "Companies to exclude (comma-separated, or Enter to skip): "
        ).strip()
        exclude_companies = [c.strip() for c in exclude_input.split(",") if c.strip()]

        # Resume upload
        print("\n" + "-" * 60)
        print("RESUME (OPTIONAL)")
        print("-" * 60 + "\n")
        resume_path = input(
            "Path to resume file (PDF or DOCX, or Enter to skip): "
        ).strip()

        resume_text = None
        if resume_path:
            resume_text = user_profile._parse_resume(resume_path)
            if resume_text:
                print("✅ Resume parsed successfully!")
            else:
                print("⚠️  Failed to parse resume. Continuing without it.")

        # Create profile
        print("\n" + "=" * 60)
        print("CREATING PROFILE...")
        print("=" * 60 + "\n")

        preferences = {
            "employment_types": employment_types,
            "remote_only": remote_only,
            "preferred_locations": locations,
            "salary_min": salary_min,
            "exclude_companies": exclude_companies,
        }

        try:
            created_id = user_profile.create_profile(
                user_id=user_id,
                name=name,
                email=email,
                skills=skills,
                experience_years=exp_years,
                education_level=education,
                preferences=preferences,
                resume_text=resume_text,
            )

            print("\n✅ Profile created successfully!")
            print(f"User ID: {created_id}")
            print(f"Skills: {len(skills)}")
            print(f"Employment Types: {', '.join(employment_types)}")
            print(f"Remote Only: {remote_only}")

            # Show summary
            summary = user_profile.get_profile_summary(user_id)
            print("\n" + "=" * 60)
            print("PROFILE SUMMARY")
            print("=" * 60)
            print(f"Name: {summary['name']}")
            print(f"Email: {summary['email']}")
            print(f"Experience: {summary['experience_years']} years")
            print(f"Education: {summary['education_level']}")
            print(
                f"Skills ({summary['skill_count']}): {', '.join(summary['skills'][:10])}"
            )

            return created_id

        except Exception as e:
            logger.error(f"Error creating profile: {e}", exc_info=True)
            return None
