"""
Graph schema definitions for Neo4j database.
"""

from typing import Dict, List, Optional
from enum import Enum


class NodeType:
    """Node types in the graph."""
    JOB = "Job"
    COMPANY = "Company"
    SKILL = "Skill"
    APPLICATION = "Application"
    USER = "User"


class RelationshipType:
    """Relationship types in the graph."""
    REQUIRES_SKILL = "REQUIRES_SKILL"
    APPLIED_TO = "APPLIED_TO"
    WORKS_AT = "WORKS_AT"
    HAS_SKILL = "HAS_SKILL"
    MATCHES = "MATCHES"
    POSTED_BY = "POSTED_BY"
    LOCATED_IN = "LOCATED_IN"


class ApplicationStatus(Enum):
    """Application status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    ACCEPTED = "accepted"


class GraphSchema:
    """Defines the graph database schema and constraints."""
    
    @staticmethod
    def get_node_properties(node_type: str) -> Dict[str, str]:
        """Get expected properties for a node type."""
        properties = {
            NodeType.JOB: {
                "job_id": "string",
                "title": "string",
                "description": "string",
                "location": "string",
                "salary_min": "float",
                "salary_max": "float",
                "employment_type": "string",
                "posted_date": "string",
                "url": "string",
                "source": "string",
            },
            NodeType.COMPANY: {
                "company_id": "string",
                "name": "string",
                "industry": "string",
                "size": "string",
                "website": "string",
            },
            NodeType.SKILL: {
                "skill_id": "string",
                "name": "string",
                "category": "string",
            },
            NodeType.APPLICATION: {
                "application_id": "string",
                "status": "string",
                "applied_date": "string",
                "updated_date": "string",
                "match_score": "float",
            },
            NodeType.USER: {
                "user_id": "string",
                "name": "string",
                "email": "string",
                "experience_years": "integer",
                "education_level": "string",
            },
        }
        return properties.get(node_type, {})
    
    @staticmethod
    def get_relationship_properties(rel_type: str) -> Dict[str, str]:
        """Get expected properties for a relationship type."""
        properties = {
            RelationshipType.REQUIRES_SKILL: {
                "required_level": "string",
                "is_mandatory": "boolean",
            },
            RelationshipType.MATCHES: {
                "match_score": "float",
                "matched_date": "string",
            },
            RelationshipType.APPLIED_TO: {
                "applied_date": "string",
            },
        }
        return properties.get(rel_type, {})
    
    @staticmethod
    def get_constraints() -> List[str]:
        """Get Cypher constraints to create."""
        return [
            f"CREATE CONSTRAINT job_id IF NOT EXISTS FOR (j:{NodeType.JOB}) REQUIRE j.job_id IS UNIQUE",
            f"CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:{NodeType.COMPANY}) REQUIRE c.company_id IS UNIQUE",
            f"CREATE CONSTRAINT skill_id IF NOT EXISTS FOR (s:{NodeType.SKILL}) REQUIRE s.skill_id IS UNIQUE",
            f"CREATE CONSTRAINT application_id IF NOT EXISTS FOR (a:{NodeType.APPLICATION}) REQUIRE a.application_id IS UNIQUE",
            f"CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:{NodeType.USER}) REQUIRE u.user_id IS UNIQUE",
        ]
    
    @staticmethod
    def get_indexes() -> List[str]:
        """Get Cypher indexes to create."""
        return [
            f"CREATE INDEX job_title IF NOT EXISTS FOR (j:{NodeType.JOB}) ON (j.title)",
            f"CREATE INDEX company_name IF NOT EXISTS FOR (c:{NodeType.COMPANY}) ON (c.name)",
            f"CREATE INDEX skill_name IF NOT EXISTS FOR (s:{NodeType.SKILL}) ON (s.name)",
        ]

