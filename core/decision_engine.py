"""
Decision Engine - Autonomous decision-making for agent workflows.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Makes intelligent decisions about agent workflows and human involvement."""

    def __init__(self, config: Optional[Any] = None):
        """Initialize decision engine.

        Args:
            config: Optional Config instance for configuration
        """
        self.config = config
        self.application_history: Dict[str, List[datetime]] = {}

        # Load configuration or use defaults
        if config:
            auto_config = config.config.get("autonomous_mode", {}).get("auto_apply", {})
            self.min_auto_apply_score = auto_config.get("min_match_score", 90)
            self.max_applications_per_day = auto_config.get("max_per_day", 10)
            self.trusted_platforms = set(
                auto_config.get(
                    "trusted_platforms", ["linkedin", "greenhouse", "lever", "workday"]
                )
            )
        else:
            self.min_auto_apply_score = 90
            self.max_applications_per_day = 10
            self.trusted_platforms = {"linkedin", "greenhouse", "lever", "workday"}

        logger.info(
            f"[DecisionEngine] Initialized "
            f"(min_score={self.min_auto_apply_score}, "
            f"max_daily={self.max_applications_per_day})"
        )

    def should_auto_apply(
        self,
        user_id: str,
        job: Dict[str, Any],
        form_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, str]:
        """Decide if job application should be auto-submitted.

        Args:
            user_id: User identifier
            job: Job information dictionary
            form_data: Optional form data if form was analyzed

        Returns:
            Tuple of (should_auto_apply: bool, reason: str)
        """
        # Check daily limit
        if not self._check_daily_limit(user_id):
            return False, "Daily application limit reached"

        # Check match score
        match_score = job.get("match_score", 0)
        if match_score < self.min_auto_apply_score:
            return (
                False,
                f"Match score {match_score} below threshold {self.min_auto_apply_score}",
            )

        # Check platform trust
        platform = self._detect_platform(job.get("application_url", ""))
        if platform not in self.trusted_platforms:
            return False, f"Platform '{platform}' not in trusted list"

        # Check for complex requirements
        if self._has_complex_requirements(job):
            return False, "Job has complex requirements (essays/portfolio)"

        # Check form for sensitive fields
        if form_data and self._has_sensitive_fields(form_data):
            return False, "Application contains sensitive fields"

        # All checks passed
        return True, f"Auto-apply approved (score={match_score}, platform={platform})"

    def needs_human_review(
        self, job: Dict[str, Any], documents: Optional[Dict[str, str]] = None
    ) -> tuple[bool, str]:
        """Decide if generated documents need human review.

        Args:
            job: Job information dictionary
            documents: Optional generated documents

        Returns:
            Tuple of (needs_review: bool, reason: str)
        """
        match_score = job.get("match_score", 0)

        # High confidence - no review needed
        if match_score >= 90:
            return False, "High confidence match"

        # Medium confidence - quick review
        if 75 <= match_score < 90:
            return True, "Medium confidence - quick review recommended"

        # Low confidence - thorough review
        if match_score < 75:
            return True, "Low confidence - thorough review required"

        # Complex requirements always need review
        if self._has_complex_requirements(job):
            return True, "Complex requirements detected"

        return False, "No review needed"

    def prioritize_jobs(
        self,
        jobs: List[Dict[str, Any]],
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Prioritize jobs for application.

        Args:
            jobs: List of job dictionaries
            user_preferences: Optional user preferences

        Returns:
            Sorted list of jobs (highest priority first)
        """

        def score_priority(job: Dict[str, Any]) -> float:
            """Calculate priority score."""
            priority = 0.0

            # Match score (40% weight)
            match_score = job.get("match_score", 0)
            priority += (match_score / 100) * 40

            # Recency (20% weight)
            posted_date = job.get("posted_date")
            if posted_date:
                days_ago = (datetime.now() - posted_date).days
                recency_score = max(0, (30 - days_ago) / 30) * 20
                priority += recency_score

            # Platform trust (15% weight)
            platform = self._detect_platform(job.get("application_url", ""))
            if platform in self.trusted_platforms:
                priority += 15

            # Simplicity (15% weight - prefer simple applications)
            if not self._has_complex_requirements(job):
                priority += 15

            # User preferences (10% weight)
            if user_preferences:
                if job.get("location") in user_preferences.get(
                    "preferred_locations", []
                ):
                    priority += 5
                if job.get("employment_type") in user_preferences.get(
                    "employment_types", []
                ):
                    priority += 5

            return priority

        # Sort by priority score
        sorted_jobs = sorted(jobs, key=score_priority, reverse=True)

        logger.info(f"[DecisionEngine] Prioritized {len(sorted_jobs)} jobs")
        return sorted_jobs

    def should_send_follow_up(
        self, application: Dict[str, Any], days_since_application: int
    ) -> tuple[bool, str]:
        """Decide if follow-up email should be sent.

        Args:
            application: Application information
            days_since_application: Days since application was submitted

        Returns:
            Tuple of (should_send: bool, reason: str)
        """
        status = application.get("status", "submitted")

        # Don't follow up if already responded
        if status in ["rejected", "interview_scheduled", "offer_received"]:
            return False, f"Application status is '{status}'"

        # Follow up after 7 days for high-priority jobs
        if days_since_application >= 7:
            match_score = application.get("match_score", 0)
            if match_score >= 85:
                return True, "High priority job, 7+ days since application"

        # Follow up after 14 days for all jobs
        if days_since_application >= 14:
            return True, "Standard follow-up after 14 days"

        return False, "Too early for follow-up"

    def select_application_strategy(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate application strategy for job.

        Args:
            job: Job information dictionary

        Returns:
            Strategy dictionary with recommended approach
        """
        match_score = job.get("match_score", 0)
        platform = self._detect_platform(job.get("application_url", ""))
        has_complex = self._has_complex_requirements(job)

        strategy = {
            "auto_apply": False,
            "generate_documents": True,
            "require_review": False,
            "priority": "medium",
            "estimated_time": 5,  # minutes
        }

        # High match + trusted platform + simple = auto-apply
        if match_score >= 90 and platform in self.trusted_platforms and not has_complex:
            strategy["auto_apply"] = True
            strategy["require_review"] = False
            strategy["priority"] = "high"
            strategy["estimated_time"] = 3

        # Medium match or complex = review required
        elif match_score < 90 or has_complex:
            strategy["auto_apply"] = False
            strategy["require_review"] = True
            strategy["priority"] = "medium" if match_score >= 75 else "low"
            strategy["estimated_time"] = 10 if has_complex else 5

        logger.debug(
            f"[DecisionEngine] Selected strategy for {job.get('title', 'Unknown')}: "
            f"auto_apply={strategy['auto_apply']}, priority={strategy['priority']}"
        )

        return strategy

    def _check_daily_limit(self, user_id: str) -> bool:
        """Check if user has reached daily application limit.

        Args:
            user_id: User identifier

        Returns:
            True if under limit, False if limit reached
        """
        today = datetime.now().date()

        # Initialize history for user if needed
        if user_id not in self.application_history:
            self.application_history[user_id] = []

        # Filter to today's applications
        today_applications = [
            dt for dt in self.application_history[user_id] if dt.date() == today
        ]

        under_limit = len(today_applications) < self.max_applications_per_day

        if not under_limit:
            logger.warning(
                f"[DecisionEngine] User {user_id} reached daily limit "
                f"({len(today_applications)}/{self.max_applications_per_day})"
            )

        return under_limit

    def record_application(self, user_id: str):
        """Record that user submitted an application.

        Args:
            user_id: User identifier
        """
        if user_id not in self.application_history:
            self.application_history[user_id] = []

        self.application_history[user_id].append(datetime.now())

        # Clean up old entries (keep last 30 days)
        cutoff = datetime.now() - timedelta(days=30)
        self.application_history[user_id] = [
            dt for dt in self.application_history[user_id] if dt > cutoff
        ]

    def _detect_platform(self, url: str) -> str:
        """Detect platform from application URL.

        Args:
            url: Application URL

        Returns:
            Platform name
        """
        url_lower = url.lower()

        if "linkedin.com" in url_lower:
            return "linkedin"
        elif "greenhouse.io" in url_lower or "greenhouse" in url_lower:
            return "greenhouse"
        elif "lever.co" in url_lower:
            return "lever"
        elif "workday" in url_lower or "myworkdayjobs" in url_lower:
            return "workday"
        elif "smartrecruiters" in url_lower:
            return "smartrecruiters"
        elif "icims" in url_lower:
            return "icims"
        else:
            return "unknown"

    def _has_complex_requirements(self, job: Dict[str, Any]) -> bool:
        """Check if job has complex requirements.

        Args:
            job: Job information dictionary

        Returns:
            True if complex requirements detected
        """
        description = job.get("description", "").lower()
        qualifications = job.get("qualifications", "").lower()
        combined_text = f"{description} {qualifications}"

        complex_indicators = [
            "cover letter required",
            "portfolio required",
            "portfolio link",
            "why do you want",
            "why are you interested",
            "writing sample",
            "work sample",
            "take-home assignment",
            "coding challenge",
            "essay question",
        ]

        return any(indicator in combined_text for indicator in complex_indicators)

    def _has_sensitive_fields(self, form_data: Dict[str, Any]) -> bool:
        """Check if form contains sensitive fields.

        Args:
            form_data: Form field data

        Returns:
            True if sensitive fields detected
        """
        sensitive_patterns = [
            "salary",
            "compensation",
            "ssn",
            "social security",
            "references",
            "legal",
            "authorization",
            "visa",
            "citizenship",
            "background check",
        ]

        # Check field names/labels
        for field_name in form_data.keys():
            field_lower = field_name.lower()
            if any(pattern in field_lower for pattern in sensitive_patterns):
                logger.info(f"[DecisionEngine] Sensitive field detected: {field_name}")
                return True

        return False

    def get_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get decision statistics for user.

        Args:
            user_id: User identifier

        Returns:
            Statistics dictionary
        """
        today = datetime.now().date()
        history = self.application_history.get(user_id, [])

        today_count = sum(1 for dt in history if dt.date() == today)
        week_count = sum(1 for dt in history if dt.date() >= today - timedelta(days=7))

        return {
            "applications_today": today_count,
            "applications_this_week": week_count,
            "remaining_today": max(0, self.max_applications_per_day - today_count),
            "daily_limit": self.max_applications_per_day,
            "min_auto_apply_score": self.min_auto_apply_score,
        }
