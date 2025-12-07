"""
Tests for DecisionEngine.
"""

import pytest
from datetime import datetime, timedelta
from core.decision_engine import DecisionEngine
from core.config import Config


class TestDecisionEngine:
    """Test DecisionEngine logic."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        config = Config()
        # Override autonomous settings for testing
        config.config_data["autonomous_mode"] = {
            "enabled": True,
            "min_score_auto_apply": 90,
            "trusted_platforms": ["linkedin", "greenhouse"],
            "daily_application_limit": 10,
            "rate_limit_per_hour": 3,
        }
        return config

    @pytest.fixture
    def engine(self, config):
        """Create DecisionEngine with test config."""
        return DecisionEngine(config)

    def test_should_auto_apply_high_score(self, engine):
        """Test auto-apply with high match score."""
        job = {
            "job_id": "job1",
            "match_score": 95,
            "url": "https://linkedin.com/jobs/123",
            "title": "Software Engineer",
        }

        form_data = {}

        should_apply, reason = engine.should_auto_apply("user1", job, form_data)

        assert should_apply
        assert "high confidence" in reason.lower()

    def test_should_not_auto_apply_low_score(self, engine):
        """Test no auto-apply with low score."""
        job = {
            "job_id": "job1",
            "match_score": 75,
            "url": "https://linkedin.com/jobs/123",
            "title": "Software Engineer",
        }

        should_apply, reason = engine.should_auto_apply("user1", job, {})

        assert not should_apply
        assert "score" in reason.lower()

    def test_should_not_auto_apply_untrusted_platform(self, engine):
        """Test no auto-apply for untrusted platform."""
        job = {
            "job_id": "job1",
            "match_score": 95,
            "url": "https://unknown-site.com/jobs/123",
            "title": "Software Engineer",
        }

        should_apply, reason = engine.should_auto_apply("user1", job, {})

        assert not should_apply
        assert "platform" in reason.lower()

    def test_should_not_auto_apply_complex_requirements(self, engine):
        """Test no auto-apply with complex requirements."""
        job = {
            "job_id": "job1",
            "match_score": 95,
            "url": "https://linkedin.com/jobs/123",
            "title": "Software Engineer",
            "description": "Please provide a cover letter and portfolio",
        }

        should_apply, reason = engine.should_auto_apply("user1", job, {})

        assert not should_apply
        assert "complex" in reason.lower()

    def test_should_not_auto_apply_sensitive_fields(self, engine):
        """Test no auto-apply with sensitive form fields."""
        job = {
            "job_id": "job1",
            "match_score": 95,
            "url": "https://linkedin.com/jobs/123",
            "title": "Software Engineer",
        }

        form_data = {"salary_expectations": "", "ssn": ""}

        should_apply, reason = engine.should_auto_apply("user1", job, form_data)

        assert not should_apply
        assert "sensitive" in reason.lower()

    def test_daily_limit_enforcement(self, engine):
        """Test daily application limit."""
        job = {
            "job_id": "job1",
            "match_score": 95,
            "url": "https://linkedin.com/jobs/123",
            "title": "Software Engineer",
        }

        # Apply to 10 jobs (limit)
        for i in range(10):
            engine.record_application("user1")

        # 11th should be rejected
        should_apply, reason = engine.should_auto_apply("user1", job, {})

        assert not should_apply
        assert "daily limit" in reason.lower()

    def test_needs_human_review_low_confidence(self, engine):
        """Test human review for low confidence."""
        job = {"match_score": 70}

        documents = {}

        needs_review, reason = engine.needs_human_review(job, documents)

        assert needs_review
        assert "thorough review" in reason.lower()

    def test_no_review_needed_high_confidence(self, engine):
        """Test no review for high confidence."""
        job = {"match_score": 95}

        needs_review, reason = engine.needs_human_review(job, {})

        assert not needs_review
        assert "high confidence" in reason.lower()

    def test_prioritize_jobs(self, engine):
        """Test job prioritization."""
        jobs = [
            {
                "job_id": "job1",
                "match_score": 85,
                "posted_date": (datetime.now() - timedelta(days=5)).isoformat(),
                "url": "https://linkedin.com/jobs/1",
                "description": "Simple application",
            },
            {
                "job_id": "job2",
                "match_score": 95,
                "posted_date": (datetime.now() - timedelta(days=1)).isoformat(),
                "url": "https://greenhouse.io/jobs/2",
                "description": "Easy apply",
            },
            {
                "job_id": "job3",
                "match_score": 75,
                "posted_date": (datetime.now() - timedelta(days=10)).isoformat(),
                "url": "https://example.com/jobs/3",
                "description": "Complex requirements",
            },
        ]

        preferences = {}

        prioritized = engine.prioritize_jobs(jobs, preferences)

        # job2 should be first (high score, recent, trusted platform)
        assert prioritized[0]["job_id"] == "job2"
        assert prioritized[0]["priority_score"] > prioritized[1]["priority_score"]

    def test_should_send_follow_up(self, engine):
        """Test follow-up timing logic."""
        # High priority - 7 days
        high_priority_app = {
            "job_id": "job1",
            "match_score": 90,
            "applied_date": (datetime.now() - timedelta(days=8)).isoformat(),
        }

        should_follow_up, reason = engine.should_send_follow_up(
            high_priority_app, days=7
        )
        assert should_follow_up

        # Standard priority - 14 days
        standard_app = {
            "job_id": "job2",
            "match_score": 80,
            "applied_date": (datetime.now() - timedelta(days=10)).isoformat(),
        }

        should_follow_up, reason = engine.should_send_follow_up(standard_app, days=14)
        assert not should_follow_up  # Not 14 days yet

    def test_select_application_strategy(self, engine):
        """Test application strategy selection."""
        # High confidence job
        high_confidence_job = {
            "match_score": 95,
            "url": "https://linkedin.com/jobs/1",
            "description": "Simple application",
        }

        strategy = engine.select_application_strategy(high_confidence_job)

        assert strategy["auto_apply"]
        assert strategy["generate_documents"]
        assert not strategy["require_review"]
        assert strategy["priority"] == "high"

        # Low confidence job
        low_confidence_job = {
            "match_score": 70,
            "url": "https://unknown.com/jobs/1",
            "description": "Complex requirements with portfolio",
        }

        strategy = engine.select_application_strategy(low_confidence_job)

        assert not strategy["auto_apply"]
        assert strategy["require_review"]
        assert strategy["priority"] == "medium"

    def test_platform_detection(self, engine):
        """Test platform detection from URL."""
        test_cases = [
            ("https://linkedin.com/jobs/123", "linkedin"),
            ("https://boards.greenhouse.io/company/jobs/456", "greenhouse"),
            ("https://jobs.lever.co/company/789", "lever"),
            ("https://company.wd1.myworkdayjobs.com/careers", "workday"),
            ("https://example.com/careers", "unknown"),
        ]

        for url, expected_platform in test_cases:
            platform = engine._detect_platform(url)
            assert platform == expected_platform

    def test_complex_requirements_detection(self, engine):
        """Test detection of complex job requirements."""
        complex_descriptions = [
            "Please provide a cover letter and portfolio",
            "Submit writing samples with your application",
            "Include a personal essay",
            "Portfolio required",
        ]

        for desc in complex_descriptions:
            assert engine._has_complex_requirements(desc)

        simple_desc = "Apply with your resume"
        assert not engine._has_complex_requirements(simple_desc)

    def test_sensitive_fields_detection(self, engine):
        """Test detection of sensitive form fields."""
        sensitive_forms = [
            {"salary_expectations": ""},
            {"current_salary": ""},
            {"ssn": ""},
            {"social_security": ""},
            {"references": ""},
            {"visa_status": ""},
        ]

        for form in sensitive_forms:
            assert engine._has_sensitive_fields(form)

        normal_form = {"name": "", "email": "", "phone": ""}
        assert not engine._has_sensitive_fields(normal_form)

    def test_statistics(self, engine):
        """Test application statistics."""
        # Record some applications
        for i in range(5):
            engine.record_application("user1")

        stats = engine.get_statistics("user1")

        assert stats["applications_today"] == 5
        assert stats["applications_this_week"] == 5
        assert stats["daily_limit"] == 10
        assert stats["remaining_today"] == 5

    def test_history_cleanup(self, engine):
        """Test old application history cleanup."""
        user_id = "user1"

        # Add old applications (35 days ago)
        old_date = datetime.now() - timedelta(days=35)
        for i in range(3):
            engine.application_history[user_id].append(
                {"timestamp": old_date, "job_id": f"old_job_{i}"}
            )

        # Add recent applications
        for i in range(2):
            engine.record_application(user_id)

        # Should have 5 total now
        assert len(engine.application_history[user_id]) == 5

        # Cleanup (removes >30 days old)
        engine._cleanup_old_applications(user_id)

        # Should only have 2 recent ones
        assert len(engine.application_history[user_id]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
