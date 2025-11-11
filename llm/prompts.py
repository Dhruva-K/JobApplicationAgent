"""
Prompt templates for different agent tasks.
"""


class PromptTemplates:
    """Collection of prompt templates for agent tasks."""
    
    # Extractor Agent Prompts
    EXTRACT_JOB_INFO = """You are a job information extraction assistant. Extract structured information from the following job description.

Job Description:
{job_description}

Extract the following information in JSON format:
{{
    "title": "Job title",
    "required_skills": ["skill1", "skill2", ...],
    "preferred_skills": ["skill1", "skill2", ...],
    "experience_level": "entry/mid/senior/executive",
    "education_required": "degree level or none",
    "responsibilities": ["responsibility1", "responsibility2", ...],
    "location": "job location",
    "employment_type": "full-time/part-time/contract/remote",
    "salary_range": "salary range if mentioned",
    "company_name": "company name if mentioned"
}}

Return only valid JSON, no additional text."""

    EXTRACT_SKILLS = """Extract all technical and soft skills mentioned in the following job description. Return a JSON array of skill names.

Job Description:
{job_description}

Return format: ["skill1", "skill2", "skill3", ...]
Return only the JSON array, no additional text."""

    # Matcher Agent Prompts
    MATCH_EVALUATION = """Evaluate how well a candidate profile matches a job requirement.

Candidate Skills: {candidate_skills}
Job Required Skills: {job_skills}
Job Title: {job_title}
Job Description: {job_description}

Provide a match score from 0.0 to 1.0 and a brief explanation.
Return JSON format:
{{
    "match_score": 0.85,
    "explanation": "Brief explanation of the match",
    "matched_skills": ["skill1", "skill2", ...],
    "missing_skills": ["skill1", "skill2", ...]
}}

Return only valid JSON, no additional text."""

    # Writer Agent Prompts
    RESUME_SECTION = """Generate a tailored resume section for a job application.

Job Title: {job_title}
Job Description: {job_description}
Required Skills: {required_skills}

User Profile:
- Skills: {user_skills}
- Experience: {user_experience}
- Education: {user_education}

Generate a {section_type} section that highlights relevant skills and experience for this specific job. Make it concise, professional, and tailored to the job requirements.

Section Type: {section_type}
{specific_instructions}

Return the section content only, no additional formatting or explanations."""

    COVER_LETTER = """Write a professional cover letter for a job application.

Job Title: {job_title}
Company: {company_name}
Job Description: {job_description}
Required Skills: {required_skills}

Applicant Information:
- Name: {applicant_name}
- Skills: {user_skills}
- Experience: {user_experience}
- Education: {user_education}

Write a compelling cover letter that:
1. Expresses genuine interest in the position
2. Highlights relevant skills and experience
3. Demonstrates understanding of the role
4. Shows enthusiasm for the company
5. Includes a strong closing

Keep it professional, concise (3-4 paragraphs), and tailored to this specific job. Do not include placeholders or generic statements.

Return the complete cover letter text only."""

    RESUME_SUMMARY = """Generate a professional resume summary/objective for a job application.

Job Title: {job_title}
Job Description: {job_description}
Required Skills: {required_skills}

User Profile:
- Skills: {user_skills}
- Experience: {user_experience}
- Years of Experience: {years_experience}

Create a 2-3 sentence professional summary that highlights the candidate's most relevant qualifications for this specific position. Focus on skills and experience that match the job requirements.

Return only the summary text, no additional formatting."""

    # General Prompts
    SUMMARIZE = """Summarize the following text in a concise manner:

{text}

Provide a clear, concise summary."""

    CLASSIFY = """Classify the following text into one of these categories: {categories}

Text: {text}

Return only the category name."""

    @staticmethod
    def format_extract_job_info(job_description: str) -> str:
        """Format job information extraction prompt."""
        return PromptTemplates.EXTRACT_JOB_INFO.format(
            job_description=job_description
        )
    
    @staticmethod
    def format_extract_skills(job_description: str) -> str:
        """Format skills extraction prompt."""
        return PromptTemplates.EXTRACT_SKILLS.format(
            job_description=job_description
        )
    
    @staticmethod
    def format_match_evaluation(
        candidate_skills: list,
        job_skills: list,
        job_title: str,
        job_description: str
    ) -> str:
        """Format match evaluation prompt."""
        return PromptTemplates.MATCH_EVALUATION.format(
            candidate_skills=", ".join(candidate_skills),
            job_skills=", ".join(job_skills),
            job_title=job_title,
            job_description=job_description
        )
    
    @staticmethod
    def format_resume_section(
        job_title: str,
        job_description: str,
        required_skills: list,
        user_skills: list,
        user_experience: str,
        user_education: str,
        section_type: str,
        specific_instructions: str = ""
    ) -> str:
        """Format resume section generation prompt."""
        return PromptTemplates.RESUME_SECTION.format(
            job_title=job_title,
            job_description=job_description,
            required_skills=", ".join(required_skills),
            user_skills=", ".join(user_skills),
            user_experience=user_experience,
            user_education=user_education,
            section_type=section_type,
            specific_instructions=specific_instructions
        )
    
    @staticmethod
    def format_cover_letter(
        job_title: str,
        company_name: str,
        job_description: str,
        required_skills: list,
        applicant_name: str,
        user_skills: list,
        user_experience: str,
        user_education: str
    ) -> str:
        """Format cover letter generation prompt."""
        return PromptTemplates.COVER_LETTER.format(
            job_title=job_title,
            company_name=company_name,
            job_description=job_description,
            required_skills=", ".join(required_skills),
            applicant_name=applicant_name,
            user_skills=", ".join(user_skills),
            user_experience=user_experience,
            user_education=user_education
        )
    
    @staticmethod
    def format_resume_summary(
        job_title: str,
        job_description: str,
        required_skills: list,
        user_skills: list,
        user_experience: str,
        years_experience: int
    ) -> str:
        """Format resume summary generation prompt."""
        return PromptTemplates.RESUME_SUMMARY.format(
            job_title=job_title,
            job_description=job_description,
            required_skills=", ".join(required_skills),
            user_skills=", ".join(user_skills),
            user_experience=user_experience,
            years_experience=years_experience
        )

