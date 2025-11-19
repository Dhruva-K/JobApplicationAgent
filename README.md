# Job Application Agent with Graph-Based Memory

A LangGraph-powered multi-agent system for automating job discovery, evaluation, and application preparation using powerful LLMs (Groq, Ollama, or vLLM) and Neo4j graph database.

## Features

- **5 Specialized Agents**: Scout, Extractor, Matcher, Writer, and Tracker
- **Graph-Based Memory**: Neo4j database for relational knowledge storage
- **Flexible LLM Options**: Groq cloud API (recommended), Ollama for local inference, or vLLM
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
- One of the following LLM options:
  - **Groq API key** (recommended - fast, powerful, and free)
  - Ollama installed with a model like Llama 3 8B
  - vLLM server running
- GPU (optional, for local inference with Ollama/vLLM)

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
   - Update configuration with your Neo4j credentials (see step 5)

4. Set up your LLM provider:

   **Option A: Groq (Recommended - Fast, Powerful, Free)**
   - Sign up for a free account at [https://console.groq.com](https://console.groq.com)
   - Generate an API key from the dashboard
   - The default model `llama-3.3-70b-versatile` is the best free option available
   
   **Option B: Ollama (Local Inference)**
   ```bash
   # Install Ollama (if not already installed)
   # Visit https://ollama.ai for installation instructions
   
   # Pull Llama 3 8B model
   ollama pull llama3:8b
   ```
   
   **Option C: vLLM (High-Performance Local Inference)**
   - Set up a vLLM server following their documentation
   - Configure the base URL in your environment

5. Configure the application:
   - Copy `.env.example` to `.env`
   - Update configuration values in `.env`:
     ```bash
     # For Groq (recommended)
     LLM_PROVIDER=groq
     LLM_MODEL_NAME=llama-3.3-70b-versatile
     GROQ_API_KEY=your_api_key_here
     
     # For Ollama
     # LLM_PROVIDER=ollama
     # LLM_MODEL_NAME=llama3:8b
     
     # For vLLM
     # LLM_PROVIDER=vllm
     # LLM_MODEL_NAME=llama3-8b
     ```
   - Add your Neo4j credentials
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

Edit `.env` to customize:
- **LLM Provider**: Choose between Groq (cloud), Ollama (local), or vLLM
  - Groq: `llama-3.3-70b-versatile` (recommended - most powerful free model)
  - Ollama: `llama3:8b` or other local models
  - vLLM: Custom model deployment
- **Neo4j**: Connection settings for graph database
- **Job APIs**: Credentials for JSearch and Remotive APIs
- **Application Behavior**: Temperature, max tokens, etc.

You can also use a `config.yaml` file for additional customization.

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
- Groq for fast cloud LLM inference
- Ollama for local LLM inference
- Meta's Llama models

