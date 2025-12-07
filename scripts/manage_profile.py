"""
Profile Management CLI - View, edit, and manage user profiles.
"""

import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from graph.memory import GraphMemory
from core.config import Config
from core.user_profile import UserProfile

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)
logging.getLogger("neo4j").setLevel(logging.WARNING)


def display_menu():
    """Display main menu."""
    print("\n" + "=" * 60)
    print("PROFILE MANAGEMENT")
    print("=" * 60)
    print("1. Create new profile")
    print("2. View profile")
    print("3. List all profiles")
    print("4. Add skill")
    print("5. Remove skill")
    print("6. Update preferences")
    print("7. Upload/Update resume")
    print("8. Delete profile")
    print("9. Exit")
    print("=" * 60)


def view_profile(user_profile: UserProfile):
    """View a user profile."""
    user_id = input("\nEnter user ID: ").strip()

    profile = user_profile.get_profile(user_id)
    if not profile:
        print(f"❌ Profile '{user_id}' not found.")
        return

    summary = user_profile.get_profile_summary(user_id)
    preferences = user_profile.get_search_preferences(user_id)

    print("\n" + "=" * 60)
    print(f"PROFILE: {user_id}")
    print("=" * 60)
    print(f"Name: {summary['name']}")
    print(f"Email: {summary['email']}")
    print(f"Experience: {summary['experience_years']} years")
    print(f"Education: {summary['education_level']}")
    print(f"\nSkills ({summary['skill_count']}):")
    for skill in summary["skills"]:
        print(f"  • {skill}")

    print(f"\nJob Search Preferences:")
    preferred_roles = preferences.get("preferred_roles", [])
    print(
        f"  Preferred Roles: {', '.join(preferred_roles) if preferred_roles else 'Not set'}"
    )
    print(f"  Employment Types: {', '.join(preferences.get('employment_types', []))}")
    print(f"  Remote Only: {preferences.get('remote_only', False)}")
    print(f"  Locations: {', '.join(preferences.get('locations', [])) or 'Any'}")
    print(
        f"  Min Salary: ${preferences.get('salary_min')}"
        if preferences.get("salary_min")
        else "  Min Salary: Not specified"
    )
    print(
        f"  Excluded Companies: {', '.join(preferences.get('exclude_companies', [])) or 'None'}"
    )

    # Show resume status
    resume_text = user_profile.get_resume(user_id)
    if resume_text:
        print(f"\n📄 Resume: Uploaded ({len(resume_text)} characters)")
        print(f"  Preview: {resume_text[:150]}...")
    else:
        print(f"\n📄 Resume: Not uploaded")


def list_profiles(user_profile: UserProfile):
    """List all profiles."""
    profiles = user_profile.list_all_profiles()

    if not profiles:
        print("\n❌ No profiles found.")
        return

    print("\n" + "=" * 60)
    print(f"ALL PROFILES ({len(profiles)})")
    print("=" * 60)

    for p in profiles:
        print(f"\n• {p.get('user_id')}")
        print(f"  Name: {p.get('name')}")
        print(f"  Email: {p.get('email')}")
        print(f"  Experience: {p.get('experience_years', 0)} years")


def add_skill(user_profile: UserProfile):
    """Add a skill to profile."""
    user_id = input("\nEnter user ID: ").strip()
    skill_name = input("Enter skill to add: ").strip()

    if user_profile.add_skill(user_id, skill_name):
        print(f"✅ Added skill '{skill_name}' to profile '{user_id}'")
    else:
        print(f"❌ Failed to add skill")


def remove_skill(user_profile: UserProfile):
    """Remove a skill from profile."""
    user_id = input("\nEnter user ID: ").strip()

    # Show current skills
    skills = user_profile.get_skills(user_id)
    if not skills:
        print(f"❌ No skills found for '{user_id}'")
        return

    print("\nCurrent skills:")
    for i, skill in enumerate(skills, 1):
        print(f"  {i}. {skill.get('name')}")

    skill_name = input("\nEnter skill to remove: ").strip()

    if user_profile.remove_skill(user_id, skill_name):
        print(f"✅ Removed skill '{skill_name}' from profile '{user_id}'")
    else:
        print(f"❌ Failed to remove skill")


def update_preferences(user_profile: UserProfile):
    """Update job search preferences."""
    user_id = input("\nEnter user ID: ").strip()

    profile = user_profile.get_profile(user_id)
    if not profile:
        print(f"❌ Profile '{user_id}' not found.")
        return

    print("\nWhat would you like to update?")
    print("1. Preferred job titles/roles")
    print("2. Employment types")
    print("3. Remote preference")
    print("4. Locations")
    print("5. Minimum salary")
    print("6. Excluded companies")

    choice = input("\nChoice: ").strip()
    updates = {}

    if choice == "1":
        print("Enter job titles (comma-separated):")
        print("Example: Software Engineer, Machine Learning Engineer, Data Scientist")
        roles = input("Job titles: ").strip()
        updates["preferred_roles"] = [r.strip() for r in roles.split(",") if r.strip()]
    elif choice == "2":
        emp_types = input("Employment types (comma-separated): ").strip()
        updates["employment_types"] = [
            et.strip().upper() for et in emp_types.split(",")
        ]
    elif choice == "3":
        remote = input("Remote only? (y/n): ").strip().lower() == "y"
        updates["remote_only"] = remote
    elif choice == "4":
        locs = input("Locations (comma-separated): ").strip()
        updates["preferred_locations"] = [
            loc.strip() for loc in locs.split(",") if loc.strip()
        ]
    elif choice == "5":
        salary = input("Minimum salary: ").strip()
        updates["salary_min"] = (
            float(salary)
            if salary.replace(".", "").replace(",", "").isdigit()
            else None
        )
    elif choice == "6":
        companies = input("Excluded companies (comma-separated): ").strip()
        updates["exclude_companies"] = [
            c.strip() for c in companies.split(",") if c.strip()
        ]
    else:
        print("Invalid choice")
        return

    if user_profile.update_preferences(user_id, updates):
        print(f"✅ Updated preferences for '{user_id}'")
    else:
        print(f"❌ Failed to update preferences")


def delete_profile(user_profile: UserProfile):
    """Delete a user profile."""
    user_id = input("\nEnter user ID to delete: ").strip()

    confirm = (
        input(f"⚠️  Are you sure you want to delete '{user_id}'? (yes/no): ")
        .strip()
        .lower()
    )

    if confirm == "yes":
        if user_profile.delete_profile(user_id):
            print(f"✅ Deleted profile '{user_id}'")
        else:
            print(f"❌ Failed to delete profile")
    else:
        print("Deletion cancelled")


def upload_resume(user_profile: UserProfile):
    """Upload or update resume for a profile."""
    user_id = input("\nEnter user ID: ").strip()

    profile = user_profile.get_profile(user_id)
    if not profile:
        print(f"❌ Profile '{user_id}' not found.")
        return

    # Check if resume exists
    existing_resume = user_profile.get_resume(user_id)
    if existing_resume:
        print(f"\n⚠️  Resume already exists ({len(existing_resume)} characters)")
        print(f"Preview: {existing_resume[:150]}...")
        replace = input("\nReplace existing resume? (y/n): ").strip().lower()
        if replace != "y":
            print("Upload cancelled")
            return

    resume_path = input("\nEnter path to resume file (PDF or DOCX): ").strip()

    if not resume_path:
        print("❌ No file path provided")
        return

    print("\n⏳ Parsing resume...")
    if user_profile.upload_resume(user_id, resume_path):
        resume_text = user_profile.get_resume(user_id)
        print(f"✅ Resume uploaded successfully!")
        print(f"   Characters: {len(resume_text)}")
        print(f"   Preview: {resume_text[:200]}...")
    else:
        print(
            "❌ Failed to upload resume. Check file path and format (PDF or DOCX only)"
        )


def main():
    """Main CLI loop."""
    try:
        # Initialize
        config_path = Path(__file__).parent.parent / "config.yaml"
        config = Config(str(config_path))
        neo = config.get_neo4j_config()
        graph = GraphMemory(
            uri=neo["uri"],
            user=neo["user"],
            password=neo["password"],
            database=neo["database"],
        )

        user_profile = UserProfile(graph_memory=graph)

        while True:
            display_menu()
            choice = input("\nChoice: ").strip()

            if choice == "1":
                UserProfile.interactive_setup(graph)
            elif choice == "2":
                view_profile(user_profile)
            elif choice == "3":
                list_profiles(user_profile)
            elif choice == "4":
                add_skill(user_profile)
            elif choice == "5":
                remove_skill(user_profile)
            elif choice == "6":
                update_preferences(user_profile)
            elif choice == "7":
                upload_resume(user_profile)
            elif choice == "8":
                delete_profile(user_profile)
            elif choice == "9":
                print("\n👋 Goodbye!")
                break
            else:
                print("\n❌ Invalid choice. Please try again.")

            input("\nPress Enter to continue...")

    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if "graph" in locals():
            graph.close()


if __name__ == "__main__":
    main()
