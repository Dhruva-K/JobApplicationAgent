"""
Quick setup script for autonomous runner - creates a default user profile
"""

import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from graph.memory import GraphMemory
from core.config import Config
from core.user_profile import UserProfile
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()


def quick_setup():
    """Quick setup for autonomous mode."""

    console.print(
        Panel.fit(
            "[bold cyan]Quick Setup for Autonomous Job Application Agent[/bold cyan]",
            border_style="cyan",
        )
    )

    console.print(
        "\nThis will create a default profile for autonomous job applications."
    )
    console.print("[dim]You can update it later using manage_profile.py[/dim]\n")

    try:
        # Initialize database
        config_path = Path(__file__).parent.parent / "config.yaml"
        config = Config(str(config_path))
        neo = config.get_neo4j_config()
        graph = GraphMemory(
            uri=neo["uri"],
            user=neo["user"],
            password=neo["password"],
            database=neo["database"],
        )

        user_profile = UserProfile(graph)

        # Check if profile exists
        existing = user_profile.get_profile("default_user")
        if existing:
            console.print("[yellow]✓[/yellow] Profile already exists!")
            console.print(f"\nCurrent profile:")
            console.print(
                f"  • Name: {existing.get('name', existing.get('full_name', 'Not set'))}"
            )
            console.print(f"  • Email: {existing.get('email', 'Not set')}")
            console.print(
                f"  • Experience: {existing.get('experience_years', 'Not set')} years"
            )

            # Debug: print all keys
            console.print(f"\n[dim]Profile has {len(existing)} fields[/dim]")

            if not Confirm.ask("\nWould you like to update it?"):
                console.print("\n[green]✓[/green] Using existing profile")
                console.print("\n[bold]Next Steps:[/bold]")
                console.print(
                    "  1. Run pre-flight check: [cyan]python test_autonomous_runner.py[/cyan]"
                )
                console.print(
                    "  2. Start the agent: [cyan]python run_autonomous.py[/cyan]"
                )
                return True

        # Gather information
        console.print("\n[bold]Basic Information:[/bold]")
        full_name = Prompt.ask("Full Name", default="Default User")
        email = Prompt.ask("Email", default="user@example.com")
        phone = Prompt.ask("Phone (optional)", default="")
        location = Prompt.ask("Location", default="Remote")

        console.print("\n[bold]Target Roles:[/bold]")
        console.print(
            "[dim]Enter job titles you're interested in (comma-separated)[/dim]"
        )
        job_titles_str = Prompt.ask(
            "Job Titles", default="Software Engineer, Python Developer"
        )
        job_titles = [title.strip() for title in job_titles_str.split(",")]

        console.print("\n[bold]Preferred Locations:[/bold]")
        console.print("[dim]Enter locations or 'remote' (comma-separated)[/dim]")
        locations_str = Prompt.ask("Locations", default="remote")
        locations = [loc.strip() for loc in locations_str.split(",")]

        console.print("\n[bold]Employment Details:[/bold]")
        employment_types = {
            "1": "FULLTIME",
            "2": "PARTTIME",
            "3": "CONTRACT",
            "4": "INTERN",
        }
        console.print("1. Full-time")
        console.print("2. Part-time")
        console.print("3. Contract")
        console.print("4. Intern")
        emp_choice = Prompt.ask(
            "Employment type", choices=["1", "2", "3", "4"], default="1"
        )
        employment_type = employment_types[emp_choice]

        salary_min = Prompt.ask("Minimum salary (optional)", default="0")
        salary_max = Prompt.ask("Maximum salary (optional)", default="0")

        console.print("\n[bold]Experience:[/bold]")
        years_experience = Prompt.ask("Years of experience", default="3")

        console.print("\n[bold]Top Skills:[/bold]")
        console.print("[dim]Enter your key skills (comma-separated)[/dim]")
        skills_str = Prompt.ask("Skills", default="Python, JavaScript, SQL, AWS")
        skills_list = [skill.strip() for skill in skills_str.split(",")]

        # Create or update profile
        console.print("\n[cyan]Creating profile...[/cyan]")

        # Check if profile exists
        existing_profile = user_profile.get_profile("default_user")

        if existing_profile:
            # Update existing profile
            console.print("[yellow]Profile exists, updating...[/yellow]")

            updates = {
                "name": full_name,
                "email": email,
                "phone": phone,
                "location": location,
                "experience_years": (
                    int(years_experience) if years_experience.isdigit() else 3
                ),
                "skills": skills_list[:10],
            }

            # Add preferences
            preferences = {
                "job_titles": job_titles,
                "locations": locations,
                "employment_type": employment_type,
                "remote_ok": "remote" in locations_str.lower(),
                "date_posted": "week",
                "salary_min": int(salary_min) if salary_min.isdigit() else 0,
                "salary_max": int(salary_max) if salary_max.isdigit() else 0,
            }
            updates["preferences"] = preferences

            user_profile.update_profile("default_user", updates)

        else:
            # Create new profile
            console.print("[cyan]Creating new profile...[/cyan]")

            # Create preferences as nested dict
            preferences_dict = {
                "preferences": {
                    "job_titles": job_titles,
                    "locations": locations,
                    "employment_type": employment_type,
                    "remote_ok": "remote" in locations_str.lower(),
                    "date_posted": "week",
                    "salary_min": int(salary_min) if salary_min.isdigit() else 0,
                    "salary_max": int(salary_max) if salary_max.isdigit() else 0,
                },
                "phone": phone,
                "location": location,
                "full_name": full_name,
            }

            created_user_id = user_profile.create_profile(
                user_id="default_user",
                name=full_name,
                email=email,
                skills=skills_list[:10],
                experience_years=(
                    int(years_experience) if years_experience.isdigit() else 3
                ),
                education_level="Bachelor's",
                preferences=preferences_dict,
            )
            console.print(f"[green]✓[/green] Created user: {created_user_id}")

        console.print("\n[green]✓[/green] Profile created successfully!")

        # Summary
        summary = f"""
[bold]Profile Summary:[/bold]
  • Name: {full_name}
  • Target Roles: {', '.join(job_titles[:3])}
  • Location: {', '.join(locations[:3])}
  • Employment: {employment_type}
  • Skills: {', '.join(skills_list[:5])}
        """

        console.print(
            Panel(
                summary,
                title="[bold green]✓ Setup Complete[/bold green]",
                border_style="green",
            )
        )

        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Review config.yaml for autonomous settings")
        console.print("  2. Start the agent: [cyan]python run_autonomous.py[/cyan]")
        console.print(
            "  3. Check status: [cyan]python run_autonomous.py --status[/cyan]"
        )

        return True

    except Exception as e:
        console.print(f"\n[red]✗[/red] Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = quick_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Setup cancelled[/yellow]")
        sys.exit(1)
