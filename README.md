# 🤖Autonomous Job Application Agent with Graph-Based Memory: 
A Multi-Agent LLM System for Intelligent Job Search and Application Automation

<div align="center">

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.0+-green.svg)](https://github.com/langchain-ai/langgraph)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.15.0+-red.svg)](https://neo4j.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**An intelligent, autonomous multi-agent system that automates your entire job search and application process.**

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## 🎯 Overview

Job Application Agent is a sophisticated AI-powered system that revolutionizes job hunting by combining **LangGraph workflows**, **Neo4j graph memory**, and **LLM intelligence** to autonomously discover, evaluate, and apply to relevant job opportunities while you focus on what matters most.


## ✨ Features

### 🤖 **Autonomous Operation**
- **Continuous Job Discovery**: Searches multiple job boards every 3-6 hours
- **Smart Auto-Apply**: Automatically applies to high-match jobs (≥90% score)
- **Human-in-the-Loop**: Requests approval for good matches (75-89%)
- **Rate Limiting**: Respects daily/hourly limits (configurable: 5/day, 3/hour, 50/week)

### 🧠 **5 Specialized AI Agents**
| Agent | Role | Key Capabilities |
|-------|------|------------------|
| **Scout** | Job Discovery | Multi-platform search, API integration, smart filtering |
| **Extractor** | Data Extraction | NLP-based parsing, skill extraction, requirements analysis |
| **Matcher** | Candidate Matching | Semantic similarity, skill-based scoring, fit analysis |
| **Writer** | Document Generation | Personalized resumes, tailored cover letters, ATS optimization |
| **Tracker** | Application Management | Status tracking, analytics, follow-up reminders |

### 🗄️ **Graph-Based Memory (Neo4j)**
- Relational knowledge storage for jobs, skills, and applications
- Persistent learning from past applications
- Advanced querying and pattern recognition
- Visual exploration of your job search network

### 🔧 **Technology Stack**
- **LLM**: meta-llama/llama-4-scout-17b-16e-instruct (Groq API)
- **Orchestration**: LangGraph for stateful agent workflows
- **Database**: Neo4j for graph-based memory
- **Embeddings**: Sentence Transformers for semantic search
- **UI**: Streamlit dashboard + Rich CLI
- **Platform Support**: LinkedIn, Greenhouse, Lever, Workday, iCIMS, Indeed, and generic job boards

---

## 🏗️ Architecture

```

┌─────────────────────────────────────────────────────────────────┐
│                   LangGraph Orchestrator                        |
│              (State Management & Coordination)                  │
└────────┬──────────┬──────────┬──────────┬──────────┬────────────┘
         │          │          │          │          │
    ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌──▼─────┐ ┌──▼──────┐
    │ Scout  │ │Extract │ │ Matcher│ │ Writer │ │ Tracker │
    │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │ │ Agent   │
    └────┬───┘ └───┬────┘ └───┬────┘ └──┬─────┘ └──┬──────┘
         │         │          │         │          │
         └─────────┴──────────┴─────────┴──────────┘
                            │
              ┌─────────────┼─────────────┐
              │                           │
         ┌────▼─────┐              ┌─────▼──────┐
         │  Neo4j   │              │ LLM Engine │
         │ Graph DB │              │            │
         └──────────┘              └────────────┘
```

### Workflow Pipeline

```
1. DISCOVER  →  Scout finds jobs matching your criteria
2. EXTRACT   →  Extractor parses requirements and skills
3. MATCH     →  Matcher scores candidate-job fit (0-100%)
4. GENERATE  →  Writer creates tailored documents
5. APPLY     →  Application agent submits (optional)
6. TRACK     →  Tracker logs and monitors status
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Neo4j** (Desktop or Aura Cloud)
- **Ollama** with Llama 3 (or API keys for Groq/OpenAI)
- **Job API Keys** (optional): [JSearch](https://rapidapi.com/jsearch/api/jsearch), Remotive

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Dhruva-K/JobApplicationAgent.git
cd JobApplicationAgent

# 2. Create virtual environment
python -m venv jobagent
source jobagent/bin/activate  # On Windows: jobagent\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up Neo4j
# Download Neo4j Desktop: https://neo4j.com/download/
# Create a new database and note credentials

# 5. Setup LLM with Groq

# 6. Configure the system
cp config.yaml.example config.yaml
# Edit config.yaml with your credentials:
# - Neo4j: uri, user, password
# - LLM: provider, model_name, api_key
# - Job APIs: jsearch api_key
```

### 🎬 First Run (3 Simple Steps)

```bash
# Step 1: Quick setup wizard
python scripts/quick_setup.py

# Step 2: Create your profile
python scripts/setup_profile.py

# Step 3: Start autonomous mode
python scripts/run_autonomous.py
```

**That's it!** The agent will now:
- ✅ Search for jobs every 3 hours
- ✅ Auto-apply to excellent matches (≥90% score)
- ✅ Request approval for good matches (75-89%)
- ✅ Generate personalized resumes and cover letters
- ✅ Track all applications in Neo4j


## 📖 Usage Examples

### Manual Mode

Run individual agents for targeted tasks:

```bash
# Search for jobs
python scripts/run_scout.py --keywords "software engineer" --location "remote"

# Match jobs to your profile
python scripts/run_matcher.py --min-score 75

# Generate application documents
python scripts/run_writer.py --job-id "12345"
```

### Programmatic Usage

```python
from workflow.job_application_graph import JobApplicationGraph
from core.user_profile import UserProfile

# Initialize workflow
workflow = JobApplicationGraph()
profile = UserProfile.load("your_user_id")

# Run job search pipeline
result = workflow.run_pipeline(
    user_id=profile.user_id,
    keywords="machine learning engineer",
    location="remote",
    min_match_score=80
)

print(f"Found {len(result['matches'])} high-quality matches")
```

### Chat Interface

```bash
python scripts/chat_with_agent.py
```

**Example conversation:**
```
You: Find me ML engineering jobs in San Francisco
Agent: 🔍 Found 8 jobs. Top match: Senior ML Engineer at TechCorp (94% fit)

You: status
Agent: 📊 Last 7 days: 12 applications | 3 responses | 1 interview

You: update job #5 to interview scheduled
Agent: ✅ Updated application status for Google - Software Engineer II
```


## 📁 Project Structure

```
JobApplicationAgent/
├── agents/                      # AI Agent implementations
│   ├── base_agent.py                # Base class for all agents
│   ├── scout_agent.py               # Job discovery from APIs
│   ├── extractor_agent.py           # Data extraction from job posts
│   ├── matcher_agent.py             # Candidate-job matching
│   ├── writer_agent.py              # Resume/cover letter generation
│   ├── tracker_agent.py             # Application tracking
│   ├── application_agent.py         # Application submission
│   ├── orchestrator_agent.py        # Multi-agent workflow coordination
│   └── browser_automation.py        # Web automation utilities
│
├── core/                        # Core business logic
│   ├── config.py                    # Configuration management
│   ├── user_profile.py              # User profile handling
│   ├── decision_engine.py           # Decision-making logic
│   ├── agent_communication.py       # Inter-agent messaging bus
│   └── conversation_state.py        # Conversation state management
│
├── graph/                       # Neo4j integration
│   ├── memory.py                    # Graph database operations
│   └── schema.py                    # Graph schema definitions
│
├── llm/                         # LLM clients and prompts
│   ├── llm_client.py                # Universal LLM interface (Groq/OpenAI)
│   ├── llama_client.py              # Ollama/local LLM integration
│   └── prompts.py                   # Prompt templates for agents
│
├── workflow/                    # LangGraph workflows
│   └── job_application_graph.py     # Main state machine workflow
│
├── utils/                       # Utility functions
│   ├── embeddings.py                # Sentence transformer embeddings
│   └── audit_logger.py              # Audit logging utilities
│
├── scripts/                     # Executable scripts
│   ├── run_autonomous.py            # Start autonomous job search
│   ├── chat_with_agent.py           # Interactive chat interface
│   ├── quick_setup.py               # Quick setup wizard
│   ├── setup_profile.py             # Detailed profile setup
│   ├── manage_profile.py            # Profile management
│   ├── run_scout.py                 # Run scout agent standalone
│   ├── run_matcher.py               # Run matcher agent standalone
│   └── run_writer.py                # Run writer agent standalone
│
├── tests/                       # Test suite
│   ├── test_scout_agent.py          # Scout agent tests
│   ├── test_matcher_agent.py        # Matcher agent tests
│   ├── test_extractor_agent.py      # Extractor agent tests
│   ├── test_agent_communication.py  # Communication bus tests
│   ├── test_conversation_state.py   # State management tests
│   ├── test_decision_engine.py      # Decision engine tests
│   ├── test_evaluation.py           # Evaluation tests
│   └── test_integration.py          # Integration tests
│
├── data/                        # Data storage
│   ├── logs/                        # Application logs
│   └── outputs/                     # Generated outputs
│
├── outputs/                     # Generated documents
│   ├── cover_letters/               # Generated cover letters
│   └── resumes/                     # Generated resumes
│
├── logs/                        # Runtime logs
│
├── config.yaml                  # Main configuration file
├── requirements.txt             # Python dependencies
├── .agent_state.json            # Persistent agent state
└── README.md                    # This file
```


## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📧 Contact

**Dhruva K** - [@Dhruva-K](https://github.com/Dhruva-K)

**Project Link**: [https://github.com/Dhruva-K/JobApplicationAgent](https://github.com/Dhruva-K/JobApplicationAgent)

---

<div align="center">

**⭐ Star this repo if you find it helpful!**


[Report Bug](https://github.com/Dhruva-K/JobApplicationAgent/issues) · [Request Feature](https://github.com/Dhruva-K/JobApplicationAgent/issues) · [Documentation](docs/)

</div>
  