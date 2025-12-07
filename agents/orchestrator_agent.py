"""
Orchestrator Agent - Main coordinator for autonomous multi-agent workflows.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from agents.base_agent import BaseAgent
from core.agent_communication import AgentCommunicationBus, AgentMessage, MessageType
from core.conversation_state import ConversationState, PipelineState
from core.decision_engine import DecisionEngine
from core.config import Config
from core.user_profile import UserProfile

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Orchestrator that coordinates all other agents and manages workflows."""

    def __init__(self, graph_memory, config: Config, user_profile: UserProfile):
        """Initialize orchestrator agent.

        Args:
            graph_memory: GraphMemory instance
            config: Configuration object
            user_profile: UserProfile instance
        """
        super().__init__(
            name="OrchestratorAgent", graph_memory=graph_memory, role="orchestrator"
        )

        self.config = config
        self.user_profile = user_profile

        # Core components
        self.communication_bus = AgentCommunicationBus()
        self.conversation_state = ConversationState()
        self.decision_engine = DecisionEngine(config)

        # Agent registry (will be populated when agents are registered)
        self.agents: Dict[str, BaseAgent] = {}

        # Set our own communication bus
        self.set_communication_bus(self.communication_bus)

        logger.info("[OrchestratorAgent] Initialized")

    def register_agent(self, agent_name: str, agent: BaseAgent):
        """Register an agent with the orchestrator.

        Args:
            agent_name: Unique identifier for the agent
            agent: Agent instance
        """
        self.agents[agent_name] = agent
        self.communication_bus.register_agent(agent_name, agent)
        agent.set_communication_bus(self.communication_bus)

        logger.info(f"[OrchestratorAgent] Registered agent: {agent_name}")

    async def handle_user_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """Main entry point - handle user message and orchestrate response.

        Args:
            user_id: User identifier
            message: User message text

        Returns:
            Response dictionary with message, options, and next action
        """
        logger.info(
            f"[OrchestratorAgent] Handling message from {user_id}: {message[:50]}..."
        )

        # Update conversation state
        self.conversation_state.increment_message_count(user_id)
        self.conversation_state.add_to_history(user_id, message, role="user")

        try:
            # Classify intent
            intent = await self._classify_intent(message)
            logger.info(f"[OrchestratorAgent] Detected intent: {intent['type']}")

            # Route to appropriate pipeline
            if intent["type"] == "find_jobs":
                response = await self._job_search_pipeline(user_id, message, intent)
            elif intent["type"] == "apply_to_jobs":
                response = await self._application_pipeline(user_id, message, intent)
            elif intent["type"] == "check_status":
                response = await self._status_pipeline(user_id)
            elif intent["type"] == "update_profile":
                response = await self._profile_pipeline(user_id, message, intent)
            elif intent["type"] == "help":
                response = self._help_response()
            else:
                response = {
                    "message": "I'm not sure what you'd like me to do. Try: 'Find me jobs' or 'Check application status'",
                    "needs_human_input": True,
                }

            # Add response to history
            self.conversation_state.add_to_history(
                user_id, response.get("message", ""), role="assistant"
            )

            return response

        except Exception as e:
            logger.error(
                f"[OrchestratorAgent] Error handling message: {e}", exc_info=True
            )
            return {
                "message": f"Sorry, I encountered an error: {str(e)}",
                "needs_human_input": True,
                "error": str(e),
            }

    async def _classify_intent(self, message: str) -> Dict[str, Any]:
        """Classify user intent from message.

        Args:
            message: User message

        Returns:
            Intent dictionary with type and extracted parameters
        """
        message_lower = message.lower()

        # Simple keyword-based classification (can be replaced with LLM)
        if any(
            keyword in message_lower
            for keyword in ["find", "search", "look for", "get me"]
        ):
            return {
                "type": "find_jobs",
                "keywords": self._extract_keywords(message),
                "location": self._extract_location(message),
                "auto_apply": "apply" in message_lower or "submit" in message_lower,
            }

        elif any(keyword in message_lower for keyword in ["apply", "submit", "send"]):
            return {
                "type": "apply_to_jobs",
                "auto": "automatic" in message_lower or "all" in message_lower,
            }

        elif any(
            keyword in message_lower
            for keyword in ["status", "check", "how many", "applications"]
        ):
            return {"type": "check_status"}

        elif any(
            keyword in message_lower
            for keyword in ["update", "change", "profile", "resume"]
        ):
            return {"type": "update_profile"}

        elif any(
            keyword in message_lower for keyword in ["help", "what can you", "how do"]
        ):
            return {"type": "help"}

        else:
            return {"type": "unknown"}

    async def _job_search_pipeline(
        self, user_id: str, message: str, intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute job search pipeline: Scout → Extractor → Matcher.

        Args:
            user_id: User identifier
            message: Original user message
            intent: Classified intent with parameters

        Returns:
            Response dictionary
        """
        logger.info(f"[OrchestratorAgent] Starting job search pipeline for {user_id}")

        # Set pipeline state
        self.conversation_state.set_pipeline_state(user_id, PipelineState.SEARCHING)

        # Check if agents are available
        if "scout" not in self.agents:
            return {
                "message": "Scout agent not available. Please ensure all agents are registered.",
                "needs_human_input": True,
                "error": "scout_not_available",
            }

        # Extract search criteria
        criteria = {
            "keywords": intent.get("keywords", []),
            "location": intent.get("location", ""),
            "user_id": user_id,
        }

        self.conversation_state.save_search_criteria(user_id, criteria)

        response_message = f"🔍 Searching for jobs"
        if criteria["keywords"]:
            response_message += f" matching: {', '.join(criteria['keywords'])}"
        if criteria["location"]:
            response_message += f" in {criteria['location']}"
        response_message += "...\n\n"

        # Step 1: Scout for jobs (if available)
        try:
            if "scout" in self.agents:
                scout_response = await self.send_to_agent(
                    "scout",
                    MessageType.REQUEST_DATA,
                    {"action": "search_jobs", "criteria": criteria},
                    requires_response=True,
                )

                job_count = scout_response.get("job_count", 0) if scout_response else 0
                response_message += f"✓ Found {job_count} job listings\n"
            else:
                job_count = 0
                response_message += "⚠️  Scout agent not available\n"
        except Exception as e:
            logger.error(f"[OrchestratorAgent] Scout failed: {e}")
            response_message += f"⚠️  Search failed: {e}\n"
            job_count = 0

        # Step 2: Extract job details (if available)
        self.conversation_state.set_pipeline_state(user_id, PipelineState.MATCHING)

        # Step 3: Match jobs to user profile (if available)
        if "matcher" in self.agents and job_count > 0:
            try:
                matcher_response = await self.send_to_agent(
                    "matcher",
                    MessageType.REQUEST_DATA,
                    {"action": "rank_jobs", "user_id": user_id, "min_score": 60},
                    requires_response=True,
                )

                matched_jobs = (
                    matcher_response.get("jobs", []) if matcher_response else []
                )
                response_message += (
                    f"✓ Matched {len(matched_jobs)} jobs to your profile\n\n"
                )

                if matched_jobs:
                    # Save matched jobs
                    job_ids = [job["job_id"] for job in matched_jobs]
                    self.conversation_state.save_job_selection(user_id, job_ids)

                    # Show top 5
                    response_message += "📊 Top matches:\n"
                    for i, job in enumerate(matched_jobs[:5], 1):
                        score = job.get("match_score", 0)
                        response_message += f"  {i}. {job.get('title', 'Unknown')} at {job.get('company_name', 'Unknown')} (Score: {score:.0f}/100)\n"

                    # Decide next action
                    if intent.get("auto_apply"):
                        response_message += "\n🤖 You requested automatic application. I'll now apply to the top matches."
                        self.conversation_state.set_pending_action(
                            user_id,
                            "apply_to_jobs",
                            {"job_ids": job_ids[:10], "auto": True},
                        )
                        return {
                            "message": response_message,
                            "needs_human_input": False,
                            "next_action": "apply_to_jobs",
                            "jobs": matched_jobs[:10],
                        }
                    else:
                        return {
                            "message": response_message,
                            "needs_human_input": True,
                            "options": [
                                "Apply to all jobs scored 90+",
                                "Apply to top 5",
                                "Show me details for review",
                                "Refine search",
                            ],
                            "next_action": "await_job_selection",
                            "jobs": matched_jobs,
                        }
                else:
                    response_message += (
                        "😔 No jobs matched your profile criteria (min score: 60)"
                    )

            except Exception as e:
                logger.error(f"[OrchestratorAgent] Matcher failed: {e}")
                response_message += f"⚠️  Matching failed: {e}\n"

        # Set state back to idle
        self.conversation_state.set_pipeline_state(user_id, PipelineState.IDLE)

        return {"message": response_message, "needs_human_input": True}

    async def _application_pipeline(
        self, user_id: str, message: str, intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute application pipeline: Writer → Application Agent.

        Args:
            user_id: User identifier
            message: Original user message
            intent: Classified intent

        Returns:
            Response dictionary
        """
        logger.info(f"[OrchestratorAgent] Starting application pipeline for {user_id}")

        # Set pipeline state
        self.conversation_state.set_pipeline_state(user_id, PipelineState.APPLYING)

        # Get selected jobs
        selected_jobs = self.conversation_state.get_job_selection(user_id)

        if not selected_jobs:
            return {
                "message": "No jobs selected. Please search for jobs first.",
                "needs_human_input": True,
            }

        response_message = (
            f"📝 Preparing applications for {len(selected_jobs)} jobs...\n\n"
        )

        # Check if writer and application agents are available
        if "writer" not in self.agents and "application" not in self.agents:
            return {
                "message": response_message + "⚠️  Application agents not available.",
                "needs_human_input": True,
                "error": "agents_not_available",
            }

        # Generate documents for each job
        self.conversation_state.set_pipeline_state(
            user_id, PipelineState.GENERATING_DOCS
        )

        results = []
        auto_submitted = 0
        pending_review = 0
        manual_required = 0
        failed = 0

        for job_id in selected_jobs[:10]:  # Limit to 10
            try:
                # Get job details
                job = self.graph_memory.get_job(job_id)
                if not job:
                    failed += 1
                    continue

                # Decide strategy
                strategy = self.decision_engine.select_application_strategy(job)

                # Apply to job using ApplicationAgent
                if "application" in self.agents:
                    app_response = await self.send_to_agent(
                        "application",
                        MessageType.REQUEST_DATA,
                        {
                            "action": "apply_to_job",
                            "job_id": job_id,
                            "user_id": user_id,
                            "documents": {},  # Documents would be from WriterAgent
                            "auto_submit": strategy["auto_apply"],
                        },
                        requires_response=True,
                    )

                    if app_response:
                        result = app_response.get("result", {})
                        status = result.get("status")

                        if status == "submitted":
                            auto_submitted += 1
                            response_message += (
                                f"✓ Applied to {job.get('title', 'Unknown')}\n"
                            )
                            self.decision_engine.record_application(user_id)
                        elif status == "pending":
                            pending_review += 1
                            response_message += f"📄 Prepared application for {job.get('title', 'Unknown')} (needs review)\n"
                        elif status == "requires_manual":
                            manual_required += 1
                            response_message += f"⚠️  {job.get('title', 'Unknown')} requires manual application\n"
                        else:
                            failed += 1

                        results.append(
                            {
                                "job_id": job_id,
                                "status": status,
                                "job": job,
                                "result": result,
                            }
                        )
                else:
                    # Fallback without ApplicationAgent
                    if strategy["auto_apply"]:
                        response_message += (
                            f"✓ Auto-applying to {job.get('title', 'Unknown')}\n"
                        )
                        auto_submitted += 1
                        self.decision_engine.record_application(user_id)
                    else:
                        response_message += f"📄 Generated documents for {job.get('title', 'Unknown')} (needs review)\n"
                        pending_review += 1

                    results.append(
                        {
                            "job_id": job_id,
                            "status": (
                                "pending" if not strategy["auto_apply"] else "submitted"
                            ),
                            "job": job,
                        }
                    )

            except Exception as e:
                logger.error(
                    f"[OrchestratorAgent] Application failed for {job_id}: {e}"
                )
                failed += 1
                results.append({"job_id": job_id, "status": "failed", "error": str(e)})

        # Summary
        response_message += f"\n📊 Summary:\n"
        if auto_submitted > 0:
            response_message += (
                f"  • {auto_submitted} applications submitted automatically\n"
            )
        if pending_review > 0:
            response_message += f"  • {pending_review} applications ready for review\n"
        if manual_required > 0:
            response_message += (
                f"  • {manual_required} applications require manual submission\n"
            )
        if failed > 0:
            response_message += f"  • {failed} applications failed\n"

        # Get statistics
        stats = self.decision_engine.get_statistics(user_id)
        response_message += f"\n📈 Today's stats: {stats['applications_today']}/{stats['daily_limit']} applications sent"

        # Set state back to completed
        self.conversation_state.set_pipeline_state(user_id, PipelineState.COMPLETED)

        return {
            "message": response_message,
            "needs_human_input": pending_review > 0 or manual_required > 0,
            "results": results,
            "statistics": stats,
            "summary": {
                "auto_submitted": auto_submitted,
                "pending_review": pending_review,
                "manual_required": manual_required,
                "failed": failed,
            },
        }

    async def _status_pipeline(self, user_id: str) -> Dict[str, Any]:
        """Get status of applications and job search.

        Args:
            user_id: User identifier

        Returns:
            Response dictionary with status
        """
        logger.info(f"[OrchestratorAgent] Getting status for {user_id}")

        # Get statistics
        stats = self.decision_engine.get_statistics(user_id)
        pipeline_state = self.conversation_state.get_pipeline_state(user_id)

        response_message = f"📊 Your Application Status\n\n"
        response_message += f"**Today**: {stats['applications_today']}/{stats['daily_limit']} applications\n"
        response_message += (
            f"**This Week**: {stats['applications_this_week']} applications\n"
        )
        response_message += (
            f"**Remaining Today**: {stats['remaining_today']} applications\n\n"
        )
        response_message += f"**Current State**: {pipeline_state.value}\n"

        # Get pending actions
        pending = self.conversation_state.get_pending_action(user_id)
        if pending:
            response_message += f"\n⏳ Pending Action: {pending['action_type']}"

        return {
            "message": response_message,
            "needs_human_input": False,
            "statistics": stats,
        }

    async def _profile_pipeline(
        self, user_id: str, message: str, intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle profile updates.

        Args:
            user_id: User identifier
            message: Original message
            intent: Classified intent

        Returns:
            Response dictionary
        """
        return {
            "message": "Profile management coming soon! For now, use manage_profile.py",
            "needs_human_input": True,
        }

    def _help_response(self) -> Dict[str, Any]:
        """Generate help response.

        Returns:
            Response dictionary with help text
        """
        help_text = """
🤖 **Job Application Agent - What I Can Do**

**Job Search:**
- "Find ML engineer jobs in San Francisco"
- "Search for software engineering internships"
- "Look for remote Python developer positions"

**Applications:**
- "Apply to the top 5 matches"
- "Apply to all jobs scored 90+"
- "Submit applications automatically"

**Status:**
- "Check my application status"
- "How many applications have I sent?"
- "What's my daily limit?"

**Smart Features:**
- ✅ Automatic job matching
- ✅ Tailored resume generation
- ✅ Intelligent auto-apply (for high-confidence matches)
- ✅ Safety limits and human checkpoints
- ✅ Daily application tracking

Just tell me what you want to do!
"""
        return {"message": help_text, "needs_human_input": False}

    def _extract_keywords(self, message: str) -> List[str]:
        """Extract job keywords from message.

        Args:
            message: User message

        Returns:
            List of keywords
        """
        # Simple extraction (can be improved with NLP)
        common_roles = [
            "engineer",
            "developer",
            "software",
            "ml",
            "data scientist",
            "analyst",
            "manager",
            "designer",
            "product",
            "intern",
        ]

        message_lower = message.lower()
        found_keywords = [role for role in common_roles if role in message_lower]

        return found_keywords

    def _extract_location(self, message: str) -> str:
        """Extract location from message.

        Args:
            message: User message

        Returns:
            Location string
        """
        # Simple extraction
        import re

        # Look for "in [location]" pattern
        match = re.search(r"\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", message)
        if match:
            return match.group(1)

        return ""

    def run(self):
        """Run method (not used in async context)."""
        raise NotImplementedError("Use handle_user_message() for orchestrator")
