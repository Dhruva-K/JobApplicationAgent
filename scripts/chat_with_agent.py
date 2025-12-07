"""
Interactive Chat Interface with Job Application Agent
Ask questions about your applications, jobs, and statistics.
"""

import sys
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich import box

from core.config import Config
from core.user_profile import UserProfile
from graph.memory import GraphMemory, ApplicationStatus
from llm.llm_client import LLMClient
from agents.tracker_agent import TrackerAgent

console = Console()


class AgentChat:
    """Interactive chat interface with the job application agent."""

    def __init__(self, config_path: str = None):
        """Initialize the chat interface.

        Args:
            config_path: Path to configuration file (defaults to ../config.yaml)
        """
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "config.yaml")
        self.config = Config(config_path)
        self.console = Console()

        # Initialize graph memory
        self.graph_memory = GraphMemory(
            uri=self.config.neo4j_uri,
            user=self.config.neo4j_user,
            password=self.config.neo4j_password,
            database=self.config.neo4j_database,
        )

        # Load user profile
        self.user_profile = UserProfile(self.graph_memory)

        # Initialize TrackerAgent for application management
        self.tracker = TrackerAgent(self.graph_memory)

        # Get user_id from config
        self.user_id = self.config.config.get("app", {}).get("user_id", "default_user")

        # Initialize LLM client for intelligent responses
        llm_config = self.config.get_llm_config()
        self.llm_client = LLMClient(llm_config)

        # Load user info
        user_info = self.user_profile.get_profile(self.user_id)
        self.user_name = (
            user_info.get("name", user_info.get("full_name", "User"))
            if user_info
            else "User"
        )

    def _print_banner(self):
        """Print welcome banner."""
        banner = f"""
╔════════════════════════════════════════════════════════════════╗
║        💬 CHAT WITH YOUR JOB APPLICATION AGENT                ║
╚════════════════════════════════════════════════════════════════╝

Welcome back, {self.user_name}! 👋

I can answer questions about:
• Your job applications and their status
• Jobs you've applied to or are tracking
• Match scores and recommendations
• Application statistics and trends
• Your profile and preferences

Type 'help' for example questions, or 'exit' to quit.
        """
        self.console.print(banner, style="cyan")

    def _get_context_data(self) -> Dict[str, Any]:
        """Gather context data from graph memory.

        Returns:
            Dictionary with current state data
        """
        try:
            # Get application statistics
            apps = self.graph_memory.get_user_applications(self.user_id)

            # Count by status
            status_counts = {}
            for app in apps:
                status = app.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1

            # Get recent applications (last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            recent_apps = [
                app
                for app in apps
                if app.get("applied_at")
                and datetime.fromisoformat(app["applied_at"].replace("Z", "+00:00"))
                > week_ago
            ]

            # Get high-match jobs not yet applied to
            all_matches = self.graph_memory.get_user_matches(
                self.user_id, min_score=80.0, limit=50
            )
            # Extract job_ids from the nested job object in applications
            applied_job_ids = {
                app.get("job", {}).get("job_id") for app in apps if app.get("job")
            }
            pending_high_matches = [
                match
                for match in all_matches
                if match.get("job_id") not in applied_job_ids
            ]

            # Get user preferences
            preferences = self.user_profile.get_search_preferences(self.user_id)

            return {
                "total_applications": len(apps),
                "status_counts": status_counts,
                "recent_applications": len(recent_apps),
                "pending_high_matches": len(pending_high_matches),
                "preferred_roles": preferences.get("preferred_roles", []),
                "recent_apps_details": recent_apps[:5],  # Last 5 for context
                "top_pending_matches": pending_high_matches[:5],  # Top 5 matches
            }
        except Exception as e:
            self.console.print(f"[yellow]Warning:[/yellow] Could not load context: {e}")
            return {}

    def _handle_quick_commands(self, query: str) -> Optional[bool]:
        """Handle quick command shortcuts.

        Args:
            query: User query

        Returns:
            True if handled, False if not a command, None to exit
        """
        query_lower = query.lower().strip()

        if query_lower in ["exit", "quit", "bye", "q"]:
            self.console.print(
                "\n[cyan]👋 Goodbye! Good luck with your job search![/cyan]"
            )
            return None

        if query_lower in ["help", "?"]:
            self._show_help()
            return True

        if query_lower in ["stats", "statistics"]:
            self._show_statistics()
            return True

        if query_lower in ["status", "applications"]:
            self._show_applications()
            return True

        if query_lower in ["matches", "jobs"]:
            self._show_matches()
            return True

        if query_lower in ["profile", "me"]:
            self._show_profile()
            return True

        # Handle status update commands
        if query_lower.startswith("update "):
            self._handle_update_command(query)
            return True

        return False

    def _show_help(self):
        """Show help with example questions."""
        help_text = """
[bold cyan]Quick Commands:[/bold cyan]
• [bold]stats[/bold] - Show application statistics
• [bold]status[/bold] - Show recent applications
• [bold]matches[/bold] - Show pending high-match jobs
• [bold]profile[/bold] - Show your profile
• [bold]update <app_id> <status>[/bold] - Update application status
• [bold]help[/bold] - Show this help
• [bold]exit[/bold] - Exit chat

[bold cyan]Status Values:[/bold cyan]
• pending, submitted, interview, rejected, accepted

[bold cyan]Example Commands:[/bold cyan]
• "update #1 interview" - Mark first application as interview stage
• "update #2 rejected" - Mark second application as rejected
• "update Grassroots interview" - Update by company name

[bold cyan]Example Questions:[/bold cyan]
• "How many applications have I submitted?"
• "What's my interview rate?"
• "Show me jobs I should apply to"
• "What companies have I applied to?"
• "Any interviews scheduled?"
• "What's my highest match score?"
• "Show applications from last week"
• "Which jobs are pending?"
• "What skills do top matches require?"
• "Should I apply to more jobs today?"
• "Update my TechCorp application to interview"
        """
        self.console.print(Panel(help_text, title="Help", border_style="cyan"))

    def _show_statistics(self):
        """Show application statistics."""
        apps = self.graph_memory.get_user_applications(self.user_id)

        # Count by status
        status_counts = {}
        for app in apps:
            status = app.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        # Create table
        table = Table(title="📊 Application Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        table.add_row("Total Applications", str(len(apps)))
        table.add_row("Pending", str(status_counts.get("pending", 0)))
        table.add_row("Submitted", str(status_counts.get("submitted", 0)))
        table.add_row("Interview", str(status_counts.get("interview", 0)))
        table.add_row("Rejected", str(status_counts.get("rejected", 0)))

        if status_counts.get("interview", 0) > 0:
            interview_rate = (status_counts.get("interview", 0) / len(apps)) * 100
            table.add_row("Interview Rate", f"{interview_rate:.1f}%")

        self.console.print(table)

    def _show_applications(self):
        """Show recent applications."""
        apps = self.graph_memory.get_user_applications(self.user_id)

        if not apps:
            self.console.print("[yellow]No applications found.[/yellow]")
            return

        table = Table(title="📝 Recent Applications", box=box.ROUNDED)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Date", style="dim", width=8)
        table.add_column("Job Title", style="cyan")
        table.add_column("Company", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Score", justify="right")

        # Store apps with index for easy reference
        for idx, app in enumerate(apps[:10], 1):

            # Date from application properties
            date = app.get("applied_date") or app.get("applied_at", "Unknown")
            if date and date != "Unknown":
                try:
                    date_obj = datetime.fromisoformat(date.replace("Z", "+00:00"))
                    date = date_obj.strftime("%m/%d")
                except:
                    pass

            # Job information is nested in 'job' dict
            job_data = app.get("job", {})
            job_title = job_data.get("title") or job_data.get("job_title", "Unknown")
            company = job_data.get("company") or job_data.get("company_name", "Unknown")

            status = app.get("status", "unknown")
            status_emoji = {
                "submitted": "✓",
                "pending": "⏳",
                "interview": "🎯",
                "rejected": "✗",
                "accepted": "🎉",
            }.get(status, "?")

            table.add_row(
                str(idx),
                date,
                job_title[:30],
                company[:20],
                f"{status_emoji} {status}",
                f"{app.get('match_score', 0):.0f}%",
            )

        self.console.print(table)
        self.console.print(
            "\n[dim]💡 Tip: Use 'update #N <status>' to update by number (e.g., 'update #1 interview')[/dim]"
        )
        self.console.print(
            "[dim]   Or 'update <company> <status>' to update by company name[/dim]"
        )

    def _show_matches(self):
        """Show pending high-match jobs."""
        all_matches = self.graph_memory.get_user_matches(
            self.user_id, min_score=80.0, limit=20
        )
        apps = self.graph_memory.get_user_applications(self.user_id)
        applied_job_ids = {app.get("job_id") for app in apps}

        pending_matches = [
            match for match in all_matches if match.get("job_id") not in applied_job_ids
        ]

        if not pending_matches:
            self.console.print(
                "[yellow]No pending high-match jobs. All caught up! 🎉[/yellow]"
            )
            return

        table = Table(title="🎯 High-Match Jobs (Not Applied)", box=box.ROUNDED)
        table.add_column("Job Title", style="cyan")
        table.add_column("Company", style="magenta")
        table.add_column("Location", style="dim")
        table.add_column("Score", style="green", justify="right")

        for match in pending_matches[:10]:
            # Job nodes have 'title' property, not 'job_title'
            job_title = match.get("title") or match.get("job_title", "Unknown")
            company = match.get("company_name") or match.get("company", "Unknown")
            table.add_row(
                job_title[:30],
                company[:20],
                match.get("location", "Unknown")[:20],
                f"{match.get('match_score', 0):.0f}%",
            )

        self.console.print(table)
        self.console.print(
            f"\n[dim]Showing {len(pending_matches[:10])} of {len(pending_matches)} matches[/dim]"
        )

    def _show_profile(self):
        """Show user profile."""
        user_info = self.user_profile.get_profile(self.user_id)
        preferences = self.user_profile.get_search_preferences(self.user_id)

        if not user_info:
            self.console.print("[yellow]No profile found.[/yellow]")
            return

        profile_text = f"""
[bold]Name:[/bold] {user_info.get('name', 'Unknown')}
[bold]Email:[/bold] {user_info.get('email', 'Unknown')}

[bold cyan]Preferences:[/bold cyan]
• Target Roles: {', '.join(preferences.get('preferred_roles', [])[:5])}
• Locations: {', '.join(preferences.get('locations', [])[:5])}
• Employment: {', '.join(preferences.get('employment_types', []))}

[bold cyan]Experience:[/bold cyan]
• Years: {user_info.get('experience_years', 'Not set')}
• Education: {user_info.get('education_level', 'Not set')}
        """
        self.console.print(
            Panel(profile_text, title="👤 Your Profile", border_style="cyan")
        )

    def _handle_update_command(self, query: str):
        """Handle status update command.

        Args:
            query: Command like "update #1 interview", "update #2 rejected", or "update Grassroots interview"
        """
        parts = query.strip().split()
        if len(parts) < 3:
            self.console.print(
                "[yellow]Usage: update #N <status> or update <company> <status>[/yellow]"
            )
            self.console.print("[dim]Example: update #1 interview[/dim]")
            self.console.print("[dim]Example: update Grassroots interview[/dim]")
            self.console.print(
                "[dim]Valid statuses: pending, submitted, interview, rejected, accepted[/dim]"
            )
            return

        identifier = parts[1]
        new_status_str = parts[2].lower()

        # Validate status
        valid_statuses = {
            "pending": ApplicationStatus.PENDING,
            "submitted": ApplicationStatus.SUBMITTED,
            "interview": ApplicationStatus.INTERVIEW,
            "rejected": ApplicationStatus.REJECTED,
            "accepted": ApplicationStatus.ACCEPTED,
        }

        if new_status_str not in valid_statuses:
            self.console.print(f"[red]Invalid status:[/red] {new_status_str}")
            self.console.print(
                f"[dim]Valid statuses: {', '.join(valid_statuses.keys())}[/dim]"
            )
            return

        # Get all applications
        apps = self.graph_memory.get_user_applications(self.user_id)

        app_id = None
        app_display = identifier

        # Check if identifier is a number (e.g., #1, #2)
        if identifier.startswith("#"):
            try:
                index = int(identifier[1:]) - 1
                if 0 <= index < len(apps):
                    app_id = apps[index].get("application_id")
                    job_data = apps[index].get("job", {})
                    company = job_data.get("company") or job_data.get(
                        "company_name", "Unknown"
                    )
                    app_display = f"#{identifier[1:]} ({company})"
                else:
                    self.console.print(f"[red]Invalid number:[/red] {identifier}")
                    self.console.print(
                        f"[dim]Valid range: #1 to #{len(apps)}. Type 'status' to see applications.[/dim]"
                    )
                    return
            except ValueError:
                self.console.print(f"[red]Invalid format:[/red] {identifier}")
                return
        else:
            # Try to match by company name (case insensitive)
            identifier_lower = identifier.lower()
            for app in apps:
                job_data = app.get("job", {})
                company = (
                    job_data.get("company") or job_data.get("company_name", "")
                ).lower()
                if identifier_lower in company:
                    app_id = app.get("application_id")
                    app_display = f"{identifier} application"
                    break

            if not app_id:
                self.console.print(f"[red]No application found for:[/red] {identifier}")
                self.console.print("[dim]Type 'status' to see all applications.[/dim]")
                return

        # Update status
        new_status = valid_statuses[new_status_str]
        success = self.tracker.update_application_status(app_id, new_status)

        if success:
            self.console.print(
                f"[green]✓[/green] Updated {app_display} status to: {new_status_str}"
            )
        else:
            self.console.print(f"[red]✗[/red] Failed to update {app_display}")
            self.console.print(
                f"[dim]Database error occurred. Check logs for details.[/dim]"
            )

    async def _handle_natural_language_update(
        self, query: str, context: Dict[str, Any]
    ) -> Optional[str]:
        """Detect and handle natural language status updates.

        Args:
            query: User query that might contain update intent
            context: Current context data

        Returns:
            Response message if update was handled, None otherwise
        """
        # Keywords that indicate status update intent
        update_keywords = ["update", "mark", "change status", "set status"]
        status_keywords = {
            "interview": ["interview", "interviewing", "scheduled"],
            "rejected": ["rejected", "rejection", "declined", "didn't get"],
            "accepted": ["accepted", "offer", "got the job", "hired"],
            "submitted": ["submitted", "applied", "sent"],
            "pending": ["pending", "waiting", "no response"],
        }

        query_lower = query.lower()

        # Check if this is an update request
        has_update_intent = any(keyword in query_lower for keyword in update_keywords)

        if not has_update_intent:
            return None

        # Get ALL applications, not just recent ones from context
        apps = self.graph_memory.get_user_applications(self.user_id)

        # Check for explicit app_id
        import re

        app_id_match = re.search(r"app_\w+", query)
        if app_id_match:
            app_id = app_id_match.group(0)

            # Detect status
            detected_status = None
            for status, keywords in status_keywords.items():
                if any(kw in query_lower for kw in keywords):
                    detected_status = status
                    break

            if detected_status:
                status_enum = getattr(ApplicationStatus, detected_status.upper())
                success = self.tracker.update_application_status(app_id, status_enum)

                if success:
                    return f"✓ Updated {app_id} status to: {detected_status}"
                else:
                    return (
                        f"✗ Failed to update {app_id}. Please check the application ID."
                    )

        # Try to match by company name
        for app in apps:
            # Job information is nested in 'job' dict
            job_data = app.get("job", {})
            company = (
                job_data.get("company") or job_data.get("company_name", "")
            ).lower()

            if company and company in query_lower:
                # Detect status
                detected_status = None
                for status, keywords in status_keywords.items():
                    if any(kw in query_lower for kw in keywords):
                        detected_status = status
                        break

                if detected_status:
                    app_id = app.get("application_id")
                    if app_id:
                        status_enum = getattr(
                            ApplicationStatus, detected_status.upper()
                        )
                        success = self.tracker.update_application_status(
                            app_id, status_enum
                        )

                        if success:
                            job_title = job_data.get("title") or job_data.get(
                                "job_title", "Unknown"
                            )
                            return f"✓ Updated your {company} application ({job_title}) to: {detected_status}"
                        else:
                            return f"✗ Failed to update your {company} application."

        # If we got here, we detected update intent but couldn't process it
        return "I understand you want to update an application status, but I need more details. Try:\n• 'update #1 interview'\n• Or type 'status' to see your applications"

    async def _generate_intelligent_response(
        self, query: str, context: Dict[str, Any]
    ) -> str:
        """Generate intelligent response using LLM.

        Args:
            query: User query
            context: Context data from graph memory

        Returns:
            AI-generated response
        """
        # Build context prompt
        context_prompt = f"""You are a helpful job application assistant. Answer the user's question based on the following data:

USER PROFILE:
- Name: {self.user_name}
- Preferred roles: {', '.join(context.get('preferred_roles', []))}

APPLICATION STATISTICS:
- Total applications: {context.get('total_applications', 0)}
- Recent applications (7 days): {context.get('recent_applications', 0)}
- Pending high matches: {context.get('pending_high_matches', 0)}
- Status breakdown: {context.get('status_counts', {})}

RECENT APPLICATIONS:
{self._format_recent_apps(context.get('recent_apps_details', []))}

TOP PENDING MATCHES:
{self._format_pending_matches(context.get('top_pending_matches', []))}

USER QUESTION: {query}

Provide a helpful, concise response. If the data shows specific jobs or numbers, mention them. 
Be encouraging and actionable. Keep responses under 200 words unless detailed data is requested.
Format your response in plain text (not markdown) but you can use emojis."""

        try:
            # Use asyncio to run synchronous LLM call
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, self.llm_client.generate, context_prompt
            )

            if response:
                return response.strip()
            else:
                return "I'm having trouble generating a response right now. Try using quick commands like 'stats', 'status', or 'matches' instead!"
        except Exception as e:
            return f"I'm having trouble processing that right now. Error: {e}\nTry using quick commands like 'stats', 'status', or 'matches' instead!"

    def _format_recent_apps(self, apps: List[Dict]) -> str:
        """Format recent applications for context."""
        if not apps:
            return "None"

        lines = []
        for app in apps:
            # Job information is nested in 'job' dict
            job_data = app.get("job", {})
            job_title = job_data.get("title") or job_data.get("job_title", "Unknown")
            company = job_data.get("company") or job_data.get("company_name", "Unknown")

            lines.append(
                f"- {job_title} at {company} "
                f"(Status: {app.get('status', 'unknown')}, Score: {app.get('match_score', 0):.0f}%)"
            )
        return "\n".join(lines)

    def _format_pending_matches(self, matches: List[Dict]) -> str:
        """Format pending matches for context."""
        if not matches:
            return "None"

        lines = []
        for match in matches:
            # Job nodes have 'title' property, not 'job_title'
            job_title = match.get("title") or match.get("job_title", "Unknown")
            company = match.get("company_name") or match.get("company", "Unknown")
            lines.append(
                f"- {job_title} at {company} "
                f"(Score: {match.get('match_score', 0):.0f}%)"
            )
        return "\n".join(lines)

    async def chat(self):
        """Start interactive chat session."""
        self._print_banner()

        while True:
            try:
                # Get user input
                self.console.print("\n[bold cyan]You:[/bold cyan]", end=" ")
                query = input().strip()

                if not query:
                    continue

                # Handle quick commands
                result = self._handle_quick_commands(query)
                if result is None:  # Exit
                    break
                elif result is True:  # Command handled
                    continue

                # Show thinking indicator
                with self.console.status("[cyan]🤔 Thinking...[/cyan]"):
                    # Get context data
                    context = self._get_context_data()

                    # Check for natural language status updates
                    update_response = await self._handle_natural_language_update(
                        query, context
                    )
                    if update_response:
                        self.console.print(
                            f"\n[bold green]Agent:[/bold green] {update_response}"
                        )
                        continue

                    # Generate intelligent response
                    response = await self._generate_intelligent_response(query, context)

                # Display response
                self.console.print(f"\n[bold green]Agent:[/bold green] {response}")

            except KeyboardInterrupt:
                self.console.print("\n\n[cyan]👋 Goodbye![/cyan]")
                break
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"\n[red]Error:[/red] {e}")
                continue


async def main():
    """Main entry point."""
    try:
        chat = AgentChat()
        await chat.chat()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
