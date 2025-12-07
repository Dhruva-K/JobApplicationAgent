"""
Neo4j graph memory implementation for storing and retrieving job application data.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from neo4j import GraphDatabase
import logging

from .schema import (
    NodeType,
    RelationshipType,
    ApplicationStatus,
    GraphSchema,
)


logger = logging.getLogger(__name__)


class GraphMemory:
    """Manages Neo4j graph database operations."""

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """Initialize Neo4j connection.

        Args:
            uri: Neo4j connection URI (e.g., "bolt://localhost:7687")
            user: Neo4j username
            password: Neo4j password
            database: Database name (default: "neo4j")
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        self._initialize_schema()

    def close(self):
        """Close the database connection."""
        self.driver.close()

    def _initialize_schema(self):
        """Initialize database schema with constraints and indexes."""
        with self.driver.session(database=self.database) as session:
            # Create constraints
            for constraint in GraphSchema.get_constraints():
                try:
                    session.run(constraint)
                except Exception as e:
                    logger.warning(f"Failed to create constraint: {e}")

            # Create indexes
            for index in GraphSchema.get_indexes():
                try:
                    session.run(index)
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")

    # Utility Query
    def query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Run a raw Cypher query and return records as dicts.

        Args:
            query: Cypher query string
            params: Optional parameters dictionary

        Returns:
            List of records (each record is a dict of returned aliases)
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, **(params or {}))
            # Use record.values() and record.keys() to properly convert Neo4j objects
            records = []
            for record in result:
                record_dict = {}
                for key in record.keys():
                    value = record[key]
                    # Convert Neo4j Node/Relationship objects to dicts
                    if hasattr(value, "__class__") and value.__class__.__name__ in [
                        "Node",
                        "Relationship",
                    ]:
                        # For relationships, we want the properties dict
                        record_dict[key] = dict(value) if value else {}
                    else:
                        record_dict[key] = value
                records.append(record_dict)
            return records

    # Job Operations
    def create_job(self, job_data: Dict[str, Any]) -> str:
        """Create a job node.

        Args:
            job_data: Dictionary containing job information

        Returns:
            job_id: The created job's ID
        """
        job_id = job_data.get("job_id", f"job_{datetime.now().timestamp()}")

        query = f"""
        MERGE (j:{NodeType.JOB} {{job_id: $job_id}})
        SET j += $properties
        RETURN j.job_id as job_id
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                job_id=job_id,
                properties={k: v for k, v in job_data.items() if k != "job_id"},
            )
            return result.single()["job_id"]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job data dictionary or None if not found
        """
        query = f"""
        MATCH (j:{NodeType.JOB} {{job_id: $job_id}})
        RETURN j as job
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, job_id=job_id)
            record = result.single()
            return dict(record["job"]) if record else None

    def search_jobs(
        self, filters: Optional[Dict[str, Any]] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search for jobs with optional filters.

        Args:
            filters: Dictionary of filter criteria
            limit: Maximum number of results

        Returns:
            List of job dictionaries
        """
        query = f"""
        MATCH (j:{NodeType.JOB})
        WHERE 1=1
        """
        params = {"limit": limit}

        if filters:
            if "title" in filters:
                query += " AND j.title CONTAINS $title"
                params["title"] = filters["title"]
            if "location" in filters:
                query += " AND j.location CONTAINS $location"
                params["location"] = filters["location"]

        query += " RETURN j as job LIMIT $limit"

        with self.driver.session(database=self.database) as session:
            result = session.run(query, **params)
            return [dict(record["job"]) for record in result]

    # Company Operations
    def create_company(self, company_data: Dict[str, Any]) -> str:
        """Create a company node.

        Args:
            company_data: Dictionary containing company information

        Returns:
            company_id: The created company's ID
        """
        company_id = company_data.get(
            "company_id", f"company_{datetime.now().timestamp()}"
        )

        query = f"""
        MERGE (c:{NodeType.COMPANY} {{company_id: $company_id}})
        SET c += $properties
        RETURN c.company_id as company_id
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                company_id=company_id,
                properties={k: v for k, v in company_data.items() if k != "company_id"},
            )
            return result.single()["company_id"]

    def link_job_to_company(self, job_id: str, company_id: str):
        """Create relationship between job and company.

        Args:
            job_id: Job identifier
            company_id: Company identifier
        """
        query = f"""
        MATCH (j:{NodeType.JOB} {{job_id: $job_id}})
        MATCH (c:{NodeType.COMPANY} {{company_id: $company_id}})
        MERGE (j)-[:{RelationshipType.POSTED_BY}]->(c)
        """

        with self.driver.session(database=self.database) as session:
            session.run(query, job_id=job_id, company_id=company_id)

    # Skill Operations
    def create_skill(self, skill_data: Dict[str, Any]) -> str:
        """Create a skill node.

        Args:
            skill_data: Dictionary containing skill information

        Returns:
            skill_id: The created skill's ID
        """
        skill_id = skill_data.get("skill_id", f"skill_{datetime.now().timestamp()}")
        skill_name = skill_data.get("name", "").lower().strip()

        query = f"""
        MERGE (s:{NodeType.SKILL} {{skill_id: $skill_id}})
        SET s += $properties, s.name = $skill_name
        RETURN s.skill_id as skill_id
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                skill_id=skill_id,
                skill_name=skill_name,
                properties={
                    k: v for k, v in skill_data.items() if k not in ["skill_id", "name"]
                },
            )
            return result.single()["skill_id"]

    def link_job_to_skill(
        self,
        job_id: str,
        skill_id: str,
        required_level: str = "intermediate",
        is_mandatory: bool = True,
    ):
        """Create relationship between job and required skill.

        Args:
            job_id: Job identifier
            skill_id: Skill identifier
            required_level: Required skill level
            is_mandatory: Whether skill is mandatory
        """
        query = f"""
        MATCH (j:{NodeType.JOB} {{job_id: $job_id}})
        MATCH (s:{NodeType.SKILL} {{skill_id: $skill_id}})
        MERGE (j)-[r:{RelationshipType.REQUIRES_SKILL}]->(s)
        SET r.required_level = $required_level,
            r.is_mandatory = $is_mandatory
        """

        with self.driver.session(database=self.database) as session:
            session.run(
                query,
                job_id=job_id,
                skill_id=skill_id,
                required_level=required_level,
                is_mandatory=is_mandatory,
            )

    def get_job_skills(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all skills required for a job.

        Args:
            job_id: Job identifier

        Returns:
            List of skill dictionaries with relationship properties
        """
        query = f"""
        MATCH (j:{NodeType.JOB} {{job_id: $job_id}})-[r:{RelationshipType.REQUIRES_SKILL}]->(s:{NodeType.SKILL})
        RETURN s as skill, r.required_level as level, r.is_mandatory as mandatory
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, job_id=job_id)
            return [
                {
                    **dict(record["skill"]),
                    "required_level": record["level"],
                    "is_mandatory": record["mandatory"],
                }
                for record in result
            ]

    # User Operations
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a user node.

        Args:
            user_data: Dictionary containing user information

        Returns:
            user_id: The created user's ID
        """
        user_id = user_data.get("user_id", f"user_{datetime.now().timestamp()}")

        query = f"""
        MERGE (u:{NodeType.USER} {{user_id: $user_id}})
        SET u += $properties
        RETURN u.user_id as user_id
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                user_id=user_id,
                properties={k: v for k, v in user_data.items() if k != "user_id"},
            )
            return result.single()["user_id"]

    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing user node with new properties.

        Args:
            user_id: User identifier
            updates: Dictionary containing properties to update

        Returns:
            bool: True if update successful, False otherwise
        """
        if not updates:
            logger.warning(f"No updates provided for user {user_id}")
            return False

        query = f"""
        MATCH (u:{NodeType.USER} {{user_id: $user_id}})
        SET u += $updates
        RETURN u.user_id as user_id
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id, updates=updates)
            record = result.single()
            if record:
                logger.info(f"Updated user {user_id} with {len(updates)} properties")
                return True
            else:
                logger.warning(f"User {user_id} not found for update")
                return False

    def link_user_to_skill(self, user_id: str, skill_id: str):
        """Create relationship between user and skill.

        Args:
            user_id: User identifier
            skill_id: Skill identifier
        """
        query = f"""
        MATCH (u:{NodeType.USER} {{user_id: $user_id}})
        MATCH (s:{NodeType.SKILL} {{skill_id: $skill_id}})
        MERGE (u)-[:{RelationshipType.HAS_SKILL}]->(s)
        """

        with self.driver.session(database=self.database) as session:
            session.run(query, user_id=user_id, skill_id=skill_id)

    def get_user_skills(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all skills for a user.

        Args:
            user_id: User identifier

        Returns:
            List of skill dictionaries
        """
        query = f"""
        MATCH (u:{NodeType.USER} {{user_id: $user_id}})-[:{RelationshipType.HAS_SKILL}]->(s:{NodeType.SKILL})
        RETURN s as skill
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id)
            return [dict(record["skill"]) for record in result]

    # Application Operations
    def create_application(self, application_data: Dict[str, Any]) -> str:
        """Create an application node.

        Args:
            application_data: Dictionary containing application information

        Returns:
            application_id: The created application's ID
        """
        application_id = application_data.get(
            "application_id", f"app_{datetime.now().timestamp()}"
        )

        query = f"""
        MERGE (a:{NodeType.APPLICATION} {{application_id: $application_id}})
        SET a += $properties
        RETURN a.application_id as application_id
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                application_id=application_id,
                properties={
                    k: v for k, v in application_data.items() if k != "application_id"
                },
            )
            return result.single()["application_id"]

    def link_application(self, user_id: str, job_id: str, application_id: str):
        """Link application to user and job.

        Args:
            user_id: User identifier
            job_id: Job identifier
            application_id: Application identifier
        """
        query = f"""
        MATCH (u:{NodeType.USER} {{user_id: $user_id}})
        MATCH (j:{NodeType.JOB} {{job_id: $job_id}})
        MATCH (a:{NodeType.APPLICATION} {{application_id: $application_id}})
        MERGE (u)-[:{RelationshipType.APPLIED_TO}]->(a)
        MERGE (a)-[:{RelationshipType.APPLIED_TO}]->(j)
        """

        with self.driver.session(database=self.database) as session:
            session.run(
                query, user_id=user_id, job_id=job_id, application_id=application_id
            )

    def update_application_status(
        self, application_id: str, status: ApplicationStatus
    ) -> bool:
        """Update application status.

        Args:
            application_id: Application identifier
            status: New application status

        Returns:
            True if application was found and updated, False otherwise
        """
        query = f"""
        MATCH (a:{NodeType.APPLICATION} {{application_id: $application_id}})
        SET a.status = $status,
            a.updated_date = $updated_date
        RETURN a.application_id as id, a.status as status
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                application_id=application_id,
                status=status.value,
                updated_date=datetime.now().isoformat(),
            )
            records = list(result)
            return len(records) > 0  # Returns True if node was found and updated

    def get_user_applications(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all applications for a user.

        Args:
            user_id: User identifier

        Returns:
            List of application dictionaries with job information
        """
        query = f"""
        MATCH (u:{NodeType.USER} {{user_id: $user_id}})-[:{RelationshipType.APPLIED_TO}]->(a:{NodeType.APPLICATION})-[:{RelationshipType.APPLIED_TO}]->(j:{NodeType.JOB})
        RETURN a as application, j as job
        ORDER BY a.applied_date DESC
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id)
            return [
                {**dict(record["application"]), "job": dict(record["job"])}
                for record in result
            ]

    # Matching Operations
    def create_match(self, user_id: str, job_id: str, match_score: float):
        """Create a match relationship between user and job.

        Args:
            user_id: User identifier
            job_id: Job identifier
            match_score: Match score (0.0 to 1.0)
        """
        query = f"""
        MATCH (u:{NodeType.USER} {{user_id: $user_id}})
        MATCH (j:{NodeType.JOB} {{job_id: $job_id}})
        MERGE (u)-[r:{RelationshipType.MATCHES}]->(j)
        SET r.match_score = $match_score,
            r.matched_date = $matched_date
        """

        with self.driver.session(database=self.database) as session:
            session.run(
                query,
                user_id=user_id,
                job_id=job_id,
                match_score=match_score,
                matched_date=datetime.now().isoformat(),
            )

    def get_user_matches(
        self, user_id: str, min_score: float = 0.0, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get job matches for a user.

        Args:
            user_id: User identifier
            min_score: Minimum match score
            limit: Maximum number of results

        Returns:
            List of job dictionaries with match scores and insights
        """
        query = f"""
        MATCH (u:{NodeType.USER} {{user_id: $user_id}})-[r:{RelationshipType.MATCHES}]->(j:{NodeType.JOB})
        WHERE r.match_score >= $min_score
        RETURN j as job, r.match_score as score, r.strengths as strengths, r.concerns as concerns, r.match_reason as reason
        ORDER BY r.match_score DESC
        LIMIT $limit
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(
                query, user_id=user_id, min_score=min_score, limit=limit
            )
            return [
                {
                    **dict(record["job"]),
                    "match_score": record["score"],
                    "match_insights": {
                        "strengths": record.get("strengths", []),
                        "gaps": record.get("concerns", []),
                        "reason": record.get("reason", ""),
                    },
                }
                for record in result
            ]

    def create_agent(self, agent_data: Dict[str, Any]) -> str:
        agent_id = agent_data.get("agent_id", f"agent_{datetime.now().timestamp()}")
        query = f"""
        MERGE (a:{NodeType.AGENT} {{agent_id: $agent_id}})
        SET a += $properties, a.last_run = $last_run
        RETURN a.agent_id as agent_id
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                agent_id=agent_id,
                properties={k: v for k, v in agent_data.items() if k != "agent_id"},
                last_run=datetime.now().isoformat(),
            )
            return result.single()["agent_id"]

    def update_agent_status(self, agent_id: str, status: str):
        query = f"""
        MATCH (a:{NodeType.AGENT} {{agent_id: $agent_id}})
        SET a.status = $status, a.last_run = $last_run
        """
        with self.driver.session(database=self.database) as session:
            session.run(
                query,
                agent_id=agent_id,
                status=status,
                last_run=datetime.now().isoformat(),
            )

    # ======== Resume Management ========
    def create_resume(self, resume_data: Dict[str, Any]) -> str:
        resume_id = resume_data.get("resume_id", f"resume_{datetime.now().timestamp()}")
        query = f"""
        MERGE (r:{NodeType.RESUME} {{resume_id: $resume_id}})
        SET r += $properties, r.created_date = $created_date
        RETURN r.resume_id as resume_id
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                resume_id=resume_id,
                properties={k: v for k, v in resume_data.items() if k != "resume_id"},
                created_date=datetime.now().isoformat(),
            )
            return result.single()["resume_id"]

    def link_resume_to_job(self, resume_id: str, job_id: str):
        query = f"""
        MATCH (r:{NodeType.RESUME} {{resume_id: $resume_id}})
        MATCH (j:{NodeType.JOB} {{job_id: $job_id}})
        MERGE (r)-[:{RelationshipType.TAILORED_FOR} {{timestamp: $timestamp}}]->(j)
        """
        with self.driver.session(database=self.database) as session:
            session.run(
                query,
                resume_id=resume_id,
                job_id=job_id,
                timestamp=datetime.now().isoformat(),
            )

    # ======== Event / Notification Management ========
    def create_event(self, event_data: Dict[str, Any]) -> str:
        event_id = event_data.get("event_id", f"event_{datetime.now().timestamp()}")
        query = f"""
        MERGE (e:{NodeType.EVENT} {{event_id: $event_id}})
        SET e += $properties, e.created_at = $created_at
        RETURN e.event_id as event_id
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                event_id=event_id,
                properties={k: v for k, v in event_data.items() if k != "event_id"},
                created_at=datetime.now().isoformat(),
            )
            return result.single()["event_id"]

    def link_event_to_user(self, event_id: str, user_id: str):
        query = f"""
        MATCH (e:{NodeType.EVENT} {{event_id: $event_id}})
        MATCH (u:{NodeType.USER} {{user_id: $user_id}})
        MERGE (u)-[:{RelationshipType.NEEDS_ACTION_ON} {{timestamp: $timestamp}}]->(e)
        """
        with self.driver.session(database=self.database) as session:
            session.run(
                query,
                event_id=event_id,
                user_id=user_id,
                timestamp=datetime.now().isoformat(),
            )

    def get_pending_events(self, user_id: str) -> List[Dict[str, Any]]:
        query = f"""
        MATCH (u:{NodeType.USER} {{user_id: $user_id}})-[:{RelationshipType.NEEDS_ACTION_ON}]->(e:{NodeType.EVENT})
        WHERE e.status = 'pending'
        RETURN e as event
        ORDER BY e.created_at DESC
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id)
            return [dict(record["event"]) for record in result]
