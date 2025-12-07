"""
Test script for WriterAgent - Generate tailored resumes and cover letters.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import Config
from core.user_profile import UserProfile
from graph.memory import GraphMemory
from agents.writer_agent import WriterAgent
from agents.matcher_agent import MatcherAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_writer_agent():
    """Test WriterAgent document generation."""

    print("=" * 80)
    print("Testing Writer Agent - Resume & Cover Letter Generation")
    print("=" * 80)
    print()

    # Initialize components
    config_path = Path(__file__).parent.parent / "config.yaml"
    config = Config(str(config_path))
    neo = config.get_neo4j_config()
    graph_memory = GraphMemory(
        uri=neo["uri"],
        user=neo["user"],
        password=neo["password"],
        database=neo["database"],
    )
    user_profile = UserProfile(graph_memory)

    # Initialize agents
    writer = WriterAgent(graph_memory, config, user_profile)
    matcher = MatcherAgent(graph_memory, config, user_profile)

    # Get user input
    user_id = (
        input("Enter your user ID (or press Enter to use 'dk007'): ").strip() or "dk007"
    )

    # Get user profile
    profile = user_profile.get_profile(user_id)
    if not profile:
        print(f"\n❌ User profile not found: {user_id}")
        print("Please create a profile first using setup_profile.py")
        return

    print(f"\n✓ Using profile: {profile.get('name', 'Unknown')}")

    # Check if resume exists
    resume = user_profile.get_resume(user_id)
    if not resume:
        print("\n⚠️  No resume found for this profile.")
        print("Please upload a resume using manage_profile.py (option 7)")
        print("The writer agent needs your resume to generate tailored documents.")
        return

    print(f"  Resume: {len(resume)} characters")

    # Get ranked jobs with match scores
    print("\n" + "-" * 80)
    print("Step 1: Get matched jobs")
    print("-" * 80)

    ranked_jobs = matcher.get_ranked_jobs(user_id, limit=10, min_score=50)

    if not ranked_jobs:
        print("\n⚠️  No matched jobs found.")
        print("Please run the matcher first with: python run_matcher.py")
        return

    print(f"\n✓ Found {len(ranked_jobs)} matched jobs")
    print("\nTop matched jobs:")
    for i, job in enumerate(ranked_jobs[:5], 1):
        score = job.get("match_score") or 0
        print(
            f"  {i}. {job.get('title', 'Unknown')} - {job.get('company_name', 'Unknown')} (Score: {score:.0f}/100)"
        )

    # Select a job
    print("\n" + "-" * 80)
    print("Step 2: Select a job to generate documents for")
    print("-" * 80)

    job_choice = input(
        f"\nEnter job number (1-{min(5, len(ranked_jobs))}), or press Enter for #1: "
    ).strip()

    try:
        job_index = int(job_choice) - 1 if job_choice else 0
        if job_index < 0 or job_index >= len(ranked_jobs):
            job_index = 0
    except ValueError:
        job_index = 0

    selected_job = ranked_jobs[job_index]
    job_id = selected_job.get("job_id")

    print(
        f"\n✓ Selected: {selected_job.get('title')} at {selected_job.get('company_name')}"
    )
    print(f"  Match Score: {selected_job.get('match_score', 0):.0f}/100")

    # Prepare match insights
    match_insights = {
        "score": selected_job.get("match_score", 0),
        "reason": selected_job.get("match_reason", ""),
        "strengths": selected_job.get("strengths", []),
        "concerns": selected_job.get("concerns", []),
    }

    # Generate documents
    print("\n" + "-" * 80)
    print("Step 3: Generate tailored documents")
    print("-" * 80)

    print("\n📝 Generating tailored resume...")
    tailored_resume = writer.generate_tailored_resume(user_id, job_id, match_insights)

    if tailored_resume:
        print(f"✓ Generated resume ({len(tailored_resume)} characters)")
        print("\n--- RESUME PREVIEW (first 500 chars) ---")
        print(tailored_resume[:500])
        print("...\n")
    else:
        print("❌ Failed to generate resume")

    print("\n💌 Generating cover letter...")
    cover_letter = writer.generate_cover_letter(user_id, job_id, match_insights)

    if cover_letter:
        print(f"✓ Generated cover letter ({len(cover_letter)} characters)")
        print("\n--- COVER LETTER PREVIEW (first 500 chars) ---")
        print(cover_letter[:500])
        print("...\n")
    else:
        print("❌ Failed to generate cover letter")

    # Export documents
    print("\n" + "-" * 80)
    print("Step 4: Export documents")
    print("-" * 80)

    export_choice = (
        input("\nExport documents? (txt/docx/both/skip) [txt]: ").strip().lower()
        or "txt"
    )

    exported_files = {}

    if export_choice in ["txt", "both"]:
        print("\n📄 Exporting as text files...")
        files = writer.export_to_text(user_id, job_id)
        exported_files.update(files)

        if files:
            print(f"✓ Exported text files:")
            for doc_type, path in files.items():
                print(f"  - {doc_type}: {path}")

    if export_choice in ["docx", "both"]:
        print("\n📄 Exporting as DOCX files...")
        files = writer.export_to_docx(user_id, job_id)
        exported_files.update(files)

        if files:
            print(f"✓ Exported DOCX files:")
            for doc_type, path in files.items():
                print(f"  - {doc_type}: {path}")
        else:
            print("⚠️  DOCX export requires python-docx: pip install python-docx")

    if exported_files:
        print(f"\n✓ All documents saved to: {Path('outputs').absolute()}")

    print("\n" + "=" * 80)
    print("Writer Agent Testing Complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        test_writer_agent()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
