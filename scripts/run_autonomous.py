"""
Autonomous Job Application Agent Runner
Continuously searches for jobs and applies based on configured preferences.
"""

import asyncio
import sys
import argparse
import signal
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.live import Live
from rich import box

# Import agents and core components
import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.orchestrator_agent import OrchestratorAgent
from agents.scout_agent import ScoutAgent
from agents.extractor_agent import ExtractorAgent
from agents.matcher_agent import MatcherAgent
from agents.writer_agent import WriterAgent
from agents.application_agent import ApplicationAgent
from agents.tracker_agent import TrackerAgent
from core.config import Config
from core.user_profile import UserProfile
from core.agent_communication import AgentMessage, MessageType
from graph.memory import GraphMemory
from utils.audit_logger import get_audit_logger

console = Console()


class AutonomousRunner:
    """Main autonomous runner that coordinates all agents."""

    def __init__(self, config_path: str = None):
        """Initialize the autonomous runner.

        Args:
            config_path: Path to configuration file (defaults to ../config.yaml)
        """
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "config.yaml")
        self.config = Config(config_path)
        self.console = Console()
        self.running = False
        self.paused = False
        self.stop_requested = False

        # Stats tracking
        self.stats = {
            "total_applications": 0,
            "today_applications": 0,
            "cycle_count": 0,
            "last_cycle_time": None,
            "jobs_found": 0,
            "high_matches": 0,
            "medium_matches": 0,
            "low_matches": 0,
            "start_time": datetime.now(),
        }

        # Load state file if exists
        self.state_file = Path(".agent_state.json")
        self._load_state()

        # Initialize audit logger
        self.audit_logger = get_audit_logger()

        # Initialize components
        self._initialize_components()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _initialize_components(self):
        """Initialize all agents and components."""
        try:
            # Initialize graph memory
            self.graph_memory = GraphMemory(
                uri=self.config.neo4j_uri,
                user=self.config.neo4j_user,
                password=self.config.neo4j_password,
                database=self.config.neo4j_database,
            )

            # Load user profile
            self.user_profile = UserProfile(self.graph_memory)

            # Initialize orchestrator
            self.orchestrator = OrchestratorAgent(
                graph_memory=self.graph_memory,
                config=self.config,
                user_profile=self.user_profile,
            )

            # Initialize LLM client for ExtractorAgent
            from llm.llm_client import LLMClient

            llm_config = self.config.get_llm_config()
            llm_client = LLMClient(llm_config)

            # Initialize and register agents
            self.scout = ScoutAgent(self.graph_memory, self.config)
            self.extractor = ExtractorAgent(self.graph_memory, llm_client)
            self.matcher = MatcherAgent(
                self.graph_memory, self.config, self.user_profile
            )
            self.writer = WriterAgent(self.graph_memory, self.config, self.user_profile)
            self.application = ApplicationAgent(self.graph_memory, self.config)
            self.tracker = TrackerAgent(self.graph_memory)

            # Register all agents with orchestrator
            self.orchestrator.register_agent("scout", self.scout)
            self.orchestrator.register_agent("extractor", self.extractor)
            self.orchestrator.register_agent("matcher", self.matcher)
            self.orchestrator.register_agent("writer", self.writer)
            self.orchestrator.register_agent("application", self.application)
            self.orchestrator.register_agent("tracker", self.tracker)

            self.console.print(
                "[green]✓[/green] All components initialized successfully"
            )

        except Exception as e:
            self.console.print(f"[red]✗[/red] Failed to initialize: {e}")
            raise

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.console.print("\n[yellow]⚠[/yellow] Received shutdown signal...")
        self.stop_requested = True
        # Force exit on second signal
        if hasattr(self, "_shutdown_count"):
            self._shutdown_count += 1
            if self._shutdown_count > 1:
                self.console.print("[red]✗[/red] Force exit!")
                import sys

                sys.exit(1)
        else:
            self._shutdown_count = 1
        # Raise KeyboardInterrupt to break out of async operations
        raise KeyboardInterrupt()

    def _load_state(self):
        """Load previous state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    saved_state = json.load(f)
                    self.stats.update(saved_state.get("stats", {}))
                    self.stats["start_time"] = datetime.fromisoformat(
                        saved_state.get("start_time", datetime.now().isoformat())
                    )
                    self.paused = saved_state.get("paused", False)
            except Exception as e:
                self.console.print(
                    f"[yellow]Warning:[/yellow] Could not load state: {e}"
                )

    def _save_state(self):
        """Save current state to file."""
        try:
            state = {
                "stats": self.stats,
                "start_time": self.stats["start_time"].isoformat(),
                "paused": self.paused,
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            self.console.print(f"[yellow]Warning:[/yellow] Could not save state: {e}")

    def _print_banner(self):
        """Print startup banner."""
        banner = """
╔════════════════════════════════════════════════════════════════╗
║        🤖 JOB APPLICATION AGENT - AUTONOMOUS MODE             ║
╚════════════════════════════════════════════════════════════════╝
        """
        self.console.print(banner, style="bold cyan")

    def _print_config(self):
        """Print current configuration."""
        auto_config = self.config.autonomous_config

        # Get user_id from config
        user_id = self.config.config.get("app", {}).get("user_id", "default_user")

        # Get user profile info
        user_info = self.user_profile.get_profile(user_id)
        if not user_info:
            self.console.print(
                f"[yellow]⚠[/yellow] No user profile found for '{user_id}'. Run setup_profile.py first."
            )
            sys.exit(1)

        full_name = user_info.get("name", user_info.get("full_name", "Unknown"))
        preferences = self.user_profile.get_search_preferences(user_id)
        job_titles = preferences.get(
            "preferred_roles", preferences.get("job_titles", [])
        )

        config_panel = f"""
[bold]Profile:[/bold] {full_name}
[bold]Target Roles:[/bold] {', '.join(job_titles[:3]) if job_titles else 'Not set'}

[bold]Configuration:[/bold]
  • Search interval: {auto_config.get('search_interval_hours', 6)} hours
  • Auto-apply threshold: ≥{auto_config.get('auto_apply_threshold', 90)}% match
  • Daily limit: {auto_config.get('max_applications_per_day', 10)} applications
  • Review medium matches: {'Yes' if auto_config.get('review_medium_matches', True) else 'No'}
        """

        self.console.print(
            Panel(config_panel, title="[bold]Settings[/bold]", border_style="blue")
        )

    async def _search_and_score_jobs(self, user_id: str) -> Dict[str, Any]:
        """Search for jobs and score them.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with job lists by score category
        """
        self.console.print(
            f"\n[cyan]🔍[/cyan] Starting job search cycle {self.stats['cycle_count'] + 1}..."
        )

        # Get user preferences
        user_info = self.user_profile.get_profile(user_id)
        preferences = self.user_profile.get_search_preferences(user_id)
        job_titles = preferences.get(
            "preferred_roles", preferences.get("job_titles", ["Software Engineer"])
        )

        # Search for jobs
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Searching for jobs...", total=None)

            all_job_ids = []
            search_failed = False

            # For free tier: search only 1 job title with 2 results to avoid rate limits
            for title in job_titles:  # Search top 1 job title only
                # Get employment type from preferences (use first one if multiple)
                emp_types = preferences.get("employment_types", ["FULLTIME", "INTERN"])
                emp_type = emp_types[0] if emp_types else "FULLTIME"

                self.console.print(
                    f"[cyan]📡[/cyan] Searching for: [bold]{title}[/bold]"
                )
                self.console.print(
                    f"[dim]  Parameters: date_posted=week, employment_type={emp_type}, max_results=10[/dim]"
                )

                search_params = {
                    "keywords": title,
                    "date_posted": preferences.get("date_posted", "week"),
                    "employment_type": emp_type,
                    "max_results": 5,  # Get 5 jobs for faster processing
                    "api_source": "jsearch",
                }

                try:
                    # Request job search from scout
                    message = AgentMessage(
                        from_agent="autonomous_runner",
                        to_agent="scout",
                        message_type=MessageType.REQUEST_DATA,
                        payload=search_params,
                        requires_response=True,
                    )
                    response = await self.orchestrator.communication_bus.send_message(
                        message, timeout=90
                    )

                    if response and response.get("status") == "success":
                        job_ids = response.get("job_ids", [])
                        all_job_ids.extend(job_ids)

                        # Show found jobs immediately
                        if job_ids:
                            self.console.print(
                                f"[green]✓[/green] Found {len(job_ids)} jobs:"
                            )
                            for job_id in job_ids:
                                job_info = self.graph_memory.get_job(job_id)
                                if job_info:
                                    title = job_info.get(
                                        "job_title",
                                        job_info.get("title", "Position Not Listed"),
                                    )
                                    company = job_info.get(
                                        "company_name",
                                        job_info.get("company", "Company Not Listed"),
                                    )
                                    location = job_info.get(
                                        "location",
                                        job_info.get(
                                            "job_location", "Location Not Listed"
                                        ),
                                    )
                                    self.console.print(
                                        f"  • {title} @ {company} ({location})"
                                    )
                        else:
                            self.console.print(
                                f"[yellow]⚠[/yellow] No new jobs found for '{title}'"
                            )

                        # Log job search
                        self.audit_logger.log_job_search(
                            user_id=user_id,
                            keywords=[title],
                            filters={
                                "date_posted": preferences.get("date_posted", "week"),
                                "employment_type": emp_type,
                            },
                            results_count=len(job_ids),
                            source=search_params.get("api_source", "jsearch"),
                        )
                    else:
                        self.console.print(
                            f"[yellow]⚠[/yellow] Search failed for '{title}': {response.get('error', 'Unknown error')}"
                        )
                        search_failed = True

                except Exception as e:
                    self.console.print(
                        f"[yellow]⚠[/yellow] Search error for '{title}': {str(e)}"
                    )
                    search_failed = True

            progress.update(task, description=f"Found {len(all_job_ids)} jobs")

        if search_failed and not all_job_ids:
            self.console.print(
                "[red]✗[/red] All job searches failed. This may be due to API timeouts or rate limits."
            )
            self.console.print(
                "[yellow]ℹ[/yellow] The system will try again in the next cycle."
            )
            return {"high": [], "medium": [], "low": []}

        # Filter out jobs that have already been scored for this user (single query)
        existing_matches = self.graph_memory.get_user_matches(
            user_id, min_score=0.0, limit=1000
        )
        existing_job_ids = {match.get("job_id") for match in existing_matches}

        new_job_ids = []
        already_scored = 0

        for job_id in all_job_ids:
            if job_id not in existing_job_ids:
                new_job_ids.append(job_id)
            else:
                already_scored += 1

        all_job_ids = new_job_ids
        self.stats["jobs_found"] += len(all_job_ids)

        if already_scored > 0:
            self.console.print(
                f"[yellow]ℹ[/yellow] Skipped {already_scored} already-analyzed job(s)"
            )

        if all_job_ids:
            self.console.print(
                f"\n[green]✓[/green] {len(all_job_ids)} new job(s) to analyze:"
            )
            for job_id in all_job_ids:
                job_info = self.graph_memory.get_job(job_id)
                if job_info:
                    title = job_info.get(
                        "job_title", job_info.get("title", "Position Not Listed")
                    )
                    company = job_info.get(
                        "company_name", job_info.get("company", "Company Not Listed")
                    )
                    self.console.print(f"  • {title} @ {company}")

        if not all_job_ids:
            self.console.print("[yellow]ℹ[/yellow] No new jobs to process this cycle")
            return {"high": [], "medium": [], "low": []}

        # Extract job information sequentially (one at a time for free tier)
        if self.stop_requested:
            return {"high": [], "medium": [], "low": []}

        self.console.print(
            f"[cyan]🔬[/cyan] Analyzing {len(all_job_ids)} jobs sequentially (free tier mode)..."
        )

        # Process jobs one at a time with 2-second delays to respect rate limits
        import asyncio
        import time

        for idx, job_id in enumerate(all_job_ids):
            if self.stop_requested:
                break

            self.console.print(
                f"[dim]  Analyzing job {idx+1}/{len(all_job_ids)}...[/dim]"
            )

            # Track extraction time
            extract_start = time.time()

            message = AgentMessage(
                from_agent="autonomous_runner",
                to_agent="extractor",
                message_type=MessageType.REQUEST_DATA,
                payload={"job_id": job_id},  # Single job instead of batch
                requires_response=True,
            )
            extract_response = await self.orchestrator.communication_bus.send_message(
                message, timeout=60
            )

            extract_time = time.time() - extract_start

            # Log extraction
            job_info = self.graph_memory.get_job(job_id)
            self.audit_logger.log_extraction(
                job_id=job_id,
                job_url=job_info.get("job_apply_link", "") if job_info else "",
                extraction_time_seconds=extract_time,
                success=(
                    extract_response and extract_response.get("status") == "success"
                ),
                error=(
                    extract_response.get("error") if extract_response else "No response"
                ),
            )

            # Add 3-second delay between extractions for free tier
            if idx < len(all_job_ids) - 1:
                await asyncio.sleep(3.0)

        # Score jobs
        if self.stop_requested:
            return {"high": [], "medium": [], "low": []}

        self.console.print("[cyan]🎯[/cyan] Scoring job matches...")

        # Track scoring time
        score_start = time.time()

        message = AgentMessage(
            from_agent="autonomous_runner",
            to_agent="matcher",
            message_type=MessageType.REQUEST_DATA,
            payload={
                "user_id": user_id,
                "job_ids": all_job_ids,  # Score all jobs - sequential processing with 6s delays prevents rate limits
                "batch_size": 1,  # Process 1 job at a time with delays
            },
            requires_response=True,
        )
        score_response = await self.orchestrator.communication_bus.send_message(
            message, timeout=120
        )

        score_time = time.time() - score_start

        if not score_response or score_response.get("status") != "success":
            self.console.print("[yellow]⚠[/yellow] Failed to score jobs")
            return {"high": [], "medium": [], "low": []}

        # Get scored jobs from graph
        # score_response.results contains summary stats, we need actual job matches
        scored_jobs = self.graph_memory.get_user_matches(
            user_id, min_score=0.0, limit=100
        )

        if not scored_jobs:
            self.console.print("[yellow]⚠[/yellow] No scored jobs found")
            return {"high": [], "medium": [], "low": []}

        # Categorize jobs by score
        auto_threshold = self.config.autonomous_config.get("auto_apply_threshold", 90)
        review_threshold = self.config.autonomous_config.get("review_threshold", 75)

        categorized = {"high": [], "medium": [], "low": []}

        for job in scored_jobs:
            score = job.get("match_score", 0)
            if score >= auto_threshold:
                categorized["high"].append(job)
                self.stats["high_matches"] += 1

                # Log scoring for high matches
                self.audit_logger.log_scoring(
                    user_id=user_id,
                    job_id=job.get("job_id", ""),
                    job_title=job.get("job_title", "Unknown"),
                    match_score=score,
                    scoring_time_seconds=score_time
                    / len(all_job_ids),  # Average per job
                    key_factors=job.get("key_factors", []),
                )

            elif score >= review_threshold:
                categorized["medium"].append(job)
                self.stats["medium_matches"] += 1

                # Log scoring for medium matches
                self.audit_logger.log_scoring(
                    user_id=user_id,
                    job_id=job.get("job_id", ""),
                    job_title=job.get("job_title", "Unknown"),
                    match_score=score,
                    scoring_time_seconds=score_time / len(all_job_ids),
                    key_factors=job.get("key_factors", []),
                )

            else:
                categorized["low"].append(job)
                self.stats["low_matches"] += 1

        # Print match summary
        self._print_match_summary(categorized)

        return categorized

    def _print_match_summary(self, categorized: Dict[str, List]):
        """Print summary of matched jobs."""
        table = Table(title="Match Results", box=box.ROUNDED)
        table.add_column("Job Title", style="cyan")
        table.add_column("Company", style="magenta")
        table.add_column("Score", style="green")
        table.add_column("Action", style="yellow")

        # Show high matches
        for job in categorized["high"][:5]:
            table.add_row(
                job.get("job_title", job.get("title", "Unknown"))[:30],
                job.get("company_name", job.get("company", "Unknown"))[:20],
                f"{job.get('match_score', 0)}%",
                "AUTO ✓",
            )

        # Show medium matches
        for job in categorized["medium"][:5]:
            table.add_row(
                job.get("job_title", job.get("title", "Unknown"))[:30],
                job.get("company_name", job.get("company", "Unknown"))[:20],
                f"{job.get('match_score', 0)}%",
                "REVIEW ?",
            )

        if len(categorized["high"]) + len(categorized["medium"]) > 10:
            table.add_row("...", "...", "...", "...")

        self.console.print(table)

        summary = f"""
[bold]Summary:[/bold]
  • Excellent (≥90%): {len(categorized['high'])} jobs
  • Good (75-89%): {len(categorized['medium'])} jobs  
  • Fair (<75%): {len(categorized['low'])} jobs
        """
        self.console.print(summary)

    async def _apply_to_jobs(
        self, user_id: str, jobs: List[Dict], auto: bool = True
    ) -> int:
        """Apply to a list of jobs.

        Args:
            user_id: User identifier
            jobs: List of job dictionaries with match scores
            auto: Whether this is auto-apply or manual

        Returns:
            Number of successful applications
        """
        max_per_day = self.config.autonomous_config.get("max_applications_per_day", 10)
        remaining = max_per_day - self.stats["today_applications"]

        if remaining <= 0:
            self.console.print("[yellow]⚠[/yellow] Daily limit reached")
            return 0

        jobs_to_apply = jobs[:remaining]
        applied_count = 0

        action_type = "Auto-applying" if auto else "Applying"
        self.console.print(
            f"\n[cyan]🤖[/cyan] {action_type} to {len(jobs_to_apply)} job(s)..."
        )

        for job in jobs_to_apply:
            try:
                job_id = job.get("job_id")
                job_title = job.get("job_title", job.get("title", "Unknown"))
                company = job.get("company_name", job.get("company", "Unknown"))
                match_score = job.get("match_score", 0)

                self.console.print(
                    f"\n[cyan]📝[/cyan] Processing: {job_title} @ {company}"
                )
                self.console.print(f"  [dim]Match score: {match_score}%[/dim]")

                # Log decision
                decision_type = "auto_apply" if auto else "manual_apply"
                self.audit_logger.log_decision(
                    user_id=user_id,
                    job_id=job_id,
                    decision_type=decision_type,
                    match_score=match_score,
                    reason=f"Score {match_score}% >= threshold",
                    metadata={"job_title": job_title, "company": company},
                )

                # Generate cover letter
                self.console.print(f"  [cyan]✍️  Generating cover letter...[/cyan]")
                doc_start = time.time()
                message = AgentMessage(
                    from_agent="autonomous_runner",
                    to_agent="writer",
                    message_type=MessageType.REQUEST_DATA,
                    payload={
                        "user_id": user_id,
                        "job_id": job_id,
                        "document_type": "cover_letter",
                        "match_insights": job.get("match_insights", {}),
                    },
                    requires_response=True,
                )
                cover_letter_response = (
                    await self.orchestrator.communication_bus.send_message(
                        message, timeout=60
                    )
                )

                cover_letter_time = time.time() - doc_start

                # Log cover letter generation
                self.audit_logger.log_document_generation(
                    user_id=user_id,
                    job_id=job_id,
                    document_type="cover_letter",
                    generation_time_seconds=cover_letter_time,
                    success=(
                        cover_letter_response
                        and cover_letter_response.get("status") == "success"
                    ),
                    file_path=(
                        cover_letter_response.get("file_path")
                        if cover_letter_response
                        else None
                    ),
                    error=(
                        cover_letter_response.get("error")
                        if cover_letter_response
                        else "No response"
                    ),
                )

                if (
                    not cover_letter_response
                    or cover_letter_response.get("status") != "success"
                ):
                    self.console.print(f"[red]✗[/red] Failed to generate cover letter")
                    continue
                else:
                    cover_letter_path = cover_letter_response.get(
                        "file_path", "unknown"
                    )
                    self.console.print(
                        f"  [green]✓[/green] Cover letter generated: [dim]{cover_letter_path}[/dim]"
                    )

                # Generate tailored resume
                self.console.print(f"  [cyan]✍️  Generating tailored resume...[/cyan]")
                resume_start = time.time()

                message = AgentMessage(
                    from_agent="autonomous_runner",
                    to_agent="writer",
                    message_type=MessageType.REQUEST_DATA,
                    payload={
                        "user_id": user_id,
                        "job_id": job_id,
                        "document_type": "resume",
                        "match_insights": job.get("match_insights", {}),
                    },
                    requires_response=True,
                )
                resume_response = (
                    await self.orchestrator.communication_bus.send_message(
                        message, timeout=60
                    )
                )

                resume_time = time.time() - resume_start

                # Log resume generation
                if resume_response:
                    self.audit_logger.log_document_generation(
                        user_id=user_id,
                        job_id=job_id,
                        document_type="resume",
                        generation_time_seconds=resume_time,
                        success=(resume_response.get("status") == "success"),
                        file_path=resume_response.get("file_path"),
                        error=resume_response.get("error"),
                    )
                    if resume_response.get("status") == "success":
                        resume_path = resume_response.get("file_path", "unknown")
                        self.console.print(
                            f"  [green]✓[/green] Resume generated: [dim]{resume_path}[/dim]"
                        )

                # Submit application (auto_submit=True because we're ready to apply)
                self.console.print(f"  [cyan]🚀 Submitting application...[/cyan]")
                app_response = await self.application.apply_to_job(
                    job_id=job_id,
                    user_id=user_id,
                    documents={
                        "cover_letter": cover_letter_response.get("file_path"),
                        "resume": (
                            resume_response.get("file_path")
                            if resume_response
                            else None
                        ),
                    },
                    auto_submit=True,
                )

                # Determine platform (simplified - would need to get from job info)
                job_info = self.graph_memory.get_job(job_id)
                platform = (
                    job_info.get("platform", "unknown") if job_info else "unknown"
                )

                # Log application submission
                self.audit_logger.log_application_submission(
                    user_id=user_id,
                    job_id=job_id,
                    job_title=job_title,
                    company=company,
                    platform=platform,
                    match_score=match_score,
                    auto_applied=auto,
                    success=(app_response.get("status") in ["success", "submitted"]),
                    error=(
                        app_response.get("message") or app_response.get("reason")
                        if app_response.get("status") not in ["success", "submitted"]
                        else None
                    ),
                    metadata={
                        "cover_letter": cover_letter_response.get("file_path"),
                        "resume": (
                            resume_response.get("file_path")
                            if resume_response
                            else None
                        ),
                    },
                )

                if app_response.get("status") in ["success", "submitted"]:
                    # Track application
                    message = AgentMessage(
                        from_agent="autonomous_runner",
                        to_agent="tracker",
                        message_type=MessageType.REQUEST_DATA,
                        payload={
                            "action": "create",
                            "user_id": user_id,
                            "job_id": job_id,
                            "match_score": job.get("match_score", 0),
                        },
                        requires_response=True,
                    )
                    tracker_response = (
                        await self.orchestrator.communication_bus.send_message(
                            message, timeout=10
                        )
                    )

                    # Show success message with mock indicator if applicable
                    if app_response.get("mock"):
                        self.console.print(
                            f"[green]✓[/green] Application submitted successfully [dim](mock mode)[/dim]"
                        )
                    else:
                        self.console.print(
                            f"[green]✓[/green] Application submitted successfully"
                        )

                    # Show tracker confirmation
                    if tracker_response and tracker_response.get("status") == "success":
                        app_record_id = tracker_response.get(
                            "application_id", "unknown"
                        )
                        self.console.print(
                            f"  [cyan]📊 TrackerAgent:[/cyan] [dim]Created application record ({app_record_id})[/dim]"
                        )

                    applied_count += 1
                    self.stats["today_applications"] += 1
                    self.stats["total_applications"] += 1
                elif app_response.get("status") == "requires_manual":
                    # Browser automation couldn't complete - provide documents for manual application
                    self.console.print(
                        f"[yellow]📋[/yellow] Manual application required for {job_title}"
                    )
                    reason = (
                        app_response.get("reason")
                        or app_response.get("message")
                        or "Browser automation could not complete"
                    )
                    self.console.print(f"  [dim]{reason}[/dim]")

                    self.console.print(f"  [cyan]Generated documents:[/cyan]")
                    resume_path = app_response.get("resume_path") or (
                        resume_response.get("file_path") if resume_response else None
                    )
                    cover_letter_path = app_response.get(
                        "cover_letter_path"
                    ) or cover_letter_response.get("file_path")

                    if cover_letter_path:
                        self.console.print(f"    • Cover Letter: {cover_letter_path}")
                    if resume_path:
                        self.console.print(f"    • Resume: {resume_path}")

                    job_url = app_response.get("job_url") or job.get("url", "")
                    if job_url:
                        self.console.print(f"  [cyan]Job URL:[/cyan] {job_url}")
                    self.console.print(
                        f"  [dim]→ Please apply manually using these documents[/dim]"
                    )
                else:
                    error_msg = (
                        app_response.get("error")
                        or app_response.get("message")
                        or app_response.get("reason")
                        or "Unknown error"
                    )
                    status = app_response.get("status", "unknown")
                    self.console.print(
                        f"[red]✗[/red] Application failed (status: {status}): {error_msg}"
                    )

                # Small delay between applications
                await asyncio.sleep(2)

            except Exception as e:
                self.console.print(f"[red]✗[/red] Error applying to job: {e}")
                continue

        return applied_count

    async def _review_jobs(self, user_id: str, jobs: List[Dict]) -> int:
        """Interactive review of medium-match jobs.

        Args:
            user_id: User identifier
            jobs: List of jobs to review

        Returns:
            Number of applications made
        """
        if not jobs:
            return 0

        self.console.print(
            f"\n[cyan]🔔[/cyan] Found {len(jobs)} job(s) that need your review!"
        )

        response = (
            input("Would you like to review them now? (y/n/later): ").lower().strip()
        )

        if response == "n":
            self.console.print("[yellow]⏭[/yellow] Skipping review")
            return 0
        elif response == "later":
            self.console.print("[yellow]⏰[/yellow] Jobs saved for later review")
            return 0

        # Start review interface
        self.console.print("\n" + "=" * 70)
        self.console.print(Panel("📋 JOB REVIEW INTERFACE", style="bold cyan"))
        self.console.print("=" * 70 + "\n")

        jobs_to_apply = []

        for idx, job in enumerate(jobs, 1):
            max_per_day = self.config.autonomous_config.get(
                "max_applications_per_day", 10
            )
            if self.stats["today_applications"] >= max_per_day:
                self.console.print("[yellow]⚠[/yellow] Daily limit reached")
                break

            # Display job details
            job_panel = f"""
[bold cyan]{job.get('job_title', job.get('title', 'Position Not Listed'))}[/bold cyan]
{job.get('company_name', job.get('company', 'Unknown Company'))} • {job.get('location', 'Location Not Listed')} • {job.get('salary', 'Not listed')}
[bold]Match Score: {job.get('match_score', 0)}%[/bold] {'⭐' * (int(float(job.get('match_score', 0))) // 25)}

[bold green]✓ Strengths:[/bold green]
{self._format_match_insights(job.get('match_insights', {}), 'strengths')}

[bold yellow]⚠ Gaps:[/bold yellow]
{self._format_match_insights(job.get('match_insights', {}), 'gaps')}

[bold]🎯 Recommended Action:[/bold] {'APPLY' if job.get('match_score', 0) >= 80 else 'CONSIDER'}
            """

            self.console.print(f"\n[bold]Job {idx} of {len(jobs)}:[/bold]")
            self.console.print(Panel(job_panel, border_style="blue"))

            action = (
                input("\n[A]pply  [S]kip  [V]iew Full  [Q]uit Review: ").lower().strip()
            )

            if action == "a":
                jobs_to_apply.append(job)
                self.console.print("[green]✓[/green] Added to apply queue")
            elif action == "v":
                # Show more details
                self.console.print(f"\n[bold]Full Job Description:[/bold]")
                self.console.print(
                    job.get("description", "No description available")[:500]
                )
                action = input("\n[A]pply  [S]kip: ").lower().strip()
                if action == "a":
                    jobs_to_apply.append(job)
            elif action == "q":
                break

        # Apply to approved jobs
        if jobs_to_apply:
            self.console.print(
                f"\n[cyan]📝[/cyan] Applying to {len(jobs_to_apply)} approved job(s)..."
            )
            applied = await self._apply_to_jobs(user_id, jobs_to_apply, auto=False)

            self.console.print(f"\n[bold green]✓[/bold green] Review session complete:")
            self.console.print(f"  • Applied: {applied} jobs")
            self.console.print(f"  • Skipped: {len(jobs) - applied} jobs")

            return applied

        return 0

    def _format_match_insights(self, insights: Dict, category: str) -> str:
        """Format match insights for display."""
        items = insights.get(category, [])
        if not items:
            return "  • None specified"

        formatted = []
        for item in items[:3]:
            if isinstance(item, str):
                formatted.append(f"  • {item}")
            elif isinstance(item, dict):
                formatted.append(
                    f"  • {item.get('skill', item.get('point', 'Unknown'))}"
                )

        return "\n".join(formatted) if formatted else "  • None specified"

    def _print_daily_summary(self):
        """Print end-of-day summary."""
        summary = f"""
[bold]Today's Summary:[/bold]
  ✅ Applications submitted: {self.stats['today_applications']}
  📝 Remaining daily quota: {self.config.autonomous_config.get('max_applications_per_day', 10) - self.stats['today_applications']}
  ⏰ Next check: {(datetime.now() + timedelta(hours=self.config.autonomous_config.get('search_interval_hours', 6))).strftime('%I:%M %p')}
        """
        self.console.print(
            Panel(summary, title="[bold]Daily Summary[/bold]", border_style="green")
        )

    async def _run_cycle(self, user_id: str):
        """Run one complete search and apply cycle."""
        self.stats["cycle_count"] += 1
        self.stats["last_cycle_time"] = datetime.now()

        # Track cycle timing and stats
        cycle_start = time.time()
        errors_count = 0
        jobs_auto_applied = 0
        jobs_needs_review = 0
        jobs_skipped = 0

        try:
            # Search and score jobs
            categorized = await self._search_and_score_jobs(user_id)

            # Auto-apply to high matches
            if categorized["high"]:
                jobs_auto_applied = await self._apply_to_jobs(
                    user_id, categorized["high"], auto=True
                )

            # Log decisions for jobs needing review
            for job in categorized["medium"]:
                jobs_needs_review += 1
                self.audit_logger.log_decision(
                    user_id=user_id,
                    job_id=job.get("job_id", ""),
                    decision_type="review",
                    match_score=job.get("match_score", 0),
                    reason=f"Score {job.get('match_score', 0)}% in review range (75-89%)",
                    metadata={
                        "job_title": job.get("job_title"),
                        "company": job.get("company"),
                    },
                )

            # Log decisions for skipped jobs
            for job in categorized["low"]:
                jobs_skipped += 1
                self.audit_logger.log_decision(
                    user_id=user_id,
                    job_id=job.get("job_id", ""),
                    decision_type="skip",
                    match_score=job.get("match_score", 0),
                    reason=f"Score {job.get('match_score', 0)}% below threshold (<75%)",
                    metadata={
                        "job_title": job.get("job_title"),
                        "company": job.get("company"),
                    },
                )

            # Review medium matches if configured
            if categorized["medium"] and self.config.autonomous_config.get(
                "review_medium_matches", True
            ):
                await self._review_jobs(user_id, categorized["medium"])

            # Print summary
            self._print_daily_summary()

            # Save state
            self._save_state()

            # Log cycle summary
            cycle_duration = time.time() - cycle_start
            self.audit_logger.log_cycle_summary(
                cycle_number=self.stats["cycle_count"],
                duration_seconds=cycle_duration,
                jobs_found=len(categorized["high"])
                + len(categorized["medium"])
                + len(categorized["low"]),
                jobs_scored=len(categorized["high"])
                + len(categorized["medium"])
                + len(categorized["low"]),
                jobs_auto_applied=jobs_auto_applied,
                jobs_needs_review=jobs_needs_review,
                jobs_skipped=jobs_skipped,
                errors_count=errors_count,
            )

        except Exception as e:
            errors_count += 1
            self.console.print(f"[red]✗[/red] Error in cycle: {e}")

            # Log error
            import traceback

            self.audit_logger.log_error(
                error_type=type(e).__name__,
                error_message=str(e),
                operation="cycle_execution",
                user_id=user_id,
                stacktrace=traceback.format_exc(),
            )

            traceback.print_exc()

    async def run(self):
        """Main autonomous run loop."""
        self.running = True
        self._print_banner()
        self._print_config()

        # Get user_id from config
        user_id = self.config.config.get("app", {}).get("user_id", "default_user")
        search_interval = self.config.autonomous_config.get("search_interval_hours", 6)

        self.console.print(f"\n[green]🚀[/green] Starting autonomous operation...")
        self.console.print(f"[dim]Press Ctrl+C to stop[/dim]\n")

        while self.running and not self.stop_requested:
            try:
                if self.paused:
                    self.console.print("[yellow]⏸[/yellow] Agent is paused. Waiting...")
                    await asyncio.sleep(60)
                    continue

                # Check if we need to reset daily counter
                now = datetime.now()
                if self.stats.get("last_reset_date") != now.date():
                    self.stats["today_applications"] = 0
                    self.stats["last_reset_date"] = now.date()

                # Run a cycle
                await self._run_cycle(user_id)

                # Check if daily limit reached
                max_per_day = self.config.autonomous_config.get(
                    "max_applications_per_day", 10
                )
                if self.stats["today_applications"] >= max_per_day:
                    self.console.print(
                        f"\n[yellow]⚠[/yellow] Daily limit reached ({max_per_day} applications)"
                    )
                    self.console.print(
                        "[yellow]😴[/yellow] Agent sleeping until tomorrow..."
                    )

                    # Sleep until midnight
                    tomorrow = now.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ) + timedelta(days=1)
                    sleep_seconds = (tomorrow - now).total_seconds()
                    await asyncio.sleep(sleep_seconds)
                    continue

                # Sleep until next cycle
                self.console.print(
                    f"\n[cyan]😴[/cyan] Agent going to sleep. Next check in {search_interval} hours..."
                )
                self.console.print(
                    "[dim]Press Ctrl+C to stop, or let me work in background.[/dim]"
                )

                # Sleep in shorter intervals to check for stop signal
                sleep_duration = search_interval * 3600
                sleep_interval = 60  # Check every minute
                for _ in range(int(sleep_duration / sleep_interval)):
                    if self.stop_requested:
                        break
                    await asyncio.sleep(sleep_interval)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]⚠[/yellow] Shutdown requested...")
                break
            except Exception as e:
                self.console.print(f"[red]✗[/red] Error in main loop: {e}")
                import traceback

                traceback.print_exc()
                await asyncio.sleep(300)  # Sleep 5 minutes on error

        self._shutdown()

    def _shutdown(self):
        """Clean shutdown."""
        self.console.print("\n[cyan]🛑[/cyan] Stopping autonomous agent...")

        # Print final stats
        runtime = datetime.now() - self.stats["start_time"]
        days = runtime.days
        hours = runtime.seconds // 3600

        final_stats = f"""
[bold]Final Statistics:[/bold]
  Total Runtime: {days} days, {hours} hours
  Total Applications: {self.stats['total_applications']}
  Jobs Analyzed: {self.stats['jobs_found']}
  High Matches: {self.stats['high_matches']}
  Medium Matches: {self.stats['medium_matches']}
        """

        self.console.print(
            Panel(
                final_stats, title="[bold]Session Complete[/bold]", border_style="green"
            )
        )
        self._save_state()
        self.console.print("\n[green]✓[/green] Agent stopped. All data saved.")
        self.console.print("[dim]Resume anytime with: python run_autonomous.py[/dim]")


def show_status(runner: AutonomousRunner):
    """Show current agent status."""
    console = Console()

    # Calculate runtime
    runtime = datetime.now() - runner.stats["start_time"]
    days = runtime.days
    hours = runtime.seconds // 3600

    # Agent state
    if runner.running:
        state = "[green]ACTIVE[/green]"
        if runner.paused:
            state = "[yellow]PAUSED[/yellow]"
    else:
        state = "[red]STOPPED[/red]"

    # Next check time
    if runner.stats.get("last_cycle_time"):
        search_interval = runner.config.autonomous_config.get(
            "search_interval_hours", 6
        )
        next_check = runner.stats["last_cycle_time"] + timedelta(hours=search_interval)
        next_check_str = next_check.strftime("%I:%M %p")
    else:
        next_check_str = "Not started"

    status_report = f"""
[bold]🤖 Agent State:[/bold] {state}
[bold]⏰ Last Activity:[/bold] {runner.stats.get('last_cycle_time', 'Never').strftime('%I:%M %p') if runner.stats.get('last_cycle_time') else 'Never'}
[bold]🔄 Next Check:[/bold] {next_check_str}

[bold]📊 Statistics (Last 7 Days):[/bold]
  Total Applications: {runner.stats['total_applications']}
  Today: {runner.stats['today_applications']}
  Jobs Found: {runner.stats['jobs_found']}
  High Matches (≥90%): {runner.stats['high_matches']}
  Medium Matches (75-89%): {runner.stats['medium_matches']}

[bold]⏱ Runtime:[/bold] {days} days, {hours} hours
    """

    console.print(
        Panel(
            status_report,
            title="[bold cyan]Agent Status Report[/bold cyan]",
            border_style="cyan",
        )
    )


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Autonomous Job Application Agent")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--status", action="store_true", help="Show agent status")
    parser.add_argument("--pause", action="store_true", help="Pause agent")
    parser.add_argument("--resume", action="store_true", help="Resume agent")
    parser.add_argument("--stop", action="store_true", help="Stop agent")

    args = parser.parse_args()

    try:
        runner = AutonomousRunner(args.config)

        if args.status:
            show_status(runner)
            return

        if args.pause:
            runner.paused = True
            runner._save_state()
            console.print("[yellow]⏸[/yellow] Agent paused")
            return

        if args.resume:
            runner.paused = False
            runner._save_state()
            console.print("[green]▶[/green] Agent resumed")
            return

        if args.stop:
            runner.stop_requested = True
            runner._save_state()
            console.print("[red]🛑[/red] Stop signal sent")
            return

        # Run autonomous mode
        await runner.run()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Fatal error:[/red] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
