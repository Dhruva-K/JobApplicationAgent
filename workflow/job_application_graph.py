"""
LangGraph workflow for orchestrating job application agents.
"""

import logging
from typing import Dict, List, Optional, Any, TypedDict
from langgraph.graph import StateGraph, END

from agents.scout_agent import ScoutAgent
from agents.extractor_agent import ExtractorAgent
from agents.matcher_agent import MatcherAgent
from agents.writer_agent import WriterAgent
from agents.tracker_agent import TrackerAgent
from graph.memory import GraphMemory
from llm.llama_client import create_llm_client
from utils.embeddings import EmbeddingGenerator
from core.config import Config
from core.user_profile import UserProfile

logger = logging.getLogger(__name__)


class JobApplicationState(TypedDict):
    """State schema for the job application workflow."""
    user_id: str
    user_query: Optional[str]
    keywords: Optional[str]
    location: Optional[str]
    employment_type: Optional[str]
    jobs: List[Dict[str, Any]]
    extracted_data: Dict[str, Dict[str, Any]]
    matches: List[Dict[str, Any]]
    selected_job_id: Optional[str]
    documents: Dict[str, str]
    application_id: Optional[str]
    application_status: Optional[str]
    error: Optional[str]


class JobApplicationGraph:
    """LangGraph workflow for job application automation."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the job application workflow.
        
        Args:
            config: Configuration instance (creates default if None)
        """
        if config is None:
            config = Config()
        
        self.config = config
        
        # Initialize components
        neo4j_config = config.get_neo4j_config()
        self.graph_memory = GraphMemory(
            uri=neo4j_config["uri"],
            user=neo4j_config["user"],
            password=neo4j_config["password"],
            database=neo4j_config["database"]
        )
        
        llm_config = config.get_llm_config()
        self.llm_client = create_llm_client(llm_config)
        
        embeddings_config = config.get("embeddings", {})
        self.embedding_generator = EmbeddingGenerator(
            model_name=embeddings_config.get("model", "sentence-transformers/all-MiniLM-L6-v2"),
            device=embeddings_config.get("device", "cpu")
        )
        
        # Initialize agents
        self.scout_agent = ScoutAgent(self.graph_memory, config)
        self.extractor_agent = ExtractorAgent(self.graph_memory, self.llm_client)
        self.matcher_agent = MatcherAgent(self.graph_memory, self.llm_client, self.embedding_generator)
        self.writer_agent = WriterAgent(self.graph_memory, self.llm_client)
        self.tracker_agent = TrackerAgent(self.graph_memory)
        self.user_profile = UserProfile(self.graph_memory)
        
        # Build graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine.
        
        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(JobApplicationState)
        
        # Add nodes
        workflow.add_node("scout", self._scout_node)
        workflow.add_node("extractor", self._extractor_node)
        workflow.add_node("matcher", self._matcher_node)
        workflow.add_node("writer", self._writer_node)
        workflow.add_node("tracker", self._tracker_node)
        
        # Define edges
        workflow.set_entry_point("scout")
        workflow.add_edge("scout", "extractor")
        workflow.add_edge("extractor", "matcher")
        
        # Conditional edge: matcher -> writer (if job selected) or END
        workflow.add_conditional_edges(
            "matcher",
            self._should_generate_documents,
            {
                "generate": "writer",
                "end": END
            }
        )
        
        workflow.add_edge("writer", "tracker")
        workflow.add_edge("tracker", END)
        
        return workflow.compile()
    
    def _scout_node(self, state: JobApplicationState) -> JobApplicationState:
        """Scout agent node: Search for jobs.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        try:
            keywords = state.get("keywords") or state.get("user_query", "")
            location = state.get("location")
            employment_type = state.get("employment_type")
            
            if not keywords:
                state["error"] = "No search keywords provided"
                return state
            
            # Search and store jobs
            jobs = self.scout_agent.search_and_store(
                keywords=keywords,
                location=location,
                employment_type=employment_type,
                max_results=50
            )
            
            state["jobs"] = jobs
            logger.info(f"Scout found {len(jobs)} jobs")
            
        except Exception as e:
            logger.error(f"Error in scout node: {e}")
            state["error"] = str(e)
        
        return state
    
    def _extractor_node(self, state: JobApplicationState) -> JobApplicationState:
        """Extractor agent node: Extract structured information from jobs.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        try:
            jobs = state.get("jobs", [])
            if not jobs:
                state["error"] = "No jobs to extract"
                return state
            
            extracted_data = {}
            
            for job in jobs:
                job_id = job.get("job_id")
                if job_id:
                    extracted = self.extractor_agent.extract_job_info(job_id)
                    if extracted:
                        extracted_data[job_id] = extracted
            
            state["extracted_data"] = extracted_data
            logger.info(f"Extracted information from {len(extracted_data)} jobs")
            
        except Exception as e:
            logger.error(f"Error in extractor node: {e}")
            state["error"] = str(e)
        
        return state
    
    def _matcher_node(self, state: JobApplicationState) -> JobApplicationState:
        """Matcher agent node: Match user to jobs.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        try:
            user_id = state.get("user_id")
            if not user_id:
                state["error"] = "User ID not provided"
                return state
            
            jobs = state.get("jobs", [])
            job_ids = [job.get("job_id") for job in jobs if job.get("job_id")]
            
            if not job_ids:
                state["error"] = "No jobs to match"
                return state
            
            # Match jobs
            matches = self.matcher_agent.match_jobs(
                user_id=user_id,
                job_ids=job_ids,
                min_score=0.6
            )
            
            state["matches"] = matches
            logger.info(f"Matcher found {len(matches)} matches")
            
        except Exception as e:
            logger.error(f"Error in matcher node: {e}")
            state["error"] = str(e)
        
        return state
    
    def _writer_node(self, state: JobApplicationState) -> JobApplicationState:
        """Writer agent node: Generate documents.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        try:
            user_id = state.get("user_id")
            job_id = state.get("selected_job_id")
            
            if not user_id or not job_id:
                state["error"] = "User ID or job ID not provided"
                return state
            
            documents = {}
            
            # Generate cover letter
            cover_letter = self.writer_agent.generate_cover_letter(user_id, job_id)
            if cover_letter:
                documents["cover_letter"] = cover_letter
            
            # Generate resume summary
            resume_summary = self.writer_agent.generate_resume_summary(user_id, job_id)
            if resume_summary:
                documents["resume_summary"] = resume_summary
            
            # Generate complete resume
            resume = self.writer_agent.generate_complete_resume(user_id, job_id)
            if resume:
                documents["resume"] = resume
            
            state["documents"] = documents
            logger.info(f"Generated {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Error in writer node: {e}")
            state["error"] = str(e)
        
        return state
    
    def _tracker_node(self, state: JobApplicationState) -> JobApplicationState:
        """Tracker agent node: Create application record.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        try:
            user_id = state.get("user_id")
            job_id = state.get("selected_job_id")
            
            if not user_id or not job_id:
                state["error"] = "User ID or job ID not provided"
                return state
            
            # Get match score if available
            matches = state.get("matches", [])
            match_score = None
            for match in matches:
                if match.get("job_id") == job_id:
                    match_score = match.get("match_score")
                    break
            
            # Create application
            application_id = self.tracker_agent.create_application(
                user_id=user_id,
                job_id=job_id,
                match_score=match_score
            )
            
            if application_id:
                state["application_id"] = application_id
                state["application_status"] = "pending"
                logger.info(f"Created application: {application_id}")
            else:
                state["error"] = "Failed to create application"
            
        except Exception as e:
            logger.error(f"Error in tracker node: {e}")
            state["error"] = str(e)
        
        return state
    
    def _should_generate_documents(self, state: JobApplicationState) -> str:
        """Determine if documents should be generated.
        
        Args:
            state: Current workflow state
            
        Returns:
            "generate" if documents should be generated, "end" otherwise
        """
        selected_job_id = state.get("selected_job_id")
        if selected_job_id:
            return "generate"
        return "end"
    
    def run(
        self,
        user_id: str,
        keywords: str,
        location: Optional[str] = None,
        employment_type: Optional[str] = None,
        selected_job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run the complete workflow.
        
        Args:
            user_id: User identifier
            keywords: Job search keywords
            location: Optional location filter
            employment_type: Optional employment type filter
            selected_job_id: Optional pre-selected job ID (skips search)
            
        Returns:
            Final workflow state
        """
        initial_state: JobApplicationState = {
            "user_id": user_id,
            "user_query": keywords,
            "keywords": keywords,
            "location": location,
            "employment_type": employment_type,
            "jobs": [],
            "extracted_data": {},
            "matches": [],
            "selected_job_id": selected_job_id,
            "documents": {},
            "application_id": None,
            "application_status": None,
            "error": None,
        }
        
        try:
            final_state = self.graph.invoke(initial_state)
            return final_state
        except Exception as e:
            logger.error(f"Error running workflow: {e}")
            initial_state["error"] = str(e)
            return initial_state
    
    def search_jobs(
        self,
        keywords: str,
        location: Optional[str] = None,
        employment_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for jobs (scout only).
        
        Args:
            keywords: Search keywords
            location: Optional location
            employment_type: Optional employment type
            
        Returns:
            List of job dictionaries
        """
        return self.scout_agent.search_and_store(
            keywords=keywords,
            location=location,
            employment_type=employment_type
        )
    
    def get_matches(
        self,
        user_id: str,
        job_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get job matches for a user.
        
        Args:
            user_id: User identifier
            job_ids: Optional list of job IDs
            
        Returns:
            List of matched jobs
        """
        return self.matcher_agent.match_jobs(user_id, job_ids)
    
    def generate_documents(
        self,
        user_id: str,
        job_id: str
    ) -> Dict[str, str]:
        """Generate documents for a job application.
        
        Args:
            user_id: User identifier
            job_id: Job identifier
            
        Returns:
            Dictionary of generated documents
        """
        documents = {}
        
        cover_letter = self.writer_agent.generate_cover_letter(user_id, job_id)
        if cover_letter:
            documents["cover_letter"] = cover_letter
        
        resume = self.writer_agent.generate_complete_resume(user_id, job_id)
        if resume:
            documents.update(resume)
        
        return documents
    
    def close(self):
        """Close database connections."""
        self.graph_memory.close()

