"""
Script to set up user profile for personalized job search.

This is a simple CLI wrapper around UserProfile.interactive_setup().
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


def main():
    """Run interactive profile setup."""
    try:
        # Initialize database connection
        config = Config()
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
            print(f"\n🎉 Setup complete! Your user ID is: {user_id}")
            print("\nNext steps:")
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
