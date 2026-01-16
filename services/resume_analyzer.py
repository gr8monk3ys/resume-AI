import re
from collections import Counter
from typing import Dict, List, Tuple

from utils.cache import cached


class ATSAnalyzer:
    """
    Thread-safe analyzer for ATS (Applicant Tracking System) compatibility scoring.

    Note: This class is stateless - all text data is passed as parameters to avoid
    race conditions when the same instance is used concurrently.
    """

    # Common ATS-friendly keywords and criteria
    FORMATTING_KEYWORDS = [
        "experience",
        "education",
        "skills",
        "projects",
        "certifications",
        "achievements",
        "summary",
        "objective",
    ]

    TECHNICAL_SKILLS = [
        "python",
        "java",
        "javascript",
        "react",
        "node",
        "sql",
        "aws",
        "docker",
        "kubernetes",
        "git",
        "agile",
        "scrum",
        "ci/cd",
        "api",
        "rest",
        "graphql",
        "typescript",
        "html",
        "css",
        "mongodb",
        "postgresql",
        "redis",
        "kafka",
    ]

    SOFT_SKILLS = [
        "leadership",
        "communication",
        "collaboration",
        "problem-solving",
        "analytical",
        "team player",
        "creative",
        "innovative",
        "detail-oriented",
        "self-motivated",
        "adaptable",
        "organized",
        "time management",
    ]

    ACTION_VERBS = [
        "achieved",
        "developed",
        "implemented",
        "designed",
        "led",
        "managed",
        "created",
        "improved",
        "increased",
        "reduced",
        "streamlined",
        "optimized",
        "built",
        "launched",
        "delivered",
        "coordinated",
        "established",
        "initiated",
    ]

    # Pre-compiled regex patterns for performance
    _NUMBER_PATTERN = re.compile(r"\d+")
    _PERCENTAGE_PATTERN = re.compile(r"\d+%")
    _METRIC_PATTERN = re.compile(r"\d+[kKmMbB]?\+?")
    _WORD_PATTERN = re.compile(r"\b[a-z]{4,}\b")

    @cached(category="ats_analysis", ttl_seconds=3600)
    def analyze_resume(self, resume_text: str, job_description: str = "") -> Dict:
        """
        Analyze resume for ATS compatibility (thread-safe).

        Note: Results are cached for 1 hour to improve performance.

        Args:
            resume_text: The resume content
            job_description: Optional job description for comparison

        Returns:
            Dictionary containing ATS score and detailed analysis

        Raises:
            ValueError: If resume_text is empty
        """
        if not resume_text or not resume_text.strip():
            raise ValueError("Resume text cannot be empty")

        # Convert to lowercase for analysis (local variables, not instance state)
        resume_lower = resume_text.lower()
        job_lower = job_description.lower() if job_description else ""

        score_breakdown = {
            "formatting": self._check_formatting(resume_lower),
            "keywords": self._check_keywords(resume_lower),
            "action_verbs": self._check_action_verbs(resume_lower),
            "quantifiable_results": self._check_quantifiable_results(resume_lower),
            "length": self._check_length(resume_lower),
            "job_match": self._check_job_match(resume_lower, job_lower) if job_description else 0,
        }

        total_score = sum(score_breakdown.values())
        max_score = 100 if job_description else 80

        ats_score = int((total_score / max_score) * 100)

        return {
            "ats_score": min(ats_score, 100),
            "score_breakdown": score_breakdown,
            "suggestions": self._generate_suggestions(score_breakdown),
            "missing_keywords": self._find_missing_keywords(resume_lower, job_lower),
            "found_skills": self._extract_skills(resume_lower),
        }

    def _check_formatting(self, resume_text: str) -> int:
        """Check for standard resume sections (20 points max)."""
        sections_found = sum(1 for keyword in self.FORMATTING_KEYWORDS if keyword in resume_text)

        # Award points based on sections found
        if sections_found >= 5:
            return 20
        elif sections_found >= 4:
            return 15
        elif sections_found >= 3:
            return 10
        return 5

    def _check_keywords(self, resume_text: str) -> int:
        """Check for relevant keywords and skills (25 points max)."""
        technical_count = sum(1 for skill in self.TECHNICAL_SKILLS if skill in resume_text)
        soft_count = sum(1 for skill in self.SOFT_SKILLS if skill in resume_text)

        total_keywords = technical_count + soft_count
        return min(total_keywords * 2, 25)

    def _check_action_verbs(self, resume_text: str) -> int:
        """Check for strong action verbs (15 points max)."""
        action_verbs_found = sum(1 for verb in self.ACTION_VERBS if verb in resume_text)
        return min(action_verbs_found * 2, 15)

    def _check_quantifiable_results(self, resume_text: str) -> int:
        """Check for quantifiable achievements (20 points max)."""
        # Look for numbers, percentages, and metrics using pre-compiled patterns
        numbers = len(self._NUMBER_PATTERN.findall(resume_text))
        percentages = len(self._PERCENTAGE_PATTERN.findall(resume_text))
        metrics = len(self._METRIC_PATTERN.findall(resume_text))

        total_quantifiers = numbers + (percentages * 2) + (metrics * 2)
        return min(total_quantifiers, 20)

    def _check_length(self, resume_text: str) -> int:
        """Check if resume length is appropriate (10 points max)."""
        word_count = len(resume_text.split())

        # Ideal resume: 400-800 words
        if 400 <= word_count <= 800:
            return 10
        elif 300 <= word_count < 400 or 800 < word_count <= 1000:
            return 7
        # word_count < 300 or word_count > 1000
        return 5

    def _check_job_match(self, resume_text: str, job_description: str) -> int:
        """Check how well resume matches job description (20 points max)."""
        if not job_description:
            return 0

        # Extract important words from job description using pre-compiled pattern
        job_words = set(self._WORD_PATTERN.findall(job_description))
        resume_words = set(self._WORD_PATTERN.findall(resume_text))

        # Calculate match percentage
        common_words = job_words.intersection(resume_words)
        match_ratio = len(common_words) / len(job_words) if job_words else 0

        return int(match_ratio * 20)

    def _find_missing_keywords(self, resume_text: str, job_description: str) -> List[str]:
        """Find keywords from job description missing in resume."""
        if not job_description:
            return []

        job_words = set(self._WORD_PATTERN.findall(job_description))
        resume_words = set(self._WORD_PATTERN.findall(resume_text))

        # Focus on technical skills and important words
        all_important_words = set(self.TECHNICAL_SKILLS + self.SOFT_SKILLS)
        missing = (job_words - resume_words) & all_important_words

        return sorted(list(missing))[:10]  # Return top 10

    def _extract_skills(self, resume_text: str) -> Dict[str, List[str]]:
        """Extract skills found in the resume."""
        technical = [skill for skill in self.TECHNICAL_SKILLS if skill in resume_text]
        soft = [skill for skill in self.SOFT_SKILLS if skill in resume_text]

        return {"technical_skills": technical, "soft_skills": soft}

    def _generate_suggestions(self, score_breakdown: Dict[str, int]) -> List[str]:
        """Generate improvement suggestions based on scores."""
        suggestions = []

        if score_breakdown["formatting"] < 15:
            suggestions.append("Add clear section headers (Experience, Education, Skills, etc.)")

        if score_breakdown["keywords"] < 15:
            suggestions.append("Include more relevant technical and soft skills")

        if score_breakdown["action_verbs"] < 10:
            suggestions.append("Use strong action verbs (achieved, developed, led, etc.)")

        if score_breakdown["quantifiable_results"] < 10:
            suggestions.append("Add quantifiable metrics (percentages, numbers, growth metrics)")

        if score_breakdown["length"] < 8:
            suggestions.append("Adjust resume length to 400-800 words for optimal ATS scanning")

        if score_breakdown.get("job_match", 0) < 10:
            suggestions.append("Incorporate more keywords from the job description")

        if not suggestions:
            suggestions.append("Great job! Your resume is well-optimized for ATS systems.")

        return suggestions

    @cached(category="keyword_gap_analysis", ttl_seconds=3600)
    def analyze_keyword_gaps(self, resume_text: str, job_description: str) -> Dict:
        """
        Perform detailed keyword gap analysis between resume and job description.

        Args:
            resume_text: The resume content
            job_description: The job description to compare against

        Returns:
            Dictionary containing detailed gap analysis with categorized keywords
        """
        resume_lower = resume_text.lower()
        job_lower = job_description.lower()

        # Extract all words (4+ characters)
        resume_words = set(re.findall(r"\b[a-z]{4,}\b", resume_lower))
        job_words = set(re.findall(r"\b[a-z]{4,}\b", job_lower))

        # Find keywords in both
        common_words = resume_words & job_words

        # Find keywords only in job description (gaps)
        missing_from_resume = job_words - resume_words

        # Find keywords only in resume (potential strengths)
        unique_to_resume = resume_words - job_words

        # Categorize found keywords
        found_technical = [s for s in self.TECHNICAL_SKILLS if s in resume_lower and s in job_lower]
        found_soft = [s for s in self.SOFT_SKILLS if s in resume_lower and s in job_lower]
        found_action_verbs = [v for v in self.ACTION_VERBS if v in resume_lower]

        # Categorize missing keywords
        missing_technical = [
            s for s in self.TECHNICAL_SKILLS if s in job_lower and s not in resume_lower
        ]
        missing_soft = [s for s in self.SOFT_SKILLS if s in job_lower and s not in resume_lower]
        missing_action_verbs = [
            v for v in self.ACTION_VERBS if v in job_lower and v not in resume_lower
        ]

        # Extract job-specific keywords (not in standard lists but important)
        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "this",
            "that",
            "from",
            "have",
            "will",
            "your",
            "are",
            "was",
            "were",
            "been",
            "being",
            "has",
            "able",
            "about",
            "also",
            "they",
            "their",
            "more",
            "should",
            "would",
            "could",
            "other",
            "such",
            "like",
            "only",
            "just",
            "work",
            "working",
            "company",
            "team",
            "role",
            "position",
            "must",
            "well",
            "including",
            "provide",
            "ensure",
            "using",
            "experience",
            "years",
            "requirements",
            "responsibilities",
        }

        # Get high-frequency job keywords
        job_word_freq = Counter(re.findall(r"\b[a-z]{4,}\b", job_lower))
        important_job_keywords = [
            word
            for word, freq in job_word_freq.most_common(50)
            if word not in stop_words and freq >= 2
        ]

        # Missing important keywords from job description
        missing_important = [kw for kw in important_job_keywords if kw not in resume_lower][:15]

        # Calculate match percentage
        relevant_job_words = job_words - stop_words
        matched_relevant = relevant_job_words & resume_words
        match_percentage = (
            (len(matched_relevant) / len(relevant_job_words) * 100) if relevant_job_words else 0
        )

        # Generate keyword placement suggestions
        placement_suggestions = self._generate_placement_suggestions(
            missing_technical, missing_soft, missing_important
        )

        return {
            "match_percentage": round(match_percentage, 1),
            "total_job_keywords": len(relevant_job_words),
            "matched_keywords": len(matched_relevant),
            "missing_count": len(relevant_job_words) - len(matched_relevant),
            "found_keywords": {
                "technical": found_technical,
                "soft_skills": found_soft,
                "action_verbs": found_action_verbs,
                "other_matches": sorted(
                    list(common_words - set(found_technical) - set(found_soft))
                )[:20],
            },
            "missing_keywords": {
                "technical": missing_technical,
                "soft_skills": missing_soft,
                "action_verbs": missing_action_verbs,
                "important_job_terms": missing_important,
            },
            "unique_strengths": sorted(list(unique_to_resume))[:10],
            "placement_suggestions": placement_suggestions,
        }

    def _generate_placement_suggestions(
        self, missing_technical: List[str], missing_soft: List[str], missing_important: List[str]
    ) -> List[Dict[str, str]]:
        """Generate suggestions for where to place missing keywords."""
        suggestions = []

        # Technical skills suggestions
        if missing_technical:
            suggestions.append(
                {
                    "category": "Technical Skills",
                    "keywords": missing_technical[:5],
                    "suggestion": "Add these to your Skills section or incorporate them in your Experience bullet points where you've used these technologies.",
                }
            )

        # Soft skills suggestions
        if missing_soft:
            suggestions.append(
                {
                    "category": "Soft Skills",
                    "keywords": missing_soft[:5],
                    "suggestion": 'Demonstrate these skills in your Experience section with concrete examples. E.g., "Led cross-functional team of 5" shows leadership.',
                }
            )

        # Important job terms
        if missing_important:
            suggestions.append(
                {
                    "category": "Job-Specific Terms",
                    "keywords": missing_important[:5],
                    "suggestion": "These appear frequently in the job description. Consider adding them to your Summary or relevant Experience entries.",
                }
            )

        return suggestions


class JobMatchScorer:
    """Advanced job match scoring beyond simple keyword analysis."""

    # Experience level indicators
    ENTRY_LEVEL_INDICATORS = [
        "entry level",
        "junior",
        "associate",
        "0-2 years",
        "1-2 years",
        "new grad",
        "graduate",
        "intern",
        "trainee",
        "early career",
    ]

    MID_LEVEL_INDICATORS = [
        "mid-level",
        "mid level",
        "3-5 years",
        "2-5 years",
        "3+ years",
        "4+ years",
        "5+ years",
        "experienced",
    ]

    SENIOR_LEVEL_INDICATORS = [
        "senior",
        "lead",
        "principal",
        "staff",
        "6+ years",
        "7+ years",
        "8+ years",
        "10+ years",
        "architect",
        "manager",
        "director",
    ]

    # Education level mapping
    EDUCATION_LEVELS = {
        "high school": 1,
        "associate": 2,
        "bachelor": 3,
        "bs": 3,
        "ba": 3,
        "b.s.": 3,
        "b.a.": 3,
        "master": 4,
        "ms": 4,
        "ma": 4,
        "m.s.": 4,
        "m.a.": 4,
        "mba": 4,
        "phd": 5,
        "ph.d": 5,
        "doctorate": 5,
        "doctoral": 5,
    }

    # Common benefit keywords
    BENEFIT_KEYWORDS = [
        "remote",
        "hybrid",
        "flexible",
        "unlimited pto",
        "equity",
        "stock",
        "bonus",
        "401k",
        "health",
        "dental",
        "vision",
    ]

    @cached(category="job_match_score", ttl_seconds=3600)
    def calculate_match_score(self, resume_text: str, job_description: str) -> Dict:
        """
        Calculate comprehensive job match score.

        Args:
            resume_text: The resume content
            job_description: The job description

        Returns:
            Dictionary with detailed match scores and recommendations
        """
        resume_lower = resume_text.lower()
        job_lower = job_description.lower()

        # Calculate individual scores
        skills_score = self._calculate_skills_match(resume_lower, job_lower)
        experience_score = self._calculate_experience_match(resume_lower, job_lower)
        education_score = self._calculate_education_match(resume_lower, job_lower)
        keyword_score = self._calculate_keyword_density(resume_lower, job_lower)
        soft_skills_score = self._calculate_soft_skills_match(resume_lower, job_lower)

        # Weighted overall score
        weights = {
            "skills": 0.30,
            "experience": 0.25,
            "education": 0.15,
            "keywords": 0.20,
            "soft_skills": 0.10,
        }

        overall_score = (
            skills_score["score"] * weights["skills"]
            + experience_score["score"] * weights["experience"]
            + education_score["score"] * weights["education"]
            + keyword_score["score"] * weights["keywords"]
            + soft_skills_score["score"] * weights["soft_skills"]
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            skills_score, experience_score, education_score, keyword_score, soft_skills_score
        )

        # Determine match level
        if overall_score >= 80:
            match_level = "Excellent Match"
            match_color = "green"
        elif overall_score >= 65:
            match_level = "Good Match"
            match_color = "green"
        elif overall_score >= 50:
            match_level = "Moderate Match"
            match_color = "orange"
        elif overall_score >= 35:
            match_level = "Partial Match"
            match_color = "orange"
        else:
            match_level = "Low Match"
            match_color = "red"

        return {
            "overall_score": round(overall_score, 1),
            "match_level": match_level,
            "match_color": match_color,
            "breakdown": {
                "skills": skills_score,
                "experience": experience_score,
                "education": education_score,
                "keywords": keyword_score,
                "soft_skills": soft_skills_score,
            },
            "weights": weights,
            "recommendations": recommendations,
            "apply_recommendation": self._get_apply_recommendation(overall_score),
        }

    def _calculate_skills_match(self, resume: str, job: str) -> Dict:
        """Calculate technical skills match."""
        # Extended technical skills list
        all_skills = [
            "python",
            "java",
            "javascript",
            "typescript",
            "react",
            "angular",
            "vue",
            "node",
            "nodejs",
            "express",
            "django",
            "flask",
            "fastapi",
            "spring",
            "sql",
            "mysql",
            "postgresql",
            "mongodb",
            "redis",
            "elasticsearch",
            "aws",
            "azure",
            "gcp",
            "docker",
            "kubernetes",
            "terraform",
            "git",
            "jenkins",
            "ci/cd",
            "agile",
            "scrum",
            "jira",
            "machine learning",
            "deep learning",
            "tensorflow",
            "pytorch",
            "data analysis",
            "pandas",
            "numpy",
            "spark",
            "hadoop",
            "rest",
            "api",
            "graphql",
            "microservices",
            "serverless",
            "linux",
            "bash",
            "shell",
            "networking",
            "security",
            "html",
            "css",
            "sass",
            "webpack",
            "figma",
            "sketch",
        ]

        job_skills = [s for s in all_skills if s in job]
        matched_skills = [s for s in job_skills if s in resume]
        missing_skills = [s for s in job_skills if s not in resume]

        score = (len(matched_skills) / len(job_skills) * 100) if job_skills else 100

        return {
            "score": min(score, 100),
            "matched": matched_skills,
            "missing": missing_skills,
            "total_required": len(job_skills),
        }

    def _calculate_experience_match(self, resume: str, job: str) -> Dict:
        """Calculate experience level match."""
        # Detect job's required level
        job_level = "mid"  # default
        if any(ind in job for ind in self.ENTRY_LEVEL_INDICATORS):
            job_level = "entry"
        elif any(ind in job for ind in self.SENIOR_LEVEL_INDICATORS):
            job_level = "senior"
        elif any(ind in job for ind in self.MID_LEVEL_INDICATORS):
            job_level = "mid"

        # Detect resume's experience level
        resume_level = "mid"  # default
        if any(ind in resume for ind in self.SENIOR_LEVEL_INDICATORS):
            resume_level = "senior"
        elif any(ind in resume for ind in self.ENTRY_LEVEL_INDICATORS):
            resume_level = "entry"

        # Extract years of experience from resume
        years_pattern = r"(\d+)\+?\s*years?\s*(?:of\s+)?(?:experience|exp)"
        years_matches = re.findall(years_pattern, resume)
        resume_years = max([int(y) for y in years_matches]) if years_matches else 0

        # Extract required years from job
        job_years_matches = re.findall(years_pattern, job)
        required_years = min([int(y) for y in job_years_matches]) if job_years_matches else 0

        # Calculate score
        level_match = {
            ("entry", "entry"): 100,
            ("entry", "mid"): 70,
            ("entry", "senior"): 50,
            ("mid", "entry"): 90,
            ("mid", "mid"): 100,
            ("mid", "senior"): 70,
            ("senior", "entry"): 80,
            ("senior", "mid"): 95,
            ("senior", "senior"): 100,
        }

        base_score = level_match.get((resume_level, job_level), 75)

        # Adjust for years
        if required_years > 0:
            if resume_years >= required_years:
                years_bonus = 10
            elif resume_years >= required_years - 1:
                years_bonus = 0
            else:
                years_bonus = -15
            base_score = min(100, max(0, base_score + years_bonus))

        return {
            "score": base_score,
            "resume_level": resume_level,
            "job_level": job_level,
            "resume_years": resume_years,
            "required_years": required_years,
        }

    def _calculate_education_match(self, resume: str, job: str) -> Dict:
        """Calculate education requirements match."""
        # Find highest education in resume
        resume_edu_level = 0
        resume_edu_name = "Not specified"
        for edu, level in self.EDUCATION_LEVELS.items():
            if edu in resume and level > resume_edu_level:
                resume_edu_level = level
                resume_edu_name = edu

        # Find required education in job
        required_edu_level = 0
        required_edu_name = "Not specified"
        for edu, level in self.EDUCATION_LEVELS.items():
            if edu in job and level > required_edu_level:
                required_edu_level = level
                required_edu_name = edu

        # Calculate score
        if required_edu_level == 0:
            score = 100  # No requirement specified
        elif resume_edu_level >= required_edu_level:
            score = 100
        elif resume_edu_level == required_edu_level - 1:
            score = 75  # One level below
        else:
            score = 50  # Significantly below

        return {
            "score": score,
            "resume_education": resume_edu_name,
            "required_education": required_edu_name,
            "meets_requirement": resume_edu_level >= required_edu_level,
        }

    def _calculate_keyword_density(self, resume: str, job: str) -> Dict:
        """Calculate keyword overlap density."""
        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "this",
            "that",
            "from",
            "have",
            "will",
            "your",
            "are",
            "was",
            "were",
            "been",
            "being",
            "has",
            "able",
            "about",
            "also",
            "they",
            "their",
            "more",
            "should",
            "would",
            "could",
            "other",
            "such",
            "like",
            "only",
            "just",
        }

        job_words = set(re.findall(r"\b[a-z]{4,}\b", job)) - stop_words
        resume_words = set(re.findall(r"\b[a-z]{4,}\b", resume)) - stop_words

        if not job_words:
            return {"score": 100, "overlap_percentage": 100, "matched_count": 0}

        matched = job_words & resume_words
        overlap_pct = len(matched) / len(job_words) * 100

        # Score with diminishing returns after 70%
        if overlap_pct >= 70:
            score = 85 + (overlap_pct - 70) * 0.5
        else:
            score = overlap_pct * 1.2

        return {
            "score": min(score, 100),
            "overlap_percentage": round(overlap_pct, 1),
            "matched_count": len(matched),
            "total_job_keywords": len(job_words),
        }

    def _calculate_soft_skills_match(self, resume: str, job: str) -> Dict:
        """Calculate soft skills match."""
        soft_skills = [
            "leadership",
            "communication",
            "teamwork",
            "collaboration",
            "problem-solving",
            "problem solving",
            "analytical",
            "creative",
            "adaptable",
            "flexible",
            "organized",
            "detail-oriented",
            "self-motivated",
            "proactive",
            "mentoring",
            "coaching",
            "presentation",
            "negotiation",
            "conflict resolution",
            "time management",
            "prioritization",
            "multitasking",
        ]

        job_soft_skills = [s for s in soft_skills if s in job]
        matched = [s for s in job_soft_skills if s in resume]

        score = (len(matched) / len(job_soft_skills) * 100) if job_soft_skills else 100

        return {
            "score": min(score, 100),
            "matched": matched,
            "missing": [s for s in job_soft_skills if s not in resume],
        }

    def _generate_recommendations(
        self, skills, experience, education, keywords, soft_skills
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if skills["score"] < 70 and skills.get("missing"):
            missing_str = ", ".join(skills["missing"][:5])
            recommendations.append(f"Add missing technical skills: {missing_str}")

        if experience["score"] < 70:
            if experience["resume_years"] < experience["required_years"]:
                recommendations.append(
                    f"Job requires {experience['required_years']}+ years. "
                    "Emphasize relevant projects and transferable experience."
                )

        if education["score"] < 70 and not education["meets_requirement"]:
            recommendations.append(
                "Education may not meet requirements. Highlight certifications, "
                "bootcamps, or equivalent practical experience."
            )

        if keywords["score"] < 70:
            recommendations.append(
                f"Keyword match is {keywords['overlap_percentage']:.0f}%. "
                "Mirror more language from the job description."
            )

        if soft_skills["score"] < 70 and soft_skills.get("missing"):
            recommendations.append("Add soft skills demonstrations in your experience bullets.")

        if not recommendations:
            recommendations.append("Strong match! Tailor your cover letter to stand out.")

        return recommendations

    def _get_apply_recommendation(self, score: float) -> Dict:
        """Get recommendation on whether to apply."""
        if score >= 70:
            return {
                "should_apply": True,
                "confidence": "High",
                "message": "You're a strong candidate. Apply with confidence!",
            }
        elif score >= 50:
            return {
                "should_apply": True,
                "confidence": "Medium",
                "message": "You meet many requirements. Apply and highlight your strengths.",
            }
        elif score >= 35:
            return {
                "should_apply": "Maybe",
                "confidence": "Low",
                "message": "Consider if you can demonstrate transferable skills. May be a stretch role.",
            }
        else:
            return {
                "should_apply": False,
                "confidence": "Low",
                "message": "This role may not be the best fit. Consider roles more aligned with your background.",
            }


def extract_keywords(text: str, top_n: int = 20) -> List[Tuple[str, int]]:
    """
    Extract most common keywords from text.

    Args:
        text: Text to analyze
        top_n: Number of top keywords to return

    Returns:
        List of (keyword, frequency) tuples
    """
    # Remove common stop words
    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "have",
        "will",
        "your",
        "are",
        "was",
        "were",
        "been",
        "being",
        "has",
    }

    words = re.findall(r"\b[a-z]{4,}\b", text.lower())
    filtered_words = [word for word in words if word not in stop_words]

    word_freq = Counter(filtered_words)
    return word_freq.most_common(top_n)
