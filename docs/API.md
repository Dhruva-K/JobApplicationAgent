# API Documentation

## JobApplicationGraph

Main workflow class for orchestrating job application agents.

### Methods

#### `__init__(config: Optional[Config] = None)`

Initialize the job application workflow.

**Parameters:**
- `config` (Optional[Config]): Configuration instance. Creates default if None.

**Returns:**
- `JobApplicationGraph`: Initialized workflow instance

---

#### `run(user_id: str, keywords: str, location: Optional[str] = None, employment_type: Optional[str] = None, selected_job_id: Optional[str] = None) -> Dict[str, Any]`

Run the complete workflow from job search to application tracking.

**Parameters:**
- `user_id` (str): User identifier
- `keywords` (str): Job search keywords
- `location` (Optional[str]): Optional location filter
- `employment_type` (Optional[str]): Optional employment type filter
- `selected_job_id` (Optional[str]): Optional pre-selected job ID (skips search)

**Returns:**
- `Dict[str, Any]`: Final workflow state containing jobs, matches, documents, and application info

**Example:**
```python
workflow = JobApplicationGraph()
result = workflow.run(
    user_id="user123",
    keywords="software engineer",
    location="remote"
)
```

---

#### `search_jobs(keywords: str, location: Optional[str] = None, employment_type: Optional[str] = None) -> List[Dict[str, Any]]`

Search for jobs using the Scout agent.

**Parameters:**
- `keywords` (str): Search keywords
- `location` (Optional[str]): Optional location filter
- `employment_type` (Optional[str]): Optional employment type filter

**Returns:**
- `List[Dict[str, Any]]`: List of job dictionaries

**Example:**
```python
jobs = workflow.search_jobs("python developer", location="remote")
```

---

#### `get_matches(user_id: str, job_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]`

Get job matches for a user.

**Parameters:**
- `user_id` (str): User identifier
- `job_ids` (Optional[List[str]]): Optional list of specific job IDs to match against

**Returns:**
- `List[Dict[str, Any]]`: List of matched jobs with scores

**Example:**
```python
matches = workflow.get_matches("user123", job_ids=["job1", "job2"])
```

---

#### `generate_documents(user_id: str, job_id: str) -> Dict[str, str]`

Generate documents (resume, cover letter) for a job application.

**Parameters:**
- `user_id` (str): User identifier
- `job_id` (str): Job identifier

**Returns:**
- `Dict[str, str]`: Dictionary mapping document types to generated content

**Example:**
```python
documents = workflow.generate_documents("user123", "job456")
cover_letter = documents.get("cover_letter")
```

---

## Agent Classes

### ScoutAgent

Retrieves job listings from APIs.

#### `search_jobs(keywords: str, location: Optional[str] = None, employment_type: Optional[str] = None, max_results: int = 50, api_source: str = "jsearch") -> List[Dict[str, Any]]`

Search for jobs using specified API.

---

### ExtractorAgent

Extracts structured information from job descriptions.

#### `extract_job_info(job_id: str) -> Optional[Dict[str, Any]]`

Extract structured information from a job description.

---

### MatcherAgent

Computes candidate-job fit scores.

#### `match_jobs(user_id: str, job_ids: Optional[List[str]] = None, min_score: float = 0.6, use_semantic: bool = True) -> List[Dict[str, Any]]`

Match user to jobs using skill overlap and semantic similarity.

---

### WriterAgent

Generates personalized resumes and cover letters.

#### `generate_cover_letter(user_id: str, job_id: str, applicant_name: Optional[str] = None) -> Optional[str]`

Generate a personalized cover letter.

#### `generate_resume_section(user_id: str, job_id: str, section_type: str, specific_instructions: str = "") -> Optional[str]`

Generate a tailored resume section.

---

### TrackerAgent

Tracks application status and maintains history.

#### `create_application(user_id: str, job_id: str, match_score: Optional[float] = None, initial_status: ApplicationStatus = ApplicationStatus.PENDING) -> Optional[str]`

Create a new application record.

#### `get_user_applications(user_id: str, status_filter: Optional[ApplicationStatus] = None) -> List[Dict[str, Any]]`

Get all applications for a user.

---

## GraphMemory

Neo4j graph database operations.

### Node Operations

- `create_job(job_data: Dict[str, Any]) -> str`
- `create_company(company_data: Dict[str, Any]) -> str`
- `create_skill(skill_data: Dict[str, Any]) -> str`
- `create_user(user_data: Dict[str, Any]) -> str`
- `create_application(application_data: Dict[str, Any]) -> str`

### Relationship Operations

- `link_job_to_company(job_id: str, company_id: str)`
- `link_job_to_skill(job_id: str, skill_id: str, required_level: str = "intermediate", is_mandatory: bool = True)`
- `link_user_to_skill(user_id: str, skill_id: str)`
- `link_application(user_id: str, job_id: str, application_id: str)`

### Query Operations

- `get_job(job_id: str) -> Optional[Dict[str, Any]]`
- `search_jobs(filters: Optional[Dict[str, Any]] = None, limit: int = 50) -> List[Dict[str, Any]]`
- `get_user_skills(user_id: str) -> List[Dict[str, Any]]`
- `get_job_skills(job_id: str) -> List[Dict[str, Any]]`
- `get_user_applications(user_id: str) -> List[Dict[str, Any]]`
- `get_user_matches(user_id: str, min_score: float = 0.0, limit: int = 20) -> List[Dict[str, Any]]`

