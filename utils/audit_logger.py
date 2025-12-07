"""
Comprehensive Audit Logging System for Job Application Agent

This module provides structured logging for all autonomous operations:
- Job searches and results
- Extractions and scoring
- Document generations
- Application submissions
- Agent decisions
- Rate limit events
- Errors and exceptions

Each log category is stored in separate files for easy filtering and analysis.
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from logging.handlers import RotatingFileHandler
import yaml


class AuditLogger:
    """
    Centralized audit logging system for the autonomous agent.

    Features:
    - Separate log files for different event types
    - Structured JSON logging for easy parsing
    - Automatic log rotation
    - Configurable retention policies
    - Sensitive data filtering
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the audit logger with configuration.

        Args:
            config_path: Path to the configuration file
        """
        self.config = self._load_config(config_path)
        self.audit_config = self.config.get("audit", {})
        self.enabled = self.audit_config.get("enabled", True)

        # Create logs directory if it doesn't exist
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Initialize loggers
        self.loggers = {}
        if self.enabled:
            self._setup_loggers()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
            return {}

    def _setup_loggers(self):
        """Set up separate loggers for each log category."""
        log_files = self.audit_config.get("logs", {})
        log_level = getattr(logging, self.audit_config.get("log_level", "INFO"))
        log_format = self.audit_config.get(
            "format", "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        )
        date_format = self.audit_config.get("date_format", "%Y-%m-%d %H:%M:%S")

        retention = self.audit_config.get("retention", {})
        max_bytes = retention.get("max_size_mb", 100) * 1024 * 1024
        backup_count = retention.get("backup_count", 10)

        # Create logger for each category
        categories = [
            "autonomous",
            "applications",
            "documents",
            "decisions",
            "errors",
            "rate_limits",
        ]

        for category in categories:
            log_file = log_files.get(category, f"logs/{category}.log")
            logger = logging.getLogger(f"audit.{category}")
            logger.setLevel(log_level)
            logger.propagate = False

            # Remove existing handlers
            logger.handlers.clear()

            # Add rotating file handler
            handler = RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
            )

            formatter = logging.Formatter(log_format, datefmt=date_format)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            self.loggers[category] = logger

    def _should_log(self, event_type: str) -> bool:
        """Check if this event type should be logged."""
        if not self.enabled:
            return False

        log_events = self.audit_config.get("log_events", {})
        return log_events.get(event_type, True)

    def _sanitize_data(self, data: Dict) -> Dict:
        """Remove sensitive data from logs if configured."""
        if self.audit_config.get("include_sensitive", False):
            return data

        # List of sensitive keys to redact
        sensitive_keys = [
            "password",
            "api_key",
            "token",
            "secret",
            "salary",
            "ssn",
            "email",
            "phone",
        ]

        sanitized = {}
        for key, value in data.items():
            if any(sens in key.lower() for sens in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    def log_job_search(
        self,
        user_id: str,
        keywords: List[str],
        filters: Dict,
        results_count: int,
        source: str = "jsearch",
    ):
        """Log a job search operation."""
        if not self._should_log("job_searches"):
            return

        data = {
            "event": "job_search",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "keywords": keywords,
            "filters": filters,
            "results_count": results_count,
            "source": source,
        }

        self.loggers["autonomous"].info(json.dumps(data))

    def log_extraction(
        self,
        job_id: str,
        job_url: str,
        extraction_time_seconds: float,
        success: bool,
        error: Optional[str] = None,
    ):
        """Log a job information extraction."""
        if not self._should_log("extractions"):
            return

        data = {
            "event": "extraction",
            "timestamp": datetime.now().isoformat(),
            "job_id": job_id,
            "job_url": job_url,
            "extraction_time_seconds": round(extraction_time_seconds, 2),
            "success": success,
            "error": error,
        }

        self.loggers["autonomous"].info(json.dumps(data))

    def log_scoring(
        self,
        user_id: str,
        job_id: str,
        job_title: str,
        match_score: float,
        scoring_time_seconds: float,
        key_factors: List[str],
    ):
        """Log a job scoring operation."""
        if not self._should_log("scoring"):
            return

        data = {
            "event": "scoring",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "job_id": job_id,
            "job_title": job_title,
            "match_score": round(match_score, 2),
            "scoring_time_seconds": round(scoring_time_seconds, 2),
            "key_factors": key_factors,
        }

        self.loggers["autonomous"].info(json.dumps(data))

    def log_document_generation(
        self,
        user_id: str,
        job_id: str,
        document_type: str,  # "resume" or "cover_letter"
        generation_time_seconds: float,
        success: bool,
        file_path: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Log a document generation event."""
        if not self._should_log("documents"):
            return

        data = {
            "event": "document_generation",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "job_id": job_id,
            "document_type": document_type,
            "generation_time_seconds": round(generation_time_seconds, 2),
            "success": success,
            "file_path": file_path,
            "error": error,
        }

        self.loggers["documents"].info(json.dumps(data))

    def log_application_submission(
        self,
        user_id: str,
        job_id: str,
        job_title: str,
        company: str,
        platform: str,
        match_score: float,
        auto_applied: bool,
        success: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """Log an application submission event."""
        if not self._should_log("applications"):
            return

        data = {
            "event": "application_submission",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "job_id": job_id,
            "job_title": job_title,
            "company": company,
            "platform": platform,
            "match_score": round(match_score, 2),
            "auto_applied": auto_applied,
            "success": success,
            "error": error,
            "metadata": self._sanitize_data(metadata or {}),
        }

        self.loggers["applications"].info(json.dumps(data))

    def log_decision(
        self,
        user_id: str,
        job_id: str,
        decision_type: str,  # "auto_apply", "review", "skip"
        match_score: float,
        reason: str,
        metadata: Optional[Dict] = None,
    ):
        """Log an autonomous decision."""
        if not self._should_log("decisions"):
            return

        data = {
            "event": "autonomous_decision",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "job_id": job_id,
            "decision_type": decision_type,
            "match_score": round(match_score, 2),
            "reason": reason,
            "metadata": metadata or {},
        }

        self.loggers["decisions"].info(json.dumps(data))

    def log_rate_limit(
        self,
        provider: str,
        limit_type: str,  # "requests_per_minute", "tokens_per_minute", etc.
        current_usage: int,
        limit: int,
        wait_time_seconds: float,
        operation: str,  # "extraction", "scoring", etc.
    ):
        """Log a rate limit event."""
        if not self._should_log("rate_limits"):
            return

        data = {
            "event": "rate_limit_hit",
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "limit_type": limit_type,
            "current_usage": current_usage,
            "limit": limit,
            "wait_time_seconds": round(wait_time_seconds, 2),
            "operation": operation,
        }

        self.loggers["rate_limits"].info(json.dumps(data))

    def log_error(
        self,
        error_type: str,
        error_message: str,
        operation: str,
        user_id: Optional[str] = None,
        job_id: Optional[str] = None,
        stacktrace: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """Log an error event."""
        if not self._should_log("errors"):
            return

        data = {
            "event": "error",
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "operation": operation,
            "user_id": user_id,
            "job_id": job_id,
            "stacktrace": stacktrace,
            "metadata": metadata or {},
        }

        self.loggers["errors"].error(json.dumps(data))

    def log_cycle_summary(
        self,
        cycle_number: int,
        duration_seconds: float,
        jobs_found: int,
        jobs_scored: int,
        jobs_auto_applied: int,
        jobs_needs_review: int,
        jobs_skipped: int,
        errors_count: int,
    ):
        """Log a summary of an autonomous cycle."""
        data = {
            "event": "cycle_summary",
            "timestamp": datetime.now().isoformat(),
            "cycle_number": cycle_number,
            "duration_seconds": round(duration_seconds, 2),
            "jobs_found": jobs_found,
            "jobs_scored": jobs_scored,
            "jobs_auto_applied": jobs_auto_applied,
            "jobs_needs_review": jobs_needs_review,
            "jobs_skipped": jobs_skipped,
            "errors_count": errors_count,
        }

        self.loggers["autonomous"].info(json.dumps(data))

    def get_application_history(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        platform: Optional[str] = None,
    ) -> List[Dict]:
        """
        Retrieve application history from logs.

        Args:
            user_id: Filter by user ID
            start_date: Filter by start date
            end_date: Filter by end date
            platform: Filter by platform

        Returns:
            List of application events
        """
        applications = []
        log_file = self.audit_config.get("logs", {}).get(
            "applications", "logs/applications.log"
        )

        try:
            with open(log_file, "r") as f:
                for line in f:
                    try:
                        # Parse the log line to extract JSON
                        if " | " in line:
                            json_part = line.split(" | ")[-1].strip()
                            data = json.loads(json_part)

                            # Apply filters
                            if user_id and data.get("user_id") != user_id:
                                continue

                            if platform and data.get("platform") != platform:
                                continue

                            timestamp = datetime.fromisoformat(
                                data.get("timestamp", "")
                            )
                            if start_date and timestamp < start_date:
                                continue
                            if end_date and timestamp > end_date:
                                continue

                            applications.append(data)
                    except (json.JSONDecodeError, ValueError):
                        continue
        except FileNotFoundError:
            pass

        return applications

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get statistics for the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with statistics
        """
        from datetime import timedelta

        start_date = datetime.now() - timedelta(days=days)
        applications = self.get_application_history(start_date=start_date)

        stats = {
            "period_days": days,
            "total_applications": len(applications),
            "successful_applications": sum(
                1 for app in applications if app.get("success")
            ),
            "failed_applications": sum(
                1 for app in applications if not app.get("success")
            ),
            "auto_applied": sum(1 for app in applications if app.get("auto_applied")),
            "manual_applied": sum(
                1 for app in applications if not app.get("auto_applied")
            ),
            "by_platform": {},
            "average_match_score": 0,
        }

        # Calculate platform breakdown
        for app in applications:
            platform = app.get("platform", "unknown")
            stats["by_platform"][platform] = stats["by_platform"].get(platform, 0) + 1

        # Calculate average match score
        if applications:
            total_score = sum(app.get("match_score", 0) for app in applications)
            stats["average_match_score"] = round(total_score / len(applications), 2)

        return stats


# Global audit logger instance
_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
