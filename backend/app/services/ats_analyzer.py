"""
ATS (Applicant Tracking System) Keyword Analyzer Service.

Provides algorithmic analysis of resumes against job descriptions without requiring LLM calls.
Optionally integrates with LLM service for enhanced suggestions.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ATSResult:
    """Result of ATS analysis."""

    overall_score: int
    keyword_match_score: int
    formatting_score: int
    section_scores: Dict[str, int]
    missing_keywords: List[str]
    matched_keywords: List[str]
    suggestions: List[str]
    experience_match: Dict[str, any]
    keyword_breakdown: Dict[str, List[str]]


@dataclass
class KeywordSuggestion:
    """Suggestion for adding a keyword to resume."""

    keyword: str
    category: str
    priority: str  # high, medium, low
    suggestion: str
    section_recommendation: str


# =============================================================================
# COMPREHENSIVE KEYWORD LISTS
# =============================================================================

# 200+ Technical Skills
TECHNICAL_SKILLS: List[str] = [
    # Programming Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go",
    "golang", "rust", "swift", "kotlin", "scala", "php", "perl", "r",
    "matlab", "julia", "haskell", "erlang", "elixir", "clojure", "groovy",
    "objective-c", "dart", "lua", "shell", "bash", "powershell", "vba",
    # Frontend Frameworks/Libraries
    "react", "reactjs", "react.js", "angular", "angularjs", "vue", "vuejs",
    "vue.js", "svelte", "nextjs", "next.js", "nuxtjs", "nuxt.js", "gatsby",
    "ember", "backbone", "jquery", "bootstrap", "tailwind", "tailwindcss",
    "material-ui", "chakra-ui", "styled-components", "sass", "scss", "less",
    "webpack", "vite", "parcel", "rollup", "esbuild",
    # Backend Frameworks
    "node", "nodejs", "node.js", "express", "expressjs", "fastapi", "django",
    "flask", "spring", "springboot", "spring boot", "rails", "ruby on rails",
    "laravel", "symfony", "asp.net", ".net", "dotnet", "gin", "fiber",
    "fastify", "nestjs", "koa", "hapi",
    # Databases
    "sql", "mysql", "postgresql", "postgres", "mongodb", "redis", "cassandra",
    "dynamodb", "couchdb", "neo4j", "elasticsearch", "sqlite", "oracle",
    "mariadb", "mssql", "sql server", "firebase", "firestore", "supabase",
    "timescaledb", "influxdb", "clickhouse", "cockroachdb",
    # Cloud Platforms
    "aws", "amazon web services", "azure", "microsoft azure", "gcp",
    "google cloud", "google cloud platform", "heroku", "digitalocean",
    "vercel", "netlify", "cloudflare", "linode", "vultr",
    # AWS Services
    "ec2", "s3", "lambda", "rds", "dynamodb", "cloudfront", "cloudwatch",
    "sns", "sqs", "kinesis", "ecs", "eks", "fargate", "api gateway",
    "cloudformation", "cdk", "sam", "step functions", "cognito", "iam",
    # DevOps/Infrastructure
    "docker", "kubernetes", "k8s", "terraform", "ansible", "puppet", "chef",
    "vagrant", "jenkins", "gitlab ci", "github actions", "circleci",
    "travis ci", "bamboo", "argo cd", "flux", "helm", "istio", "envoy",
    "prometheus", "grafana", "datadog", "splunk", "elk", "logstash", "kibana",
    "new relic", "pagerduty", "opsgenie",
    # Version Control
    "git", "github", "gitlab", "bitbucket", "svn", "mercurial",
    # APIs and Protocols
    "rest", "restful", "api", "graphql", "grpc", "soap", "websocket",
    "webhooks", "oauth", "oauth2", "jwt", "openapi", "swagger",
    # Data Engineering
    "spark", "apache spark", "hadoop", "hive", "airflow", "apache airflow",
    "kafka", "apache kafka", "flink", "apache flink", "beam", "nifi",
    "databricks", "snowflake", "redshift", "bigquery", "dbt", "presto",
    "trino", "etl", "elt", "data pipeline", "data warehouse", "data lake",
    # Machine Learning / AI
    "machine learning", "ml", "deep learning", "dl", "tensorflow", "pytorch",
    "keras", "scikit-learn", "sklearn", "pandas", "numpy", "scipy",
    "matplotlib", "seaborn", "plotly", "jupyter", "nlp",
    "natural language processing", "computer vision", "cv", "opencv",
    "hugging face", "transformers", "bert", "gpt", "llm", "langchain",
    "rag", "vector database", "pinecone", "weaviate", "milvus", "qdrant",
    # Mobile Development
    "ios", "android", "react native", "flutter", "xamarin", "ionic",
    "cordova", "swiftui", "uikit", "jetpack compose",
    # Testing
    "unit testing", "integration testing", "e2e testing", "jest", "mocha",
    "chai", "pytest", "unittest", "junit", "testng", "selenium", "cypress",
    "playwright", "puppeteer", "postman", "tdd", "bdd", "cucumber",
    # Security
    "security", "cybersecurity", "penetration testing", "owasp", "sast",
    "dast", "encryption", "ssl", "tls", "https", "firewall", "vpn",
    "sso", "saml", "ldap", "active directory", "kerberos",
    # Architecture/Design
    "microservices", "monolith", "serverless", "event-driven", "soa",
    "domain-driven design", "ddd", "cqrs", "event sourcing", "saga pattern",
    "api gateway", "service mesh", "load balancing",
    # Methodologies
    "agile", "scrum", "kanban", "lean", "xp", "extreme programming",
    "waterfall", "sdlc", "ci/cd", "cicd", "continuous integration",
    "continuous deployment", "continuous delivery", "devops", "devsecops",
    "gitops", "infrastructure as code", "iac",
    # Other Tools
    "jira", "confluence", "trello", "asana", "slack", "teams", "notion",
    "figma", "sketch", "adobe xd", "invision", "zeplin", "storybook",
    "chromatic", "percy", "visual regression",
]

# 50+ Soft Skills
SOFT_SKILLS: List[str] = [
    "leadership", "communication", "collaboration", "teamwork", "team player",
    "problem-solving", "problem solving", "critical thinking", "analytical",
    "creativity", "creative", "innovation", "innovative", "adaptability",
    "adaptable", "flexibility", "flexible", "time management", "organization",
    "organized", "detail-oriented", "attention to detail", "self-motivated",
    "self-starter", "initiative", "proactive", "accountability", "responsible",
    "reliability", "reliable", "dependable", "interpersonal", "emotional intelligence",
    "empathy", "conflict resolution", "negotiation", "persuasion", "influence",
    "presentation", "public speaking", "written communication", "verbal communication",
    "active listening", "customer service", "client relations", "stakeholder management",
    "decision making", "strategic thinking", "strategic planning", "mentoring",
    "coaching", "training", "facilitation", "cross-functional", "multitasking",
    "prioritization", "deadline-driven", "results-oriented", "goal-oriented",
    "work ethic", "integrity", "professionalism", "positive attitude", "resilience",
    "stress management", "patience", "cultural awareness", "diversity", "inclusion",
]

# Common Certifications
CERTIFICATIONS: List[str] = [
    # Cloud Certifications
    "aws certified", "aws solutions architect", "aws developer", "aws sysops",
    "aws devops engineer", "aws security specialty", "aws data analytics",
    "aws machine learning", "azure certified", "azure administrator",
    "azure developer", "azure solutions architect", "azure security engineer",
    "azure data engineer", "azure ai engineer", "gcp certified",
    "google cloud architect", "google cloud developer", "google cloud engineer",
    # Project Management
    "pmp", "project management professional", "capm", "prince2", "scrum master",
    "csm", "certified scrum master", "psm", "professional scrum master",
    "safe", "safe agilist", "pmi-acp", "agile certified practitioner",
    # IT/Security
    "cissp", "cism", "cisa", "ceh", "certified ethical hacker",
    "comptia security+", "comptia network+", "comptia a+", "ccna", "ccnp",
    "ccie", "oscp", "itil", "cobit",
    # Data/Analytics
    "cdmp", "certified data management professional", "google data analytics",
    "microsoft certified data analyst", "tableau certified", "power bi certified",
    "snowflake certification", "databricks certified",
    # Development
    "oracle certified", "java certified", "microsoft certified developer",
    "certified kubernetes administrator", "cka", "ckad", "cks",
    "terraform certified", "hashicorp certified", "docker certified",
    # Other
    "six sigma", "lean six sigma", "green belt", "black belt",
]

# Education Keywords
EDUCATION_KEYWORDS: List[str] = [
    # Degrees
    "bachelor", "bachelors", "bachelor's", "bs", "ba", "b.s.", "b.a.",
    "master", "masters", "master's", "ms", "ma", "m.s.", "m.a.", "mba", "m.b.a.",
    "phd", "ph.d.", "doctorate", "doctoral", "associate", "associates",
    "associate's", "diploma", "certificate", "certification",
    # Fields of Study
    "computer science", "software engineering", "information technology",
    "information systems", "data science", "computer engineering",
    "electrical engineering", "mathematics", "statistics", "physics",
    "business administration", "economics", "finance", "accounting",
    "marketing", "communications", "psychology", "engineering",
    # Academic Terms
    "gpa", "cum laude", "magna cum laude", "summa cum laude", "honors",
    "dean's list", "graduate", "undergraduate", "coursework", "thesis",
    "dissertation", "research", "academic", "scholarship",
]

# Action Verbs for Resume
ACTION_VERBS: List[str] = [
    # Leadership
    "led", "managed", "directed", "supervised", "coordinated", "oversaw",
    "administered", "chaired", "headed", "orchestrated", "spearheaded",
    # Achievement
    "achieved", "accomplished", "attained", "exceeded", "surpassed", "earned",
    "awarded", "recognized", "promoted", "selected",
    # Creation/Development
    "created", "developed", "designed", "built", "established", "founded",
    "implemented", "launched", "initiated", "pioneered", "introduced",
    "architected", "engineered", "constructed", "formulated",
    # Improvement
    "improved", "enhanced", "optimized", "streamlined", "upgraded",
    "modernized", "transformed", "revamped", "refined", "restructured",
    "consolidated", "strengthened", "accelerated",
    # Analysis
    "analyzed", "evaluated", "assessed", "researched", "investigated",
    "examined", "audited", "diagnosed", "identified", "discovered",
    # Communication
    "presented", "communicated", "negotiated", "persuaded", "collaborated",
    "partnered", "liaised", "advocated", "represented", "facilitated",
    # Problem Solving
    "resolved", "solved", "troubleshot", "debugged", "fixed", "addressed",
    "mitigated", "prevented", "remediated",
    # Growth/Results
    "increased", "grew", "expanded", "scaled", "generated", "drove",
    "boosted", "maximized", "delivered", "produced", "reduced", "decreased",
    "cut", "saved", "eliminated", "minimized",
    # Technical
    "automated", "integrated", "migrated", "deployed", "configured",
    "customized", "programmed", "coded", "tested", "validated", "documented",
]

# Experience Level Patterns
EXPERIENCE_PATTERNS: List[Tuple[str, str]] = [
    (r"(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)", "years"),
    (r"(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)", "range"),
    (r"(?:over|more than|at least|minimum)\s+(\d+)\s*(?:years?|yrs?)", "minimum"),
    (r"(\d+)\+\s*(?:years?|yrs?)", "minimum"),
    (r"(?:entry[- ]?level|junior|associate)", "entry"),
    (r"(?:mid[- ]?level|intermediate)", "mid"),
    (r"(?:senior|sr\.?|lead|principal|staff)", "senior"),
    (r"(?:director|vp|vice president|head of|chief)", "executive"),
    (r"(?:intern|internship|trainee|apprentice)", "intern"),
]


class ATSAnalyzer:
    """
    Comprehensive ATS (Applicant Tracking System) Keyword Analyzer.

    Provides algorithmic analysis of resumes against job descriptions
    without requiring LLM calls. Can optionally use LLM for enhanced suggestions.
    """

    def __init__(self, use_llm: bool = False):
        """
        Initialize the ATS Analyzer.

        Args:
            use_llm: Whether to use LLM for enhanced suggestions (default False)
        """
        self.use_llm = use_llm
        self._llm_service = None

    def _get_llm_service(self):
        """Lazy load LLM service if needed."""
        if self._llm_service is None and self.use_llm:
            try:
                from app.services.llm_service import get_llm_service
                self._llm_service = get_llm_service()
            except Exception:
                self.use_llm = False
        return self._llm_service

    def extract_keywords(self, text: str) -> Dict[str, List[str]]:
        """
        Extract keywords from text, categorized by type.

        Args:
            text: The text to analyze (typically a job description)

        Returns:
            Dictionary with categorized keywords:
            - technical_skills: Programming languages, frameworks, tools
            - soft_skills: Interpersonal and professional skills
            - tools: Software tools and platforms
            - certifications: Professional certifications
            - education: Educational requirements
            - experience_years: Experience level requirements
        """
        text_lower = text.lower()
        words_in_text = set(re.findall(r'\b[\w.#+/-]+\b', text_lower))

        result = {
            "technical_skills": [],
            "soft_skills": [],
            "tools": [],
            "certifications": [],
            "education": [],
            "experience_years": [],
        }

        # Extract technical skills
        for skill in TECHNICAL_SKILLS:
            skill_lower = skill.lower()
            if self._keyword_in_text(skill_lower, text_lower):
                result["technical_skills"].append(skill)

        # Extract soft skills
        for skill in SOFT_SKILLS:
            skill_lower = skill.lower()
            if self._keyword_in_text(skill_lower, text_lower):
                result["soft_skills"].append(skill)

        # Extract certifications
        for cert in CERTIFICATIONS:
            cert_lower = cert.lower()
            if self._keyword_in_text(cert_lower, text_lower):
                result["certifications"].append(cert)

        # Extract education keywords
        for edu in EDUCATION_KEYWORDS:
            edu_lower = edu.lower()
            if self._keyword_in_text(edu_lower, text_lower):
                result["education"].append(edu)

        # Extract experience years
        experience_info = self._extract_experience_requirements(text)
        if experience_info:
            result["experience_years"] = experience_info

        # Deduplicate while preserving order
        for key in result:
            if isinstance(result[key], list):
                seen = set()
                unique = []
                for item in result[key]:
                    item_lower = item.lower() if isinstance(item, str) else str(item)
                    if item_lower not in seen:
                        seen.add(item_lower)
                        unique.append(item)
                result[key] = unique

        return result

    def _keyword_in_text(self, keyword: str, text: str) -> bool:
        """Check if a keyword exists in text using word boundary matching."""
        # Handle special characters in keywords
        escaped = re.escape(keyword)
        pattern = rf'\b{escaped}\b'
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _extract_experience_requirements(self, text: str) -> List[Dict[str, any]]:
        """Extract experience requirements from text."""
        results = []
        text_lower = text.lower()

        for pattern, pattern_type in EXPERIENCE_PATTERNS:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                if pattern_type == "years":
                    results.append({
                        "type": "years",
                        "value": int(match.group(1)),
                        "text": match.group(0),
                    })
                elif pattern_type == "range":
                    results.append({
                        "type": "range",
                        "min": int(match.group(1)),
                        "max": int(match.group(2)),
                        "text": match.group(0),
                    })
                elif pattern_type == "minimum":
                    results.append({
                        "type": "minimum",
                        "value": int(match.group(1)),
                        "text": match.group(0),
                    })
                else:
                    results.append({
                        "type": "level",
                        "level": pattern_type,
                        "text": match.group(0),
                    })

        return results

    def analyze_resume(self, resume: str, job_description: str) -> ATSResult:
        """
        Perform full ATS analysis of resume against job description.

        Args:
            resume: The resume content
            job_description: The job description to match against

        Returns:
            ATSResult with comprehensive analysis including scores and suggestions
        """
        resume_lower = resume.lower()
        jd_lower = job_description.lower()

        # Extract keywords from both
        jd_keywords = self.extract_keywords(job_description)
        resume_keywords = self.extract_keywords(resume)

        # Calculate section scores
        section_scores = self._calculate_section_scores(resume_lower, jd_lower)

        # Calculate keyword match score
        keyword_match_score, matched, missing = self._calculate_keyword_match(
            resume_keywords, jd_keywords
        )

        # Calculate formatting score
        formatting_score = self._calculate_formatting_score(resume_lower)

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            keyword_match_score, formatting_score, section_scores
        )

        # Get experience match
        experience_match = self.calculate_experience_match(resume, job_description)

        # Generate suggestions
        suggestions = self._generate_suggestions(
            section_scores, keyword_match_score, formatting_score, missing, experience_match
        )

        # Create keyword breakdown
        keyword_breakdown = {
            "technical_skills_found": resume_keywords["technical_skills"],
            "soft_skills_found": resume_keywords["soft_skills"],
            "certifications_found": resume_keywords["certifications"],
            "action_verbs_found": self._find_action_verbs(resume_lower),
        }

        return ATSResult(
            overall_score=overall_score,
            keyword_match_score=keyword_match_score,
            formatting_score=formatting_score,
            section_scores=section_scores,
            missing_keywords=missing,
            matched_keywords=matched,
            suggestions=suggestions,
            experience_match=experience_match,
            keyword_breakdown=keyword_breakdown,
        )

    def _calculate_section_scores(
        self, resume: str, job_description: str
    ) -> Dict[str, int]:
        """Calculate scores for different resume sections."""
        scores = {}

        # Standard sections check (0-20 points)
        standard_sections = [
            "experience", "education", "skills", "summary", "objective",
            "projects", "certifications", "achievements", "work history"
        ]
        sections_found = sum(1 for s in standard_sections if s in resume)
        scores["sections"] = min(sections_found * 4, 20)

        # Technical skills match (0-25 points)
        jd_tech = set(s.lower() for s in self.extract_keywords(job_description)["technical_skills"])
        resume_tech = set(s.lower() for s in self.extract_keywords(resume)["technical_skills"])
        if jd_tech:
            tech_match = len(jd_tech & resume_tech) / len(jd_tech)
            scores["technical_skills"] = int(tech_match * 25)
        else:
            scores["technical_skills"] = 15 if resume_tech else 0

        # Soft skills match (0-15 points)
        jd_soft = set(s.lower() for s in self.extract_keywords(job_description)["soft_skills"])
        resume_soft = set(s.lower() for s in self.extract_keywords(resume)["soft_skills"])
        if jd_soft:
            soft_match = len(jd_soft & resume_soft) / len(jd_soft)
            scores["soft_skills"] = int(soft_match * 15)
        else:
            scores["soft_skills"] = 10 if resume_soft else 0

        # Action verbs (0-15 points)
        action_verbs_found = len(self._find_action_verbs(resume))
        scores["action_verbs"] = min(action_verbs_found * 2, 15)

        # Quantifiable results (0-15 points)
        numbers = len(re.findall(r'\d+%|\$\d+|\d+\+', resume))
        metrics = len(re.findall(r'\b\d+[kKmMbB]\b', resume))
        scores["quantifiable_results"] = min((numbers + metrics) * 2, 15)

        # Length appropriateness (0-10 points)
        word_count = len(resume.split())
        if 400 <= word_count <= 800:
            scores["length"] = 10
        elif 300 <= word_count <= 1000:
            scores["length"] = 7
        else:
            scores["length"] = 4

        return scores

    def _calculate_keyword_match(
        self,
        resume_keywords: Dict[str, List[str]],
        jd_keywords: Dict[str, List[str]],
    ) -> Tuple[int, List[str], List[str]]:
        """Calculate keyword match score and find matched/missing keywords."""
        matched = []
        missing = []

        # Combine all keywords for comparison
        jd_all = set()
        resume_all = set()

        for key in ["technical_skills", "soft_skills", "certifications"]:
            jd_all.update(k.lower() for k in jd_keywords.get(key, []))
            resume_all.update(k.lower() for k in resume_keywords.get(key, []))

        matched = sorted(list(jd_all & resume_all))
        missing = sorted(list(jd_all - resume_all))

        if jd_all:
            score = int((len(matched) / len(jd_all)) * 100)
        else:
            score = 50  # Default score when no keywords in JD

        return min(score, 100), matched, missing

    def _calculate_formatting_score(self, resume: str) -> int:
        """Calculate score based on resume formatting."""
        score = 0

        # Check for clear section headers
        section_patterns = [
            r'(?:^|\n)\s*(experience|work history|employment)',
            r'(?:^|\n)\s*(education|academic)',
            r'(?:^|\n)\s*(skills|technical skills|core competencies)',
            r'(?:^|\n)\s*(summary|profile|objective)',
        ]
        for pattern in section_patterns:
            if re.search(pattern, resume, re.IGNORECASE):
                score += 10

        # Check for consistent formatting (bullet points or dashes)
        if re.search(r'[*\-\u2022]\s+\w', resume):
            score += 15

        # Check for contact information
        if re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', resume):
            score += 10
        if re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume):
            score += 5

        # Penalize for excessive special characters (might break ATS)
        special_chars = len(re.findall(r'[^\w\s@.+#-]', resume))
        word_count = len(resume.split())
        if word_count > 0 and (special_chars / word_count) > 0.1:
            score -= 10

        return max(min(score, 100), 0)

    def _calculate_overall_score(
        self,
        keyword_score: int,
        formatting_score: int,
        section_scores: Dict[str, int],
    ) -> int:
        """Calculate overall ATS score."""
        # Weighted average
        section_total = sum(section_scores.values())
        max_section = 100  # Maximum possible from sections

        # Weights: keywords 40%, sections 40%, formatting 20%
        weighted = (
            (keyword_score * 0.4) +
            ((section_total / max_section * 100) * 0.4) +
            (formatting_score * 0.2)
        )

        return min(int(weighted), 100)

    def _find_action_verbs(self, text: str) -> List[str]:
        """Find action verbs used in text."""
        found = []
        for verb in ACTION_VERBS:
            if self._keyword_in_text(verb, text):
                found.append(verb)
        return found

    def get_missing_keywords(self, resume: str, job_description: str) -> List[str]:
        """
        Get keywords present in job description but missing from resume.

        Args:
            resume: The resume content
            job_description: The job description

        Returns:
            List of missing keywords, sorted by importance
        """
        jd_keywords = self.extract_keywords(job_description)
        resume_keywords = self.extract_keywords(resume)

        missing = []

        # Check technical skills (highest priority)
        for skill in jd_keywords["technical_skills"]:
            if skill.lower() not in [s.lower() for s in resume_keywords["technical_skills"]]:
                missing.append(skill)

        # Check certifications
        for cert in jd_keywords["certifications"]:
            if cert.lower() not in [c.lower() for c in resume_keywords["certifications"]]:
                missing.append(cert)

        # Check soft skills
        for skill in jd_keywords["soft_skills"]:
            if skill.lower() not in [s.lower() for s in resume_keywords["soft_skills"]]:
                missing.append(skill)

        return missing

    def get_keyword_suggestions(
        self, missing_keywords: List[str]
    ) -> List[KeywordSuggestion]:
        """
        Generate suggestions for how to add missing keywords to resume.

        Args:
            missing_keywords: List of keywords missing from resume

        Returns:
            List of KeywordSuggestion objects with actionable advice
        """
        suggestions = []

        for keyword in missing_keywords[:15]:  # Limit to top 15
            keyword_lower = keyword.lower()

            # Determine category and priority
            category = "general"
            priority = "medium"
            section = "Skills"
            suggestion = f"Add '{keyword}' to your resume"

            # Technical skills
            if keyword_lower in [s.lower() for s in TECHNICAL_SKILLS]:
                category = "technical_skill"
                priority = "high"
                section = "Skills or Technical Skills"
                suggestion = (
                    f"Add '{keyword}' to your Skills section. If you have experience "
                    f"with {keyword}, also mention it in relevant work experience bullets."
                )

            # Soft skills
            elif keyword_lower in [s.lower() for s in SOFT_SKILLS]:
                category = "soft_skill"
                priority = "medium"
                section = "Experience or Summary"
                suggestion = (
                    f"Demonstrate '{keyword}' through your achievements. Instead of "
                    f"just listing it, show how you applied this skill in your work. "
                    f"Example: 'Led cross-functional team...' shows leadership."
                )

            # Certifications
            elif keyword_lower in [c.lower() for c in CERTIFICATIONS]:
                category = "certification"
                priority = "high"
                section = "Certifications or Education"
                suggestion = (
                    f"If you have '{keyword}', add it to a Certifications section. "
                    f"If not, consider pursuing this certification as it's valued "
                    f"for this role."
                )

            # Education
            elif keyword_lower in [e.lower() for e in EDUCATION_KEYWORDS]:
                category = "education"
                priority = "medium"
                section = "Education"
                suggestion = (
                    f"Ensure your Education section clearly shows '{keyword}'. "
                    f"Include relevant coursework if applicable."
                )

            suggestions.append(KeywordSuggestion(
                keyword=keyword,
                category=category,
                priority=priority,
                suggestion=suggestion,
                section_recommendation=section,
            ))

        return suggestions

    def calculate_experience_match(
        self, resume: str, job_description: str
    ) -> Dict[str, any]:
        """
        Calculate how well resume experience matches job requirements.

        Args:
            resume: The resume content
            job_description: The job description

        Returns:
            Dictionary with experience match details
        """
        # Extract experience from job description
        jd_experience = self._extract_experience_requirements(job_description)

        # Extract experience from resume
        resume_experience = self._extract_years_from_resume(resume)

        result = {
            "job_requires": jd_experience,
            "resume_shows": resume_experience,
            "match_level": "unknown",
            "recommendation": "",
        }

        # Determine required years from JD
        required_years = None
        required_level = None

        for exp in jd_experience:
            if exp["type"] == "years":
                required_years = exp["value"]
            elif exp["type"] == "minimum":
                required_years = exp["value"]
            elif exp["type"] == "range":
                required_years = exp["min"]
            elif exp["type"] == "level":
                required_level = exp["level"]

        # Compare with resume
        if resume_experience.get("total_years"):
            resume_years = resume_experience["total_years"]

            if required_years:
                if resume_years >= required_years:
                    result["match_level"] = "strong"
                    result["recommendation"] = (
                        f"Your {resume_years}+ years of experience meets or exceeds "
                        f"the {required_years} years required."
                    )
                elif resume_years >= required_years * 0.7:
                    result["match_level"] = "moderate"
                    result["recommendation"] = (
                        f"Your experience ({resume_years} years) is slightly below "
                        f"the requirement ({required_years} years). Emphasize the "
                        f"depth and relevance of your experience."
                    )
                else:
                    result["match_level"] = "weak"
                    result["recommendation"] = (
                        f"The role requires {required_years} years, and you show "
                        f"{resume_years} years. Focus on transferable skills and "
                        f"achievements to compensate."
                    )
        elif required_level:
            result["match_level"] = "needs_review"
            result["recommendation"] = (
                f"This appears to be a {required_level}-level position. Ensure "
                f"your resume clearly shows relevant experience for this level."
            )
        else:
            result["match_level"] = "undetermined"
            result["recommendation"] = (
                "Unable to determine experience requirements. Ensure your resume "
                "clearly states years of experience in relevant fields."
            )

        return result

    def _extract_years_from_resume(self, resume: str) -> Dict[str, any]:
        """Extract years of experience mentioned in resume."""
        result = {
            "total_years": None,
            "by_skill": {},
            "positions": [],
        }

        # Look for explicit years of experience statements
        patterns = [
            r'(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)',
            r'(?:over|more than)\s+(\d+)\s*(?:years?|yrs?)',
        ]

        max_years = 0
        for pattern in patterns:
            matches = re.findall(pattern, resume.lower())
            for match in matches:
                years = int(match) if isinstance(match, str) else int(match[0])
                max_years = max(max_years, years)

        if max_years > 0:
            result["total_years"] = max_years

        # Try to extract from date ranges (e.g., "2018 - 2023")
        date_pattern = r'(20\d{2})\s*[-\u2013]\s*(20\d{2}|present|current)'
        date_matches = re.findall(date_pattern, resume.lower())

        for start, end in date_matches:
            start_year = int(start)
            end_year = 2024 if end in ["present", "current"] else int(end)
            result["positions"].append({
                "start": start_year,
                "end": end_year,
                "duration": end_year - start_year,
            })

        # Calculate total from positions if not explicitly stated
        if not result["total_years"] and result["positions"]:
            total_from_positions = sum(p["duration"] for p in result["positions"])
            result["total_years"] = total_from_positions

        return result

    def _generate_suggestions(
        self,
        section_scores: Dict[str, int],
        keyword_score: int,
        formatting_score: int,
        missing_keywords: List[str],
        experience_match: Dict[str, any],
    ) -> List[str]:
        """Generate actionable improvement suggestions."""
        suggestions = []

        # Section-based suggestions
        if section_scores.get("sections", 0) < 12:
            suggestions.append(
                "Add clear section headers (Experience, Education, Skills, Summary) "
                "to improve ATS readability."
            )

        if section_scores.get("technical_skills", 0) < 15:
            suggestions.append(
                "Include more technical skills from the job description. "
                "Create a dedicated 'Technical Skills' or 'Core Competencies' section."
            )

        if section_scores.get("action_verbs", 0) < 10:
            suggestions.append(
                "Start bullet points with strong action verbs like 'Led', 'Developed', "
                "'Implemented', 'Achieved', 'Optimized', 'Delivered'."
            )

        if section_scores.get("quantifiable_results", 0) < 10:
            suggestions.append(
                "Add quantifiable achievements with numbers, percentages, and metrics. "
                "Example: 'Increased efficiency by 25%' or 'Managed $1M budget'."
            )

        if section_scores.get("length", 0) < 7:
            word_count = section_scores.get("length", 0)
            if word_count < 400:
                suggestions.append(
                    "Your resume appears short. Aim for 400-800 words with detailed "
                    "achievements and responsibilities."
                )
            else:
                suggestions.append(
                    "Your resume may be too long. Aim for 400-800 words by focusing "
                    "on the most relevant experience."
                )

        # Keyword suggestions
        if keyword_score < 50 and missing_keywords:
            top_missing = missing_keywords[:5]
            suggestions.append(
                f"Add these key missing skills: {', '.join(top_missing)}. "
                f"These appear in the job description but not your resume."
            )

        # Formatting suggestions
        if formatting_score < 50:
            suggestions.append(
                "Improve formatting for ATS compatibility: use standard section headers, "
                "bullet points, and avoid tables, graphics, or unusual characters."
            )

        # Experience match suggestions
        if experience_match.get("match_level") == "weak":
            suggestions.append(experience_match.get("recommendation", ""))

        # Add positive feedback if score is good
        if not suggestions:
            suggestions.append(
                "Your resume is well-optimized for ATS systems. Consider tailoring "
                "specific keywords for each application."
            )

        return suggestions


def get_ats_analyzer(use_llm: bool = False) -> ATSAnalyzer:
    """
    Factory function to get an ATS Analyzer instance.

    Args:
        use_llm: Whether to enable LLM-enhanced suggestions

    Returns:
        ATSAnalyzer instance
    """
    return ATSAnalyzer(use_llm=use_llm)
