# User Guide

## Getting Started

### 1. Initial Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up Neo4j**
   - Download and install Neo4j Desktop from https://neo4j.com/download/
   - Create a new database
   - Note the connection details (URI, username, password)

3. **Set Up Ollama**
   ```bash
   # Install Ollama from https://ollama.ai
   # Pull Llama 3 8B model
   ollama pull llama3:8b
   ```

4. **Configure Application**
   - Edit `config.yaml` with your Neo4j credentials
   - Add your job API keys (JSearch, Remotive) if available
   - Or set environment variables in `.env` file

### 2. Running the Application

#### Streamlit UI (Recommended)

```bash
streamlit run ui/app.py
```

The application will open in your browser at `http://localhost:8501`

#### Python API

```python
from workflow.job_application_graph import JobApplicationGraph

# Initialize
workflow = JobApplicationGraph()

# Search for jobs
jobs = workflow.search_jobs("software engineer", location="remote")
```

## Using the Streamlit UI

### Profile Management

1. Navigate to the **Profile** page
2. Fill in your information:
   - Name and Email
   - Years of Experience
   - Education Level
   - Skills (comma-separated)
3. Click **Save Profile**

### Job Search

1. Navigate to the **Job Search** page
2. Enter search criteria:
   - Keywords (e.g., "python developer")
   - Location (optional)
   - Employment Type (optional)
3. Click **Search Jobs**
4. Browse results and select jobs of interest

### Viewing Matches

1. Navigate to the **Matches** page
2. Click **Refresh Matches** to find jobs matching your profile
3. View match scores and skill analysis
4. Click **Generate Documents** for jobs you want to apply to

### Generating Documents

1. Select a job from Matches or Job Search
2. Navigate to the **Documents** page
3. Click **Generate Documents**
4. Review generated:
   - Cover Letter
   - Resume Summary
   - Resume Sections
5. Download documents as needed

### Tracking Applications

1. Navigate to the **Applications** page
2. View statistics:
   - Total Applications
   - Status Breakdown (Pending, Submitted, Interview, etc.)
   - Average Match Score
3. View recent applications and their status

## Workflow Overview

The system follows this workflow:

1. **Scout**: Searches for jobs from APIs
2. **Extractor**: Extracts skills and requirements from job descriptions
3. **Matcher**: Computes match scores based on your profile
4. **Writer**: Generates personalized documents
5. **Tracker**: Records and tracks applications

## Tips for Best Results

1. **Complete Your Profile**: The more detailed your profile, the better the matching
2. **Update Skills Regularly**: Keep your skills list current
3. **Review Generated Documents**: Always review and edit generated documents before submitting
4. **Track Applications**: Use the tracking feature to stay organized
5. **Use Specific Keywords**: More specific job search keywords yield better results

## Troubleshooting

### Neo4j Connection Issues

- Verify Neo4j is running
- Check connection details in `config.yaml`
- Ensure database exists and is accessible

### Ollama Not Responding

- Verify Ollama is running: `ollama list`
- Check if model is installed: `ollama show llama3:8b`
- Verify API URL in configuration

### No Jobs Found

- Check API keys are configured
- Try different search keywords
- Verify API service is accessible

### Document Generation Fails

- Ensure user profile is complete
- Verify job information is available
- Check LLM service is running

## Advanced Usage

### Custom Configuration

Edit `config.yaml` to customize:
- LLM temperature and max tokens
- Match score thresholds
- API endpoints
- Embedding models

### Programmatic Access

Use the Python API for automation:

```python
from workflow.job_application_graph import JobApplicationGraph

workflow = JobApplicationGraph()

# Complete workflow
result = workflow.run(
    user_id="user123",
    keywords="data scientist",
    location="remote"
)

# Individual operations
jobs = workflow.search_jobs("python developer")
matches = workflow.get_matches("user123")
documents = workflow.generate_documents("user123", "job456")
```

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Check the project README
4. Open an issue on the project repository

