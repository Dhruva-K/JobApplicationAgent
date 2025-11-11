"""
Streamlit UI for Job Application Agent.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
import logging
from typing import Dict, List, Optional
import json

from workflow.job_application_graph import JobApplicationGraph
from core.config import Config
from graph.memory import ApplicationStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Job Application Agent",
    page_icon="💼",
    layout="wide"
)

# Initialize session state
if "workflow" not in st.session_state:
    try:
        config = Config()
        st.session_state.workflow = JobApplicationGraph(config)
        st.session_state.user_id = "default_user"
    except Exception as e:
        st.error(f"Failed to initialize workflow: {e}")
        st.stop()

if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "name": "",
        "email": "",
        "skills": [],
        "experience_years": 0,
        "education_level": ""
    }


def main():
    """Main application entry point."""
    st.title("💼 Job Application Agent")
    st.markdown("Automate your job search with AI-powered matching and document generation")
    
    # Sidebar navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Home", "Profile", "Job Search", "Matches", "Applications", "Documents"]
    )
    
    if page == "Home":
        show_home()
    elif page == "Profile":
        show_profile()
    elif page == "Job Search":
        show_job_search()
    elif page == "Matches":
        show_matches()
    elif page == "Applications":
        show_applications()
    elif page == "Documents":
        show_documents()


def show_home():
    """Display home page."""
    st.header("Welcome to Job Application Agent")
    
    st.markdown("""
    This application helps you:
    - 🔍 Search for jobs across multiple platforms
    - 🎯 Get personalized job recommendations
    - ✍️ Generate tailored resumes and cover letters
    - 📊 Track your applications
    
    **Get Started:**
    1. Set up your profile in the Profile section
    2. Search for jobs in the Job Search section
    3. View matches and generate documents
    4. Track your applications
    """)


def show_profile():
    """Display profile management page."""
    st.header("User Profile")
    
    with st.form("profile_form"):
        name = st.text_input("Name", value=st.session_state.user_profile.get("name", ""))
        email = st.text_input("Email", value=st.session_state.user_profile.get("email", ""))
        experience_years = st.number_input("Years of Experience", min_value=0, max_value=50, 
                                          value=st.session_state.user_profile.get("experience_years", 0))
        education_level = st.selectbox(
            "Education Level",
            ["High School", "Bachelor's", "Master's", "PhD", "Other"],
            index=0
        )
        
        st.subheader("Skills")
        skills_input = st.text_area(
            "Enter skills (comma-separated)",
            value=", ".join(st.session_state.user_profile.get("skills", []))
        )
        
        submitted = st.form_submit_button("Save Profile")
        
        if submitted:
            try:
                skills = [s.strip() for s in skills_input.split(",") if s.strip()]
                
                # Create or update profile
                user_profile = st.session_state.workflow.user_profile
                user_id = st.session_state.user_id
                
                user_profile.create_profile(
                    user_id=user_id,
                    name=name,
                    email=email,
                    skills=skills,
                    experience_years=experience_years,
                    education_level=education_level
                )
                
                st.session_state.user_profile = {
                    "name": name,
                    "email": email,
                    "skills": skills,
                    "experience_years": experience_years,
                    "education_level": education_level
                }
                
                st.success("Profile saved successfully!")
                
            except Exception as e:
                st.error(f"Error saving profile: {e}")


def show_job_search():
    """Display job search page."""
    st.header("Job Search")
    
    with st.form("job_search_form"):
        keywords = st.text_input("Keywords", placeholder="e.g., software engineer, python developer")
        location = st.text_input("Location (optional)", placeholder="e.g., remote, New York")
        employment_type = st.selectbox(
            "Employment Type",
            ["", "FULLTIME", "PARTTIME", "CONTRACTOR", "INTERN"],
            index=0
        )
        
        col1, col2 = st.columns(2)
        with col1:
            max_results = st.number_input("Max Results", min_value=1, max_value=100, value=50)
        with col2:
            api_source = st.selectbox("API Source", ["jsearch", "remotive"], index=0)
        
        submitted = st.form_submit_button("Search Jobs")
        
        if submitted and keywords:
            with st.spinner("Searching for jobs..."):
                try:
                    jobs = st.session_state.workflow.search_jobs(
                        keywords=keywords,
                        location=location if location else None,
                        employment_type=employment_type if employment_type else None
                    )
                    
                    if jobs:
                        st.session_state.search_results = jobs
                        st.success(f"Found {len(jobs)} jobs!")
                    else:
                        st.warning("No jobs found. Try different keywords.")
                        
                except Exception as e:
                    st.error(f"Error searching jobs: {e}")
    
    # Display search results
    if "search_results" in st.session_state:
        st.subheader("Search Results")
        
        for i, job in enumerate(st.session_state.search_results[:20]):  # Show first 20
            with st.expander(f"{job.get('title', 'Unknown')} - {job.get('company_name', 'Unknown Company')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Location:** {job.get('location', 'N/A')}")
                    st.write(f"**Type:** {job.get('employment_type', 'N/A')}")
                with col2:
                    st.write(f"**Source:** {job.get('source', 'N/A')}")
                    if job.get('salary_min'):
                        st.write(f"**Salary:** ${job.get('salary_min', '')} - ${job.get('salary_max', '')}")
                
                st.write(f"**Description:** {job.get('description', '')[:500]}...")
                
                if st.button(f"Select Job {i+1}", key=f"select_{i}"):
                    st.session_state.selected_job = job
                    st.rerun()


def show_matches():
    """Display job matches page."""
    st.header("Job Matches")
    
    user_id = st.session_state.user_id
    
    if st.button("Refresh Matches"):
        with st.spinner("Finding matches..."):
            try:
                matches = st.session_state.workflow.get_matches(user_id)
                st.session_state.matches = matches
            except Exception as e:
                st.error(f"Error getting matches: {e}")
    
    if "matches" in st.session_state and st.session_state.matches:
        st.subheader(f"Found {len(st.session_state.matches)} matches")
        
        for i, match in enumerate(st.session_state.matches):
            job = match.get("job", {})
            score = match.get("match_score", 0.0)
            
            with st.expander(f"{job.get('title', 'Unknown')} - Match Score: {score:.2%}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Match Score", f"{score:.2%}")
                    st.write(f"**Company:** {job.get('company_name', 'N/A')}")
                    st.write(f"**Location:** {job.get('location', 'N/A')}")
                with col2:
                    matched_skills = match.get("matched_skills", [])
                    missing_skills = match.get("missing_skills", [])
                    st.write(f"**Matched Skills:** {', '.join(matched_skills[:5])}")
                    if missing_skills:
                        st.write(f"**Missing Skills:** {', '.join(missing_skills[:5])}")
                
                if st.button(f"Generate Documents", key=f"gen_docs_{i}"):
                    st.session_state.selected_job_id = job.get("job_id")
                    st.rerun()
    else:
        st.info("No matches found. Search for jobs first or update your profile.")


def show_applications():
    """Display applications tracking page."""
    st.header("Application Tracking")
    
    user_id = st.session_state.user_id
    
    try:
        tracker = st.session_state.workflow.tracker_agent
        statistics = tracker.get_application_statistics(user_id)
        
        # Display statistics
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total", statistics.get("total_applications", 0))
        with col2:
            st.metric("Pending", statistics.get("pending", 0))
        with col3:
            st.metric("Submitted", statistics.get("submitted", 0))
        with col4:
            st.metric("Interview", statistics.get("interview", 0))
        with col5:
            st.metric("Accepted", statistics.get("accepted", 0))
        
        # Display recent applications
        st.subheader("Recent Applications")
        applications = tracker.get_recent_applications(user_id, limit=20)
        
        if applications:
            for app in applications:
                job = app.get("job", {})
                status = app.get("status", "unknown")
                
                with st.expander(f"{job.get('title', 'Unknown')} - {status.upper()}"):
                    st.write(f"**Company:** {job.get('company_name', 'N/A')}")
                    st.write(f"**Applied:** {app.get('applied_date', 'N/A')}")
                    st.write(f"**Status:** {status}")
                    if app.get("match_score"):
                        st.write(f"**Match Score:** {app.get('match_score'):.2%}")
        else:
            st.info("No applications yet. Generate documents for a job to create an application.")
            
    except Exception as e:
        st.error(f"Error loading applications: {e}")


def show_documents():
    """Display document generation page."""
    st.header("Document Generation")
    
    user_id = st.session_state.user_id
    
    # Job selection
    if "selected_job_id" in st.session_state:
        job_id = st.session_state.selected_job_id
        job = st.session_state.workflow.graph_memory.get_job(job_id)
        
        if job:
            st.subheader(f"Generating documents for: {job.get('title', 'Unknown')}")
            
            if st.button("Generate Documents"):
                with st.spinner("Generating documents..."):
                    try:
                        documents = st.session_state.workflow.generate_documents(user_id, job_id)
                        
                        if documents:
                            st.session_state.generated_documents = documents
                            st.session_state.generated_job_id = job_id
                            st.success("Documents generated successfully!")
                        else:
                            st.warning("Failed to generate documents.")
                            
                    except Exception as e:
                        st.error(f"Error generating documents: {e}")
    
    # Display generated documents
    if "generated_documents" in st.session_state:
        documents = st.session_state.generated_documents
        
        tabs = st.tabs(list(documents.keys()))
        
        for i, (doc_type, content) in enumerate(documents.items()):
            with tabs[i]:
                st.text_area(
                    doc_type.replace("_", " ").title(),
                    value=content,
                    height=400
                )
                
                st.download_button(
                    f"Download {doc_type.replace('_', ' ').title()}",
                    data=content,
                    file_name=f"{doc_type}_{st.session_state.generated_job_id}.txt",
                    mime="text/plain"
                )
    else:
        st.info("Select a job from Matches or Job Search to generate documents.")


if __name__ == "__main__":
    main()

