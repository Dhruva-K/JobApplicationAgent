"""
Test script for ScoutAgent
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.scout_agent import ScoutAgent
from graph.memory import GraphMemory
from core.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_scout_agent():
    """Test the ScoutAgent functionality."""

    try:
        # Initialize configuration and graph memory
        logger.info("Initializing configuration and graph memory...")
        config_path = Path(__file__).parent.parent / "config.yaml"
        config = Config(str(config_path))
        neo4j_config = config.get_neo4j_config()
        graph_memory = GraphMemory(
            uri=neo4j_config["uri"],
            user=neo4j_config["user"],
            password=neo4j_config["password"],
            database=neo4j_config["database"],
        )

        # Initialize ScoutAgent
        logger.info("Initializing ScoutAgent...")
        scout = ScoutAgent(graph_memory=graph_memory, config=config)

        # Test 1: Search jobs from JSearch
        logger.info("\n" + "=" * 60)
        logger.info("TEST 1: Searching jobs from JSearch API")
        logger.info("=" * 60)

        jobs = scout.search_jobs(
            keywords="software engineer intern",
            date_posted="today",
            employment_type="INTERN",
            max_results=5,
            api_source="jsearch",
        )

        logger.info(f"Found {len(jobs)} jobs from JSearch")

        if jobs:
            logger.info("\nFirst job details:")
            first_job = jobs[0]
            logger.info(f"Title: {first_job.get('title')}")
            logger.info(f"Company: {first_job.get('company_name')}")
            logger.info(f"Location: {first_job.get('location')}")
            logger.info(f"Employment Type: {first_job.get('employment_type')}")
            logger.info(f"URL: {first_job.get('url')}")
            logger.info(
                f"Qualifications: {len(first_job.get('qualifications', []))} items"
            )
            logger.info(
                f"Responsibilities: {len(first_job.get('responsibilities', []))} items"
            )

            # Print first few qualifications and responsibilities
            if first_job.get("qualifications"):
                logger.info("\nSample Qualifications:")
                for qual in first_job["qualifications"][:3]:
                    logger.info(f"  - {qual}")

            if first_job.get("responsibilities"):
                logger.info("\nSample Responsibilities:")
                for resp in first_job["responsibilities"][:3]:
                    logger.info(f"  - {resp}")

        # Test 2: Store jobs in graph database
        logger.info("\n" + "=" * 60)
        logger.info("TEST 2: Storing jobs in graph database")
        logger.info("=" * 60)

        if jobs:
            stored_ids = scout.store_jobs(jobs)
            logger.info(f"Successfully stored {len(stored_ids)} jobs")
            logger.info(f"Job IDs: {stored_ids[:3]}...")  # Show first 3 IDs
        else:
            logger.warning("No jobs to store")

        # Test 3: Run full cycle
        logger.info("\n" + "=" * 60)
        logger.info("TEST 3: Running full Scout Agent cycle")
        logger.info("=" * 60)

        scout.run(
            keywords="product manager intern",
            date_posted="today",
            employment_type="INTERN",
            max_results=3,
            api_source="jsearch",
        )

        # Test 4: Search from Remotive (if configured)
        logger.info("\n" + "=" * 60)
        logger.info("TEST 4: Searching jobs from Remotive API")
        logger.info("=" * 60)

        try:
            remotive_jobs = scout.search_jobs(
                keywords="developer",
                location=None,
                employment_type=None,
                max_results=3,
                api_source="remotive",
            )
            logger.info(f"Found {len(remotive_jobs)} jobs from Remotive")

            if remotive_jobs:
                logger.info(f"First Remotive job: {remotive_jobs[0].get('title')}")
        except Exception as e:
            logger.warning(f"Remotive test failed: {e}")

        logger.info("\n" + "=" * 60)
        logger.info("All tests completed!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
    finally:
        # Clean up
        if "graph_memory" in locals():
            graph_memory.close()
            logger.info("Graph memory connection closed")


if __name__ == "__main__":
    test_scout_agent()
