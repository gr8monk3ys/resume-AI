# ResuBoost AI

A job-search toolkit: users track applications, tune resumes against job descriptions, and prepare for interviews, with optional LLM assistance.

## Language

**Profile**:
The owner of all job-search data; every application, resume, story and alert hangs off one Profile belonging to a User.
_Avoid_: Account, candidate

**Job Application**:
One tracked pursuit of a position at a company, moving through a Status. Stores recruiter, referral and source details.
_Avoid_: Job, role, lead

**Status**:
The pipeline stage of a Job Application: Bookmarked, Applied, Phone Screen, Interview, Offer, Rejected. Drives the Kanban board columns.
_Avoid_: Stage, state

**Resume**:
An uploaded or authored resume version; a Job Application may point at the Resume used.
_Avoid_: CV

**Cover Letter**:
A generated or written letter attached to a Job Application.

**Interview Event**:
A scheduled interview, call or meeting belonging to a Job Application.
_Avoid_: Meeting, appointment

## Analysis

**ATS Result**:
The algorithmic score of a Resume against a job description: overall, keyword-match and formatting scores, plus matched and missing keywords. Computed without an LLM.
_Avoid_: Resume score

**Keyword Suggestion**:
A missing keyword proposed for addition to a Resume after ATS analysis.

## Interview prep

**STAR Story**:
A behavioral-interview story written as Situation, Task, Action, Result.
_Avoid_: Anecdote

**Company Research**:
Saved notes on a company gathered for interview preparation.

**Career Journal**:
A log of achievements and milestones, mined later for resume and interview material.

## Job discovery

**Job Alert**:
Saved search criteria that the scheduler runs to surface new postings.

**Job Import**:
Creating a Job Application from a pasted URL or posting.

**Company Filter**:
A blacklist or whitelist entry for companies.

**Keyword Filter**:
An exclude or require keyword rule applied to a posting title, description or both.

**Application Question**:
A reusable answer to a recurring application form question (text, number, select or boolean).

## Guidance and billing

**Nudge**:
A computed, actionable prompt derived from existing data, typed as overdue_followup, stale_followup, interview_prep, thank_you, application_velocity or resume_freshness. A Nudge can be turned into a draft message.

**Subscription**:
A User's billing plan: free, pro_monthly or pro_annual.

**Usage Record**:
A per-user, per-period count of a feature's use, enforced against Subscription tier limits.

## Platform

**LLM Provider**:
The selectable backend behind AI features: openai, anthropic, google, ollama or mock. mock is the default.
