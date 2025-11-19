import re
from typing import Dict, List, Tuple
from collections import Counter
from utils.cache import cached

class ATSAnalyzer:
    """Analyzer for ATS (Applicant Tracking System) compatibility scoring."""

    # Common ATS-friendly keywords and criteria
    FORMATTING_KEYWORDS = [
        'experience', 'education', 'skills', 'projects', 'certifications',
        'achievements', 'summary', 'objective'
    ]

    TECHNICAL_SKILLS = [
        'python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 'docker',
        'kubernetes', 'git', 'agile', 'scrum', 'ci/cd', 'api', 'rest', 'graphql',
        'typescript', 'html', 'css', 'mongodb', 'postgresql', 'redis', 'kafka'
    ]

    SOFT_SKILLS = [
        'leadership', 'communication', 'collaboration', 'problem-solving',
        'analytical', 'team player', 'creative', 'innovative', 'detail-oriented',
        'self-motivated', 'adaptable', 'organized', 'time management'
    ]

    ACTION_VERBS = [
        'achieved', 'developed', 'implemented', 'designed', 'led', 'managed',
        'created', 'improved', 'increased', 'reduced', 'streamlined', 'optimized',
        'built', 'launched', 'delivered', 'coordinated', 'established', 'initiated'
    ]

    def __init__(self):
        self.resume_text = ""
        self.job_description = ""

    @cached(category='ats_analysis', ttl_seconds=3600)
    def analyze_resume(self, resume_text: str, job_description: str = "") -> Dict:
        """
        Analyze resume for ATS compatibility.

        Note: Results are cached for 1 hour to improve performance.

        Args:
            resume_text: The resume content
            job_description: Optional job description for comparison

        Returns:
            Dictionary containing ATS score and detailed analysis
        """
        self.resume_text = resume_text.lower()
        self.job_description = job_description.lower()

        score_breakdown = {
            'formatting': self._check_formatting(),
            'keywords': self._check_keywords(),
            'action_verbs': self._check_action_verbs(),
            'quantifiable_results': self._check_quantifiable_results(),
            'length': self._check_length(),
            'job_match': self._check_job_match() if job_description else 0
        }

        total_score = sum(score_breakdown.values())
        max_score = 100 if job_description else 80

        ats_score = int((total_score / max_score) * 100)

        return {
            'ats_score': min(ats_score, 100),
            'score_breakdown': score_breakdown,
            'suggestions': self._generate_suggestions(score_breakdown),
            'missing_keywords': self._find_missing_keywords(),
            'found_skills': self._extract_skills()
        }

    def _check_formatting(self) -> int:
        """Check for standard resume sections (20 points max)."""
        score = 0
        sections_found = sum(1 for keyword in self.FORMATTING_KEYWORDS
                           if keyword in self.resume_text)

        # Award points based on sections found
        if sections_found >= 5:
            score = 20
        elif sections_found >= 4:
            score = 15
        elif sections_found >= 3:
            score = 10
        else:
            score = 5

        return score

    def _check_keywords(self) -> int:
        """Check for relevant keywords and skills (25 points max)."""
        technical_count = sum(1 for skill in self.TECHNICAL_SKILLS
                             if skill in self.resume_text)
        soft_count = sum(1 for skill in self.SOFT_SKILLS
                        if skill in self.resume_text)

        total_keywords = technical_count + soft_count
        score = min(total_keywords * 2, 25)

        return score

    def _check_action_verbs(self) -> int:
        """Check for strong action verbs (15 points max)."""
        action_verbs_found = sum(1 for verb in self.ACTION_VERBS
                                if verb in self.resume_text)

        score = min(action_verbs_found * 2, 15)
        return score

    def _check_quantifiable_results(self) -> int:
        """Check for quantifiable achievements (20 points max)."""
        # Look for numbers, percentages, and metrics
        numbers = len(re.findall(r'\d+', self.resume_text))
        percentages = len(re.findall(r'\d+%', self.resume_text))
        metrics = len(re.findall(r'\d+[kKmMbB]?\+?', self.resume_text))

        total_quantifiers = numbers + (percentages * 2) + (metrics * 2)
        score = min(total_quantifiers, 20)

        return score

    def _check_length(self) -> int:
        """Check if resume length is appropriate (10 points max)."""
        word_count = len(self.resume_text.split())

        # Ideal resume: 400-800 words
        if 400 <= word_count <= 800:
            return 10
        elif 300 <= word_count < 400 or 800 < word_count <= 1000:
            return 7
        elif word_count < 300 or word_count > 1000:
            return 5

        return 5

    def _check_job_match(self) -> int:
        """Check how well resume matches job description (20 points max)."""
        if not self.job_description:
            return 0

        # Extract important words from job description
        job_words = set(re.findall(r'\b[a-z]{4,}\b', self.job_description))
        resume_words = set(re.findall(r'\b[a-z]{4,}\b', self.resume_text))

        # Calculate match percentage
        common_words = job_words.intersection(resume_words)
        match_ratio = len(common_words) / len(job_words) if job_words else 0

        score = int(match_ratio * 20)
        return score

    def _find_missing_keywords(self) -> List[str]:
        """Find keywords from job description missing in resume."""
        if not self.job_description:
            return []

        job_words = set(re.findall(r'\b[a-z]{4,}\b', self.job_description))
        resume_words = set(re.findall(r'\b[a-z]{4,}\b', self.resume_text))

        # Focus on technical skills and important words
        all_important_words = set(self.TECHNICAL_SKILLS + self.SOFT_SKILLS)
        missing = (job_words - resume_words) & all_important_words

        return sorted(list(missing))[:10]  # Return top 10

    def _extract_skills(self) -> Dict[str, List[str]]:
        """Extract skills found in the resume."""
        technical = [skill for skill in self.TECHNICAL_SKILLS
                    if skill in self.resume_text]
        soft = [skill for skill in self.SOFT_SKILLS
               if skill in self.resume_text]

        return {
            'technical_skills': technical,
            'soft_skills': soft
        }

    def _generate_suggestions(self, score_breakdown: Dict[str, int]) -> List[str]:
        """Generate improvement suggestions based on scores."""
        suggestions = []

        if score_breakdown['formatting'] < 15:
            suggestions.append("Add clear section headers (Experience, Education, Skills, etc.)")

        if score_breakdown['keywords'] < 15:
            suggestions.append("Include more relevant technical and soft skills")

        if score_breakdown['action_verbs'] < 10:
            suggestions.append("Use strong action verbs (achieved, developed, led, etc.)")

        if score_breakdown['quantifiable_results'] < 10:
            suggestions.append("Add quantifiable metrics (percentages, numbers, growth metrics)")

        if score_breakdown['length'] < 8:
            suggestions.append("Adjust resume length to 400-800 words for optimal ATS scanning")

        if score_breakdown.get('job_match', 0) < 10:
            suggestions.append("Incorporate more keywords from the job description")

        if not suggestions:
            suggestions.append("Great job! Your resume is well-optimized for ATS systems.")

        return suggestions

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
        'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have',
        'will', 'your', 'are', 'was', 'were', 'been', 'being', 'has'
    }

    words = re.findall(r'\b[a-z]{4,}\b', text.lower())
    filtered_words = [word for word in words if word not in stop_words]

    word_freq = Counter(filtered_words)
    return word_freq.most_common(top_n)
