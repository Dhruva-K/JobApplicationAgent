"""
Script to set up user profile for personalized job search.

This is a simple CLI wrapper around UserProfile.interactive_setup().
"""

import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import yaml
from graph.memory import GraphMemory
from core.config import Config
from core.user_profile import UserProfile

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)
logging.getLogger("neo4j").setLevel(logging.WARNING)


def configure_autonomous_settings(config_path: str = None) -> bool:
    """Interactive wizard for autonomous configuration.

    Args:
        config_path: Path to config.yaml file (defaults to ../config.yaml)

    Returns:
        True if configuration successful
    """
    if config_path is None:
        config_path = str(Path(__file__).parent.parent / "config.yaml")

    try:
        print("\n" + "=" * 60)
        print("🤖 Autonomous Mode Configuration")
        print("=" * 60)

        # Load existing config
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Ensure autonomous section exists
        if "autonomous" not in config:
            config["autonomous"] = {
                "search": {},
                "auto_apply": {},
                "review": {},
                "rate_limiting": {},
                "notifications": {},
                "state": {},
            }

        # 1. Search interval
        print("\nHow often should I search for new jobs?")
        print("1. Every 3 hours (aggressive)")
        print("2. Every 6 hours (recommended)")
        print("3. Every 12 hours (relaxed)")
        print("4. Daily")
        interval_choice = input("> ").strip()

        intervals = {"1": 3, "2": 6, "3": 12, "4": 24}
        interval_hours = intervals.get(interval_choice, 6)

        if "search" not in config["autonomous"]:
            config["autonomous"]["search"] = {}
        config["autonomous"]["search"]["interval_hours"] = interval_hours

        # 2. Auto-apply threshold
        print("\nWhat's the minimum match score for auto-apply? (0-100)")
        print("Recommended: 90 (only excellent matches)")
        try:
            min_score = int(input("> ").strip() or "90")
            min_score = max(0, min(100, min_score))  # Clamp to 0-100
        except ValueError:
            print("⚠️  Invalid input, using default: 90")
            min_score = 90

        if "auto_apply" not in config["autonomous"]:
            config["autonomous"]["auto_apply"] = {}
        config["autonomous"]["auto_apply"]["min_score"] = min_score

        # 3. Daily application limit
        print("\nMaximum applications per day?")
        print("Recommended: 10 (safe limit)")
        try:
            max_per_day = int(input("> ").strip() or "10")
            max_per_day = max(1, max_per_day)  # At least 1
        except ValueError:
            print("⚠️  Invalid input, using default: 10")
            max_per_day = 10

        config["autonomous"]["auto_apply"]["max_per_day"] = max_per_day

        # 4. Platform selection
        print("\nWhich platforms should I use?")
        print("☑ 1. LinkedIn (Easy Apply)")
        print("☑ 2. Greenhouse")
        print("☑ 3. Lever")
        print("☑ 4. Workday")
        print("☐ 5. iCIMS")
        print("☑ 6. Indeed")
        print("☑ 7. Generic (other sites)")
        print("Enter platform numbers (comma-separated, e.g., 1,2,3,4,6,7):")
        print("Or press Enter for recommended: 1,2,3,4,6,7")

        platforms_input = input("> ").strip()
        if not platforms_input:
            platforms_input = "1,2,3,4,6,7"

        platform_map = {
            "1": "linkedin",
            "2": "greenhouse",
            "3": "lever",
            "4": "workday",
            "5": "icims",
            "6": "indeed",
            "7": "generic",
        }

        selected = []
        for p in platforms_input.split(","):
            p = p.strip()
            if p in platform_map:
                selected.append(platform_map[p])

        if not selected:
            selected = [
                "linkedin",
                "greenhouse",
                "lever",
                "workday",
                "indeed",
                "generic",
            ]
            print("⚠️  No valid platforms selected, using recommended set")

        config["autonomous"]["auto_apply"]["enabled_platforms"] = selected
        print(f"✓ Selected: {', '.join(selected)}")

        # 5. Review medium matches
        print("\nShould I ask for review before applying to medium matches (75-89)?")
        print("Recommended: yes (gives you control over borderline applications)")
        review_input = input("> ").strip().lower()
        review_enabled = review_input in ["yes", "y", ""] or review_input == ""

        if "review" not in config["autonomous"]:
            config["autonomous"]["review"] = {}
        config["autonomous"]["review"]["enabled"] = review_enabled

        # Set reasonable defaults for review settings
        config["autonomous"]["review"]["min_score"] = 75
        config["autonomous"]["review"]["max_score"] = (
            min_score - 1
        )  # Just below auto-apply threshold

        # Save config
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print("\n✅ Configuration saved to config.yaml")
        print("\n📋 Summary:")
        print(f"   • Search interval: Every {interval_hours} hours")
        print(f"   • Auto-apply threshold: ≥{min_score}% match")
        print(f"   • Daily limit: {max_per_day} applications")
        print(f"   • Platforms: {len(selected)} enabled")
        print(f"   • Review medium matches: {'Yes' if review_enabled else 'No'}")

        return True

    except Exception as e:
        print(f"\n❌ Error configuring autonomous settings: {e}")
        return False


def main():
    """Run interactive profile setup."""
    try:
        # Initialize database connection
        config_path = Path(__file__).parent.parent / "config.yaml"
        config = Config(str(config_path))
        neo = config.get_neo4j_config()
        graph = GraphMemory(
            uri=neo["uri"],
            user=neo["user"],
            password=neo["password"],
            database=neo["database"],
        )

        # Run interactive setup
        user_id = UserProfile.interactive_setup(graph)

        if user_id:
            # Save user_id to config
            config_path_str = str(Path(__file__).parent.parent / "config.yaml")
            try:
                with open(config_path_str, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)
                if "app" not in config_data:
                    config_data["app"] = {}
                config_data["app"]["user_id"] = user_id
                with open(config_path_str, "w", encoding="utf-8") as f:
                    yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            except Exception as e:
                print(
                    f"[yellow]Warning:[/yellow] Could not save user_id to config: {e}"
                )

            print(f"\n🎉 Profile created! Your user ID is: {user_id}")

            # Ask if they want to configure autonomous mode
            print("\n" + "=" * 60)
            print("Would you like to configure autonomous mode now?")
            print("(The agent will automatically search and apply to jobs)")
            print("=" * 60)
            configure_input = (
                input("Configure now? (y/n) [recommended: y]: ").strip().lower()
            )

            if configure_input in ["yes", "y", ""]:
                if configure_autonomous_settings():
                    print("\n✅ Setup complete!")
                    print("\n🚀 Next steps:")
                    print("  1. Run: python run_autonomous.py")
                    print("  2. The agent will work automatically!")
                    print("  3. Sit back and let it find jobs for you 🎯")
                else:
                    print("\n⚠️  Autonomous configuration failed.")
                    print("You can configure it later by editing config.yaml")
                    print("or running this setup again.")
            else:
                print("\n✅ Profile setup complete!")
                print("\nYou can configure autonomous mode later:")
                print("  • Edit config.yaml manually, or")
                print("  • Run: python setup_profile.py")
                print("\nFor manual job search:")
                print("  1. Run: python run_scout.py")
                print("  2. Enter your user ID when prompted")
                print("  3. Scout will find jobs matching your profile")
        else:
            print("\n❌ Profile setup failed or was cancelled.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if "graph" in locals():
            graph.close()


if __name__ == "__main__":
    main()
