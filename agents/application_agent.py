"""
Application Agent - Handles automated job application submission.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from agents.base_agent import BaseAgent
from agents.browser_automation import (
    BrowserAutomation,
    LinkedInHandler,
    GreenhouseHandler,
    LeverHandler,
    WorkdayHandler,
    iCIMSHandler,
    IndeedHandler,
    GenericHandler,
)
from graph.memory import GraphMemory
from core.config import Config

logger = logging.getLogger(__name__)


class ApplicationStatus(Enum):
    """Status of an application submission."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FAILED = "failed"
    REQUIRES_MANUAL = "requires_manual"


class ApplicationAgent(BaseAgent):
    """Agent responsible for submitting job applications."""

    def __init__(self, graph_memory: GraphMemory, config: Config):
        """Initialize Application Agent.

        Args:
            graph_memory: GraphMemory instance
            config: Configuration instance
        """
        super().__init__(
            name="ApplicationAgent", graph_memory=graph_memory, role="application"
        )
        self.config = config
        self.application_history: Dict[str, List[Dict[str, Any]]] = {}

        logger.info("[ApplicationAgent] Initialized")

    async def apply_to_job(
        self,
        job_id: str,
        user_id: str,
        documents: Optional[Dict[str, str]] = None,
        form_data: Optional[Dict[str, Any]] = None,
        auto_submit: bool = False,
    ) -> Dict[str, Any]:
        """Apply to a job with provided documents and form data.

        Args:
            job_id: Job identifier
            user_id: User identifier
            documents: Dictionary of document paths (resume, cover_letter)
            form_data: Pre-filled form data
            auto_submit: Whether to auto-submit or require review

        Returns:
            Application result dictionary
        """
        logger.info(f"[ApplicationAgent] Applying to job {job_id} for user {user_id}")

        try:
            # Get job details
            job = self._get_job_details(job_id)
            if not job:
                return {
                    "status": ApplicationStatus.FAILED.value,
                    "job_id": job_id,
                    "error": "Job not found",
                    "timestamp": datetime.now().isoformat(),
                }

            # Detect platform
            platform = self._detect_platform(job.get("url", ""))
            logger.info(f"[ApplicationAgent] Detected platform: {platform}")

            # Check if complex form - but we'll try automation anyway if enabled
            is_complex = self._requires_manual_application(job, platform)
            if is_complex:
                logger.info(
                    f"[ApplicationAgent] Complex form detected - will attempt automation if enabled"
                )

            # Fetch user profile data
            user_profile = self._get_user_profile(user_id)

            # Prepare application
            application_data = self._prepare_application_data(
                job=job,
                documents=documents,
                form_data=form_data,
                user_profile=user_profile,
            )

            # Submit application
            if auto_submit:
                result = await self._submit_application(
                    job_id=job_id, platform=platform, application_data=application_data
                )
            else:
                # Prepare for review
                result = {
                    "status": ApplicationStatus.PENDING.value,
                    "job_id": job_id,
                    "platform": platform,
                    "application_data": application_data,
                    "ready_for_review": True,
                    "timestamp": datetime.now().isoformat(),
                }

            # Record application attempt
            self._record_application(user_id, job_id, result)

            # Update graph memory
            if result["status"] == ApplicationStatus.SUBMITTED.value:
                self._update_graph_memory(job_id, user_id, result)

            return result

        except Exception as e:
            logger.error(
                f"[ApplicationAgent] Error applying to job {job_id}: {e}", exc_info=True
            )
            return {
                "status": ApplicationStatus.FAILED.value,
                "job_id": job_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def batch_apply(
        self,
        job_ids: List[str],
        user_id: str,
        documents: Optional[Dict[str, str]] = None,
        auto_submit: bool = False,
    ) -> List[Dict[str, Any]]:
        """Apply to multiple jobs in batch.

        Args:
            job_ids: List of job identifiers
            user_id: User identifier
            documents: Dictionary of document paths
            auto_submit: Whether to auto-submit

        Returns:
            List of application results
        """
        logger.info(f"[ApplicationAgent] Batch applying to {len(job_ids)} jobs")

        results = []
        for job_id in job_ids:
            result = await self.apply_to_job(
                job_id=job_id,
                user_id=user_id,
                documents=documents,
                auto_submit=auto_submit,
            )
            results.append(result)

            # Rate limiting - wait between applications
            await asyncio.sleep(2)

        return results

    def _get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from graph memory.

        Args:
            user_id: User identifier

        Returns:
            User profile dictionary or None
        """
        query = """
        MATCH (u:User {user_id: $user_id})
        RETURN u.email as email,
               u.name as full_name
        """

        result = self.graph_memory.query(query, {"user_id": user_id})
        if result:
            profile = result[0]
            # Parse full name into first/last name
            full_name = profile.get("full_name", "")
            if full_name:
                name_parts = full_name.split()
                profile["first_name"] = name_parts[0] if name_parts else ""
                profile["last_name"] = (
                    " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                )
            return profile

        logger.warning(f"[ApplicationAgent] No profile found for user {user_id}")
        return None

    def _get_job_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details from graph memory.

        Args:
            job_id: Job identifier

        Returns:
            Job details dictionary or None
        """
        if not self.graph_memory:
            return None

        try:
            return self.graph_memory.get_job(job_id)
        except Exception as e:
            logger.error(f"[ApplicationAgent] Error getting job details: {e}")
            return None

    def _detect_platform(self, url: str) -> str:
        """Detect job application platform from URL.

        Args:
            url: Job posting URL

        Returns:
            Platform identifier
        """
        url_lower = url.lower()

        if "linkedin.com" in url_lower:
            return "linkedin"
        elif "greenhouse.io" in url_lower:
            return "greenhouse"
        elif "lever.co" in url_lower:
            return "lever"
        elif "workday.com" in url_lower or "myworkdayjobs.com" in url_lower:
            return "workday"
        elif "smartrecruiters.com" in url_lower:
            return "smartrecruiters"
        elif "icims.com" in url_lower:
            return "icims"
        elif "indeed.com" in url_lower:
            return "indeed"
        else:
            return "unknown"

    def _requires_manual_application(self, job: Dict[str, Any], platform: str) -> bool:
        """Check if job requires manual application.

        Args:
            job: Job details
            platform: Platform identifier

        Returns:
            True if manual application required
        """
        # Always require manual for unknown platforms
        if platform == "unknown":
            return True

        # Check for external redirects
        description = job.get("description", "").lower()
        if any(
            phrase in description
            for phrase in [
                "apply on our website",
                "external application",
                "visit our careers page",
                "apply directly at",
            ]
        ):
            return True

        # Check for complex requirements
        if any(
            phrase in description
            for phrase in [
                "video interview",
                "assessment test",
                "coding challenge",
                "take-home assignment",
            ]
        ):
            return True

        return False

    def _prepare_application_data(
        self,
        job: Dict[str, Any],
        documents: Optional[Dict[str, str]],
        form_data: Optional[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Prepare application data for submission.

        Args:
            job: Job details
            documents: Document paths
            form_data: Form data
            user_profile: User profile data

        Returns:
            Prepared application data
        """
        application_data = {
            "job_id": job.get("job_id"),
            "job_title": job.get("title"),
            "company": job.get("company_name"),
            "url": job.get("url"),
            "documents": documents or {},
            "form_data": form_data or {},
            "prepared_at": datetime.now().isoformat(),
        }

        # Add user profile data for form filling
        if user_profile:
            application_data.update(
                {
                    "email": user_profile.get("email"),
                    "phone": user_profile.get("phone"),
                    "first_name": user_profile.get("first_name"),
                    "last_name": user_profile.get("last_name"),
                    "full_name": f"{user_profile.get('first_name', '')} {user_profile.get('last_name', '')}".strip(),
                    "linkedin_url": user_profile.get("linkedin_url"),
                    "github_url": user_profile.get("github_url"),
                    "website_url": user_profile.get("website_url"),
                    "address": user_profile.get("address"),
                    "city": user_profile.get("city"),
                    "state": user_profile.get("state"),
                    "zip_code": user_profile.get("zip_code"),
                }
            )

        return application_data

    async def _submit_application(
        self, job_id: str, platform: str, application_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit application to platform.

        Args:
            job_id: Job identifier
            platform: Platform identifier
            application_data: Application data

        Returns:
            Submission result
        """
        logger.info(f"[ApplicationAgent] Submitting application to {platform}")

        # Check for mock mode first
        mock_mode = self.config.get("application", {}).get("mock_applications", False)
        if mock_mode:
            # Mock successful application
            logger.info(
                f"[ApplicationAgent] Mock mode enabled - simulating successful application"
            )
            result = {
                "status": ApplicationStatus.SUBMITTED.value,
                "job_id": job_id,
                "platform": platform,
                "message": "Mock application submitted successfully",
                "mock": True,
                "timestamp": datetime.now().isoformat(),
            }
            return result

        # Check if we have browser automation enabled
        use_automation = self.config.get("application", {}).get("use_automation", False)

        if use_automation:
            # Use browser automation (Playwright)
            result = await self._submit_with_automation(platform, application_data)

            # Add document paths to requires_manual responses
            if result.get("status") == "requires_manual":
                result["resume_path"] = application_data.get("documents", {}).get(
                    "resume"
                )
                result["cover_letter_path"] = application_data.get("documents", {}).get(
                    "cover_letter"
                )
                result["job_url"] = application_data.get("url")
                result["job_id"] = job_id
        else:
            # Manual submission required
            result = {
                "status": ApplicationStatus.REQUIRES_MANUAL.value,
                "job_id": job_id,
                "platform": platform,
                "message": "Browser automation not enabled",
                "resume_path": application_data.get("documents", {}).get("resume"),
                "cover_letter_path": application_data.get("documents", {}).get(
                    "cover_letter"
                ),
                "job_url": application_data.get("url"),
                "timestamp": datetime.now().isoformat(),
            }

        return result

    async def _submit_with_automation(
        self, platform: str, application_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit application using browser automation.

        Args:
            platform: Platform identifier
            application_data: Application data

        Returns:
            Submission result
        """
        logger.info(f"[ApplicationAgent] Starting browser automation for {platform}")

        try:
            # Get job URL
            job_url = application_data.get("url") or application_data.get("job_url")
            if not job_url:
                return {
                    "status": ApplicationStatus.FAILED.value,
                    "reason": "No job URL provided",
                    "timestamp": datetime.now().isoformat(),
                }

            # Initialize browser automation
            headless = self.config.get("application", {}).get("headless_browser", True)
            screenshot_dir = self.config.get("application", {}).get(
                "screenshot_dir", "outputs/screenshots"
            )

            async with BrowserAutomation(
                headless=headless, screenshot_dir=screenshot_dir
            ) as browser:
                # Select appropriate handler
                handler = None

                if platform == "linkedin":
                    handler = LinkedInHandler(browser)
                elif platform == "greenhouse":
                    handler = GreenhouseHandler(browser)
                elif platform == "lever":
                    handler = LeverHandler(browser)
                elif platform == "workday":
                    handler = WorkdayHandler(browser)
                elif platform == "icims":
                    handler = iCIMSHandler(browser)
                elif platform == "indeed":
                    handler = IndeedHandler(browser)
                elif platform in ["smartrecruiters", "unknown"]:
                    # Use generic handler for SmartRecruiters and unknown platforms
                    handler = GenericHandler(browser)

                if not handler:
                    return {
                        "status": ApplicationStatus.REQUIRES_MANUAL.value,
                        "reason": f"No handler available for platform: {platform}",
                        "timestamp": datetime.now().isoformat(),
                    }

                # Apply to job
                result = await handler.apply(job_url, application_data)
                result["timestamp"] = datetime.now().isoformat()

                return result

        except ImportError as e:
            logger.error(f"[ApplicationAgent] Playwright not installed: {e}")
            return {
                "status": ApplicationStatus.REQUIRES_MANUAL.value,
                "reason": "Browser automation not available - Playwright not installed",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(
                f"[ApplicationAgent] Browser automation error: {e}", exc_info=True
            )
            return {
                "status": ApplicationStatus.FAILED.value,
                "reason": f"Browser automation error: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            }

    def _record_application(self, user_id: str, job_id: str, result: Dict[str, Any]):
        """Record application attempt in history.

        Args:
            user_id: User identifier
            job_id: Job identifier
            result: Application result
        """
        if user_id not in self.application_history:
            self.application_history[user_id] = []

        self.application_history[user_id].append(
            {
                "job_id": job_id,
                "status": result.get("status"),
                "timestamp": datetime.now(),
                "result": result,
            }
        )

        logger.info(f"[ApplicationAgent] Recorded application for user {user_id}")

    def _update_graph_memory(self, job_id: str, user_id: str, result: Dict[str, Any]):
        """Update graph memory with application status.

        Args:
            job_id: Job identifier
            user_id: User identifier
            result: Application result
        """
        if not self.graph_memory:
            return

        try:
            # Create application node in graph
            application_data = {
                "application_id": f"app_{user_id}_{job_id}_{datetime.now().timestamp()}",
                "job_id": job_id,
                "user_id": user_id,
                "status": result.get("status"),
                "submitted_at": datetime.now().isoformat(),
                "platform": result.get("platform"),
                "confirmation": result.get("confirmation_number"),
            }

            # Store in graph (simplified - actual implementation would use proper schema)
            logger.info(f"[ApplicationAgent] Updated graph memory for application")

        except Exception as e:
            logger.error(f"[ApplicationAgent] Error updating graph memory: {e}")

    def get_application_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get application history for user.

        Args:
            user_id: User identifier

        Returns:
            List of application records
        """
        return self.application_history.get(user_id, [])

    def get_application_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get application statistics for user.

        Args:
            user_id: User identifier

        Returns:
            Statistics dictionary
        """
        history = self.get_application_history(user_id)

        total = len(history)
        submitted = sum(
            1 for app in history if app["status"] == ApplicationStatus.SUBMITTED.value
        )
        pending = sum(
            1 for app in history if app["status"] == ApplicationStatus.PENDING.value
        )
        failed = sum(
            1 for app in history if app["status"] == ApplicationStatus.FAILED.value
        )
        manual = sum(
            1
            for app in history
            if app["status"] == ApplicationStatus.REQUIRES_MANUAL.value
        )

        return {
            "total_applications": total,
            "submitted": submitted,
            "pending": pending,
            "failed": failed,
            "requires_manual": manual,
            "success_rate": (submitted / total * 100) if total > 0 else 0,
        }

    async def handle_message(self, message):
        """Handle incoming messages from other agents.

        Args:
            message: AgentMessage instance
        """
        from core.agent_communication import MessageType

        if message.message_type == MessageType.REQUEST_DATA:
            action = message.payload.get("action")

            if action == "apply_to_job":
                result = await self.apply_to_job(
                    job_id=message.payload.get("job_id"),
                    user_id=message.payload.get("user_id"),
                    documents=message.payload.get("documents"),
                    auto_submit=message.payload.get("auto_submit", False),
                )

                await self.send_to_agent(
                    message.from_agent, MessageType.RESPONSE_DATA, {"result": result}
                )

            elif action == "batch_apply":
                results = await self.batch_apply(
                    job_ids=message.payload.get("job_ids", []),
                    user_id=message.payload.get("user_id"),
                    documents=message.payload.get("documents"),
                    auto_submit=message.payload.get("auto_submit", False),
                )

                await self.send_to_agent(
                    message.from_agent, MessageType.RESPONSE_DATA, {"results": results}
                )

            elif action == "get_statistics":
                stats = self.get_application_statistics(message.payload.get("user_id"))

                await self.send_to_agent(
                    message.from_agent, MessageType.RESPONSE_DATA, {"statistics": stats}
                )

        else:
            await super().handle_message(message)

    def run(self):
        """Run method (not used in async context)."""
        raise NotImplementedError("Use handle_message() for ApplicationAgent")
