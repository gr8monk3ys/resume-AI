/**
 * LinkedIn Form Filler
 * Handles LinkedIn Easy Apply and job application forms
 */

class LinkedInFiller extends GenericFiller {
  constructor() {
    super()
    this.platform = 'linkedin'
  }

  /**
   * Fill LinkedIn application form
   * @param {Object} profileData User profile data
   * @returns {Object} Result with filled fields
   */
  async fill(profileData) {
    this.filledFields = []
    const dataMap = this.mapProfileData(profileData)

    // LinkedIn Easy Apply has a multi-step form
    // We need to handle each step

    // Step 1: Contact Info (usually pre-filled from LinkedIn profile)
    await this.fillContactInfo(dataMap)

    // Step 2: Resume upload
    await this.handleResumeUpload(profileData)

    // Step 3: Additional questions
    await this.fillAdditionalQuestions(dataMap)

    // Step 4: Work authorization and other questions
    await this.fillWorkAuthQuestions(profileData)

    return {
      success: true,
      filledFields: this.filledFields,
    }
  }

  /**
   * Fill contact information fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillContactInfo(dataMap) {
    // LinkedIn-specific selectors for contact info
    const contactSelectors = {
      email: [
        'input[name="email"]',
        'input[id*="email"]',
        '[data-test-single-line-text-input="email"]',
      ],
      phone: [
        'input[name="phone"]',
        'input[id*="phone"]',
        '[data-test-single-line-text-input="phone"]',
        'input[name="phoneNumber"]',
      ],
      firstName: [
        'input[name="firstName"]',
        '[data-test-single-line-text-input="firstName"]',
      ],
      lastName: [
        'input[name="lastName"]',
        '[data-test-single-line-text-input="lastName"]',
      ],
    }

    for (const [field, selectors] of Object.entries(contactSelectors)) {
      if (!dataMap[field]) continue

      for (const selector of selectors) {
        const input = document.querySelector(selector)
        if (input) {
          await this.fillField(input, dataMap[field])
          break
        }
      }
    }
  }

  /**
   * Handle resume file upload
   * @param {Object} profileData Profile data with resume info
   */
  async handleResumeUpload(profileData) {
    // TODO: Implement resume upload
    // LinkedIn Easy Apply typically shows previously uploaded resumes
    // We may need to select from existing or upload new

    const resumeUploadButton = document.querySelector([
      'button[aria-label*="Upload resume"]',
      '[data-test-document-upload-button]',
      '.jobs-document-upload__button',
    ].join(', '))

    if (resumeUploadButton) {
      console.log('[ResuBoost] Resume upload button found, manual upload required')
      // TODO: Trigger file picker with resume from profile
    }

    // Check for "Use previous resume" option
    const previousResume = document.querySelector([
      '.jobs-document-upload__container input[type="radio"]',
      '[data-test-document-select]',
    ].join(', '))

    if (previousResume) {
      previousResume.click()
      this.filledFields.push({ name: 'resume', type: 'select' })
    }
  }

  /**
   * Fill additional screening questions
   * @param {Object} dataMap Mapped profile data
   */
  async fillAdditionalQuestions(dataMap) {
    // LinkedIn presents custom questions from employers
    const questionContainers = document.querySelectorAll([
      '.jobs-easy-apply-form-section__grouping',
      '[data-test-form-element]',
    ].join(', '))

    for (const container of questionContainers) {
      const label = container.querySelector('label, .fb-dash-form-element__label')
      const labelText = (label?.textContent || '').toLowerCase()

      // Try to match common questions
      if (this.matchesPattern(labelText, ['experience', 'years'])) {
        await this.fillYearsExperience(container, dataMap)
      } else if (this.matchesPattern(labelText, ['linkedin', 'profile'])) {
        await this.fillLinkedInInput(container, dataMap.linkedIn)
      } else if (this.matchesPattern(labelText, ['website', 'portfolio'])) {
        await this.fillLinkedInInput(container, dataMap.website)
      } else if (this.matchesPattern(labelText, ['github'])) {
        await this.fillLinkedInInput(container, dataMap.github)
      } else if (this.matchesPattern(labelText, ['salary', 'compensation'])) {
        await this.fillSalaryQuestion(container, dataMap.salary)
      }
    }
  }

  /**
   * Fill work authorization questions
   * @param {Object} profileData Profile data with authorization info
   */
  async fillWorkAuthQuestions(profileData) {
    // Common work authorization questions
    const authQuestions = document.querySelectorAll([
      '[data-test-text-entity-list-form-component]',
      '.jobs-easy-apply-form-section',
    ].join(', '))

    for (const question of authQuestions) {
      const labelText = (question.textContent || '').toLowerCase()

      // Work authorization
      if (this.matchesPattern(labelText, ['authorized', 'legally', 'work in'])) {
        const yesOption = question.querySelector(
          'input[type="radio"][value="Yes"], input[type="radio"]:first-of-type'
        )
        if (yesOption && profileData.workAuthorization) {
          yesOption.click()
          this.filledFields.push({ name: 'workAuthorization', type: 'radio' })
        }
      }

      // Sponsorship required
      if (this.matchesPattern(labelText, ['sponsorship', 'visa'])) {
        const noOption = question.querySelector(
          'input[type="radio"][value="No"], input[type="radio"]:last-of-type'
        )
        if (noOption && !profileData.requiresSponsorship) {
          noOption.click()
          this.filledFields.push({ name: 'sponsorship', type: 'radio' })
        }
      }
    }
  }

  /**
   * Fill years of experience question
   * @param {HTMLElement} container Question container
   * @param {Object} dataMap Profile data
   */
  async fillYearsExperience(container, dataMap) {
    const input = container.querySelector('input[type="text"], input[type="number"], select')

    if (input && dataMap.yearsExperience) {
      await this.fillField(input, dataMap.yearsExperience.toString())
    }
  }

  /**
   * Fill a LinkedIn URL input
   * @param {HTMLElement} container Question container
   * @param {string} url URL to fill
   */
  async fillLinkedInInput(container, url) {
    const input = container.querySelector('input[type="text"], input[type="url"]')

    if (input && url) {
      await this.fillField(input, url)
    }
  }

  /**
   * Fill salary expectation question
   * @param {HTMLElement} container Question container
   * @param {string} salary Expected salary
   */
  async fillSalaryQuestion(container, salary) {
    const input = container.querySelector('input[type="text"], input[type="number"]')

    if (input && salary) {
      await this.fillField(input, salary.toString())
    }
  }

  /**
   * Check if text matches any of the patterns
   * @param {string} text Text to check
   * @param {string[]} patterns Patterns to match
   * @returns {boolean} True if any pattern matches
   */
  matchesPattern(text, patterns) {
    return patterns.some((pattern) => text.includes(pattern))
  }

  /**
   * Extract job details from LinkedIn job page
   * @returns {Object} Job details
   */
  extractJobDetails() {
    return {
      title: this.extractText([
        '.job-details-jobs-unified-top-card__job-title',
        '.jobs-unified-top-card__job-title',
        'h1.jobs-details__main-title',
      ]),
      company: this.extractText([
        '.job-details-jobs-unified-top-card__company-name',
        '.jobs-unified-top-card__company-name',
        '.jobs-details__main-company-name',
      ]),
      location: this.extractText([
        '.job-details-jobs-unified-top-card__bullet',
        '.jobs-unified-top-card__bullet',
        '.jobs-details__main-location',
      ]),
      description: this.extractText([
        '.jobs-description__content',
        '.jobs-box__html-content',
        '#job-details',
      ]),
      postedDate: this.extractText([
        '.jobs-unified-top-card__posted-date',
        '.job-details-jobs-unified-top-card__primary-description-without-tagline',
      ]),
      applicants: this.extractText([
        '.jobs-unified-top-card__applicant-count',
      ]),
    }
  }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.LinkedInFiller = LinkedInFiller
}
