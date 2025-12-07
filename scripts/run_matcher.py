"""
Test script for the LLM-based Matcher Agent.
Run this AFTER Scout has collected jobs.
"""

import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from agents.matcher_agent import MatcherAgent
from core.config import Config
from core.user_profile import UserProfile
from graph.memory import GraphMemory

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Suppress neo4j notifications
logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def test_matcher_scoring():
    """Test Matcher Agent LLM-based job scoring."""

    print("\n" + "=" * 80)
    print("Testing Matcher Agent - LLM Scoring Mode")
    print("Scores ALL jobs collected by Scout Agent")
    print("=" * 80 + "\n")

    # Initialize components
    config_path = Path(__file__).parent.parent / "config.yaml"
    config = Config(str(config_path))

    # Initialize GraphMemory and UserProfile
    neo = config.get_neo4j_config()
    graph = GraphMemory(
        uri=neo["uri"],
        user=neo["user"],
        password=neo["password"],
        database=neo["database"],
    )
    user_profile = UserProfile(graph)
    matcher = MatcherAgent(graph_memory=graph, config=config, user_profile=user_profile)

    # Get or create test user
    user_id = (
        input("Enter your user ID (or press Enter to use 'test_user'): ").strip()
        or "test_user"
    )

    try:
        profile = user_profile.get_profile(user_id)
        if not profile:
            print(f"\n⚠️  No profile found for {user_id}")
            print("Creating a test profile...")
            user_profile.create_profile(
                user_id=user_id,
                name="Test User",
                email="test@example.com",
                skills=[
                    "Python",
                    "Machine Learning",
                    "Data Science",
                    "SQL",
                    "TensorFlow",
                ],
                experience_years=3,
                preferences={
                    "employment_types": ["FULLTIME", "INTERN"],
                    "remote_only": True,
                    "salary_min": 70000,
                },
            )
            profile = user_profile.get_profile(user_id)

        print(f"\n✓ Using profile: {profile.get('name', user_id)}")
        print(f"  Skills: {', '.join(profile.get('skills', []))}")
        print(f"  Experience: {profile.get('experience_years', 0)} years")

    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        return

    print("\n" + "-" * 80)
    print("Step 1: Score all unscored jobs with LLM")
    print("-" * 80)

    # Score all jobs with smaller batch to avoid rate limits
    result = matcher.run(
        user_id=user_id, batch_size=3
    )  # Process 3 jobs at a time to avoid rate limits

    if "error" in result:
        print(f"\n❌ Error: {result['error']}")
        return

    print(f"\n✓ Scoring complete!")
    print(f"  - Total jobs processed: {result.get('total_jobs', 0)}")
    print(f"  - Successfully scored: {result.get('scored', 0)}")
    print(f"  - Failed: {result.get('failed', 0)}")
    print(f"  - Average score: {result.get('average_score', 0):.1f}/100")

    score_range = result.get("score_range", {})
    print(
        f"  - Score range: {score_range.get('min', 0):.1f} - {score_range.get('max', 0):.1f}"
    )

    print("\n" + "-" * 80)
    print("Step 2: Retrieve ranked jobs")
    print("-" * 80)

    # Get top ranked jobs
    ranked_jobs = matcher.get_ranked_jobs(user_id, limit=10, min_score=50)

    if not ranked_jobs:
        print("\n⚠️  No ranked jobs found (maybe scores are below threshold?)")
    else:
        print(f"\n✓ Top {len(ranked_jobs)} matched jobs:\n")

        for i, job in enumerate(ranked_jobs, 1):
            print(
                f"{i}. {job.get('title', 'Unknown')} - {job.get('company', {}).get('name', 'Unknown')}"
            )
            # Handle None match_score gracefully
            match_score = job.get("match_score") or 0
            print(f"   Score: {match_score:.1f}/100")
            print(f"   Reason: {job.get('match_reason', 'N/A')}")

            strengths = job.get("strengths") or []
            if strengths:
                print(f"   ✓ Strengths: {', '.join(strengths[:2])}")

            concerns = job.get("concerns") or []
            if concerns:
                print(f"   ⚠  Concerns: {', '.join(concerns[:2])}")

            print()

    print("=" * 80)
    print("Matcher Testing Complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        test_matcher_scoring()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
