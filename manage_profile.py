"""
Profile Management CLI - View, edit, and manage user profiles.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
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
    print("7. Delete profile")
    print("8. Exit")
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
    print("1. Employment types")
    print("2. Remote preference")
    print("3. Locations")
    print("4. Minimum salary")
    print("5. Excluded companies")

    choice = input("\nChoice: ").strip()
    updates = {}

    if choice == "1":
        emp_types = input("Employment types (comma-separated): ").strip()
        updates["employment_types"] = [
            et.strip().upper() for et in emp_types.split(",")
        ]
    elif choice == "2":
        remote = input("Remote only? (y/n): ").strip().lower() == "y"
        updates["remote_only"] = remote
    elif choice == "3":
        locs = input("Locations (comma-separated): ").strip()
        updates["preferred_locations"] = [
            loc.strip() for loc in locs.split(",") if loc.strip()
        ]
    elif choice == "4":
        salary = input("Minimum salary: ").strip()
        updates["salary_min"] = (
            float(salary)
            if salary.replace(".", "").replace(",", "").isdigit()
            else None
        )
    elif choice == "5":
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


def main():
    """Main CLI loop."""
    try:
        # Initialize
        config = Config()
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
                delete_profile(user_profile)
            elif choice == "8":
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
