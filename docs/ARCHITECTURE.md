# System Architecture

## Overview

The Job Application Agent is a multi-agent system built with LangGraph that automates job discovery, evaluation, and application preparation. It uses Neo4j for graph-based memory and Llama 3 8B for local LLM inference.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI                          │
│              (User Interface Layer)                      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              LangGraph Workflow                          │
│         (Orchestration Layer)                           │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼───┐  ┌─────▼─────┐  ┌───▼────────┐
│   Scout   │  │ Extractor │  │  Matcher   │
└───────┬───┘  └─────┬─────┘  └───┬────────┘
        │            │            │
        │      ┌─────▼─────┐      │
        │      │   Writer  │      │
        │      └─────┬─────┘      │
        │            │            │
        └────────────┼────────────┘
                     │
            ┌────────▼────────┐
            │    Tracker      │
            └────────┬────────┘
                     │
        ┌────────────┼────────────┐
        │                         │
┌───────▼──────┐        ┌────────▼──────┐
│   Neo4j      │        │  Ollama/LLM   │
│  Graph DB    │        │   (Llama 3)   │
└──────────────┘        └───────────────┘
```

## Component Details

### 1. LangGraph Workflow

The central orchestration layer that manages the state machine and coordinates agent interactions.

**Key Responsibilities:**
- State management
- Agent coordination
- Workflow execution
- Error handling

**State Schema:**
```python
{
    "user_id": str,
    "keywords": str,
    "jobs": List[Dict],
    "extracted_data": Dict,
    "matches": List[Dict],
    "documents": Dict,
    "application_id": str
}
```

### 2. Agents

#### Scout Agent
- **Purpose**: Job discovery
- **Input**: Search keywords, filters
- **Output**: List of job listings
- **Dependencies**: Job APIs (JSearch, Remotive)

#### Extractor Agent
- **Purpose**: Information extraction
- **Input**: Job descriptions
- **Output**: Structured data (skills, requirements)
- **Dependencies**: LLM (Llama 3 8B)

#### Matcher Agent
- **Purpose**: Candidate-job matching
- **Input**: User profile, job requirements
- **Output**: Match scores and recommendations
- **Dependencies**: LLM, Embeddings

#### Writer Agent
- **Purpose**: Document generation
- **Input**: User profile, job details
- **Output**: Resumes, cover letters
- **Dependencies**: LLM (Llama 3 8B)

#### Tracker Agent
- **Purpose**: Application tracking
- **Input**: Application data
- **Output**: Application records, statistics
- **Dependencies**: Neo4j

### 3. Graph Memory (Neo4j)

Stores relational knowledge about:
- Jobs and companies
- Skills and requirements
- User profiles
- Applications and matches

**Node Types:**
- Job
- Company
- Skill
- User
- Application

**Relationship Types:**
- REQUIRES_SKILL
- APPLIED_TO
- HAS_SKILL
- MATCHES
- POSTED_BY

### 4. LLM Integration

**Ollama Client:**
- Local inference with Llama 3 8B
- JSON generation for structured extraction
- Prompt-based document generation

**Embeddings:**
- SentenceTransformers for semantic similarity
- Skill matching
- Document relevance

## Data Flow

### Job Search Workflow

1. User submits search query
2. Scout Agent queries job APIs
3. Jobs stored in Neo4j
4. Extractor Agent processes job descriptions
5. Skills extracted and linked in graph
6. Matcher Agent computes match scores
7. Results presented to user

### Application Workflow

1. User selects a job
2. Writer Agent generates documents
3. Documents reviewed by user
4. Tracker Agent creates application record
5. Status tracked in graph database

## Design Patterns

### Agent Pattern
Each agent is a self-contained module with:
- Single responsibility
- Clear input/output interface
- Independent operation capability

### State Machine Pattern
LangGraph implements a state machine with:
- Defined states
- Transitions between states
- Conditional routing

### Repository Pattern
GraphMemory acts as a repository for:
- Data persistence
- Query abstraction
- Relationship management

## Scalability Considerations

1. **Horizontal Scaling**: Agents can run independently
2. **Caching**: Job listings and embeddings cached
3. **Batch Processing**: Multiple jobs processed in parallel
4. **Async Operations**: LLM calls can be async

## Security Considerations

1. **API Keys**: Stored in environment variables
2. **Data Privacy**: User data stored locally
3. **Input Validation**: All inputs validated
4. **Error Handling**: Graceful error handling throughout

## Future Enhancements

1. **Vector Store**: ChromaDB for semantic search
2. **Multi-User Support**: User authentication and isolation
3. **API Layer**: REST API for programmatic access
4. **Analytics**: Advanced matching analytics
5. **Notifications**: Application status notifications

