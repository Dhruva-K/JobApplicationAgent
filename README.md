# Job Application Agent with Graph-Based Memory

A LangGraph-powered multi-agent system for automating job discovery, evaluation, and application preparation using Llama 3 8B and Neo4j graph database.

## Features

- **5 Specialized Agents**: Scout, Extractor, Matcher, Writer, and Tracker
- **Graph-Based Memory**: Neo4j database for relational knowledge storage
- **Open-Source LLM**: Llama 3 8B via Ollama for local inference
- **Intelligent Matching**: Skill-based and semantic similarity matching
- **Document Generation**: Automated resume and cover letter generation
- **Application Tracking**: Comprehensive tracking of job applications

## System Architecture

```
┌─────────────┐
│   Scout     │ → Retrieves job listings from APIs
└──────┬──────┘
       │
┌──────▼──────┐
│  Extractor  │ → Extracts structured info from job descriptions
└──────┬──────┘
       │
┌──────▼──────┐
│   Matcher   │ → Computes candidate-job fit scores
└──────┬──────┘
       │
┌──────▼──────┐
│   Writer    │ → Generates personalized documents
└──────┬──────┘
       │
┌──────▼──────┐
│   Tracker   │ → Tracks application status
└─────────────┘
```

## Prerequisites

- Python 3.10+
- Neo4j database (local or cloud)
- Ollama installed with Llama 3 8B model
- GPU (optional, for faster inference)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd JobApplicationAgent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Neo4j:
   - Install Neo4j Desktop or use Neo4j Aura (cloud)
   - Create a new database
   - Update `config.yaml` with your Neo4j credentials

4. Set up Ollama:
```bash
# Install Ollama (if not already installed)
# Visit https://ollama.ai for installation instructions

# Pull Llama 3 8B model
ollama pull llama3:8b
```

5. Configure the application:
   - Copy `.env.example` to `.env`
   - Update configuration values in `config.yaml` or `.env`
   - Add your job API keys (JSearch, Remotive)

## Usage

### Running the Streamlit UI

```bash
streamlit run ui/app.py
```

### Running as a Python Module

```python
from workflow.job_application_graph import JobApplicationGraph

# Initialize the workflow
workflow = JobApplicationGraph()

# Run a job search
result = workflow.search_jobs(
    keywords="software engineer",
    location="remote",
    max_results=10
)
```

## Project Structure

```
JobApplicationAgent/
├── agents/              # Agent implementations
├── graph/               # Neo4j graph memory
├── llm/                 # LLM client and prompts
├── workflow/            # LangGraph orchestration
├── core/                # Core utilities and config
├── ui/                  # Streamlit interface
├── utils/               # Helper utilities
├── tests/               # Test files
├── config.yaml          # Configuration file
└── requirements.txt     # Python dependencies
```

## Configuration

Edit `config.yaml` to customize:
- Neo4j connection settings
- LLM model and parameters
- Job API credentials
- Application behavior

## Development

### Running Tests

```bash
pytest tests/
```

### Code Structure

- **Agents**: Each agent is a self-contained module with specific responsibilities
- **Graph Memory**: Neo4j integration for persistent knowledge storage
- **Workflow**: LangGraph state machine orchestrating agent interactions
- **UI**: Streamlit-based user interface

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Acknowledgments

- LangGraph for agent orchestration
- Neo4j for graph database
- Ollama for local LLM inference
- Llama 3 8B by Meta

