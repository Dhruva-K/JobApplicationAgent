"""
Tracker Agent: Tracks application status and maintains application history.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from graph.memory import GraphMemory, ApplicationStatus
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class TrackerAgent(BaseAgent):
    """Agent responsible for tracking job applications."""

    def __init__(self, graph_memory: GraphMemory):
        """Initialize Tracker Agent.

        Args:
            graph_memory: GraphMemory instance
        """
        super().__init__(name="TrackerAgent", graph_memory=graph_memory, role="tracker")

    def create_application(
        self,
        user_id: str,
        job_id: str,
        match_score: Optional[float] = None,
        initial_status: ApplicationStatus = ApplicationStatus.PENDING,
    ) -> Optional[str]:
        """Create a new application record.

        Args:
            user_id: User identifier
            job_id: Job identifier
            match_score: Optional match score
            initial_status: Initial application status

        Returns:
            Application ID or None if creation fails
        """
        try:
            application_id = f"app_{user_id}_{job_id}_{int(datetime.now().timestamp())}"

            application_data = {
                "application_id": application_id,
                "status": initial_status.value,
                "applied_date": datetime.now().isoformat(),
                "updated_date": datetime.now().isoformat(),
            }

            if match_score is not None:
                application_data["match_score"] = match_score

            # Create application node
            created_id = self.graph_memory.create_application(application_data)

            # Link application to user and job
            self.graph_memory.link_application(user_id, job_id, created_id)

            logger.info(
                f"Created application {created_id} for user {user_id} and job {job_id}"
            )
            return created_id

        except Exception as e:
            logger.error(f"Error creating application: {e}")
            return None

    def update_application_status(
        self, application_id: str, status: ApplicationStatus
    ) -> bool:
        """Update application status.

        Args:
            application_id: Application identifier
            status: New status

        Returns:
            True if update successful, False otherwise
        """
        try:
            success = self.graph_memory.update_application_status(
                application_id, status
            )
            if success:
                logger.info(
                    f"Updated application {application_id} status to {status.value}"
                )
            else:
                logger.warning(f"Application {application_id} not found in database")
            return success
        except Exception as e:
            logger.error(f"Error updating application status: {e}")
            return False

    def get_application(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Get application details.

        Args:
            application_id: Application identifier

        Returns:
            Application dictionary or None if not found
        """
        # This would query the graph for the application
        # For now, return None as the graph_memory doesn't have a direct get_application method
        # In a real implementation, this would query Neo4j
        try:
            # Query would be: MATCH (a:Application {application_id: $application_id}) RETURN a
            return None
        except Exception as e:
            logger.error(f"Error getting application: {e}")
            return None

    def get_user_applications(
        self, user_id: str, status_filter: Optional[ApplicationStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get all applications for a user.

        Args:
            user_id: User identifier
            status_filter: Optional status filter

        Returns:
            List of application dictionaries
        """
        try:
            applications = self.graph_memory.get_user_applications(user_id)

            if status_filter:
                applications = [
                    app
                    for app in applications
                    if app.get("status") == status_filter.value
                ]

            logger.info(
                f"Retrieved {len(applications)} applications for user {user_id}"
            )
            return applications

        except Exception as e:
            logger.error(f"Error getting user applications: {e}")
            return []

    def get_application_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get application statistics for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary containing statistics
        """
        try:
            applications = self.graph_memory.get_user_applications(user_id)

            total = len(applications)

            status_counts = {}
            for status in ApplicationStatus:
                status_counts[status.value] = sum(
                    1 for app in applications if app.get("status") == status.value
                )

            # Calculate average match score
            match_scores = [
                app.get("match_score", 0.0)
                for app in applications
                if app.get("match_score") is not None
            ]
            avg_match_score = (
                sum(match_scores) / len(match_scores) if match_scores else 0.0
            )

            statistics = {
                "total_applications": total,
                "status_breakdown": status_counts,
                "average_match_score": round(avg_match_score, 2),
                "pending": status_counts.get("pending", 0),
                "submitted": status_counts.get("submitted", 0),
                "interview": status_counts.get("interview", 0),
                "rejected": status_counts.get("rejected", 0),
                "accepted": status_counts.get("accepted", 0),
            }

            logger.info(f"Generated statistics for user {user_id}")
            return statistics

        except Exception as e:
            logger.error(f"Error generating statistics: {e}")
            return {
                "total_applications": 0,
                "status_breakdown": {},
                "average_match_score": 0.0,
            }

    async def _handle_data_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle application tracking request from another agent.

        Args:
            payload: Request with action ('create', 'update', 'get_status', 'get_statistics')

        Returns:
            Response with tracking data
        """
        try:
            action = payload.get("action")
            user_id = payload.get("user_id")

            if action == "create":
                job_id = payload.get("job_id")
                match_score = payload.get("match_score")
                app_id = self.create_application(user_id, job_id, match_score)
                return {"status": "success", "application_id": app_id}

            elif action == "update":
                app_id = payload.get("application_id")
                new_status = ApplicationStatus(payload.get("new_status", "pending"))
                notes = payload.get("notes")
                success = self.update_application_status(app_id, new_status, notes)
                return {"status": "success" if success else "error", "updated": success}

            elif action == "get_status":
                job_id = payload.get("job_id")
                status = self.get_application_status(user_id, job_id)
                return {
                    "status": "success",
                    "application_status": status.value if status else None,
                }

            elif action == "get_statistics":
                stats = self.get_application_statistics(user_id)
                return {"status": "success", "statistics": stats}

            else:
                return {"status": "error", "error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"[TrackerAgent] Error handling request: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_status_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status update from orchestrator.

        Args:
            payload: Status update details

        Returns:
            Current agent status
        """
        return {"status": "acknowledged", "agent": "tracker"}

    def get_recent_applications(
        self, user_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent applications for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of applications to return

        Returns:
            List of recent application dictionaries
        """
        applications = self.get_user_applications(user_id)

        # Sort by applied_date descending
        applications.sort(key=lambda x: x.get("applied_date", ""), reverse=True)

        return applications[:limit]

    def get_applications_by_status(
        self, user_id: str, status: ApplicationStatus
    ) -> List[Dict[str, Any]]:
        """Get applications filtered by status.

        Args:
            user_id: User identifier
            status: Application status to filter by

        Returns:
            List of application dictionaries
        """
        return self.get_user_applications(user_id, status_filter=status)

    def add_application_note(self, application_id: str, note: str) -> bool:
        """Add a note to an application (future enhancement).

        Args:
            application_id: Application identifier
            note: Note text

        Returns:
            True if note added successfully
        """
        # This would store notes in the graph or a separate notes table
        # For now, just log it
        logger.info(f"Note added to application {application_id}: {note}")
        return True

    def get_application_timeline(self, user_id: str) -> List[Dict[str, Any]]:
        """Get application timeline for a user.

        Args:
            user_id: User identifier

        Returns:
            List of timeline events
        """
        applications = self.get_user_applications(user_id)

        timeline = []
        for app in applications:
            timeline.append(
                {
                    "date": app.get("applied_date", ""),
                    "event": "Application submitted",
                    "job_title": app.get("job", {}).get("title", "Unknown"),
                    "status": app.get("status", ""),
                }
            )

            if app.get("updated_date") != app.get("applied_date"):
                timeline.append(
                    {
                        "date": app.get("updated_date", ""),
                        "event": f"Status updated to {app.get('status', '')}",
                        "job_title": app.get("job", {}).get("title", "Unknown"),
                        "status": app.get("status", ""),
                    }
                )

        # Sort by date
        timeline.sort(key=lambda x: x.get("date", ""), reverse=True)

        return timeline
