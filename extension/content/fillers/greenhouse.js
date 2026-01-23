/**
 * Greenhouse Form Filler
 * Handles Greenhouse ATS job application forms
 */

class GreenhouseFiller extends GenericFiller {
  constructor() {
    super()
    this.platform = 'greenhouse'
  }

  /**
   * Fill Greenhouse application form
   * @param {Object} profileData User profile data
   * @returns {Object} Result with filled fields
   */
  async fill(profileData) {
    this.filledFields = []
    const dataMap = this.mapProfileData(profileData)

    // Greenhouse forms are typically single-page
    // with sections for personal info, resume, and custom questions

    // Section 1: Personal Information
    await this.fillPersonalInfo(dataMap)

    // Section 2: Resume and Cover Letter
    await this.handleDocuments(profileData)

    // Section 3: Links (LinkedIn, Portfolio, etc.)
    await this.fillLinks(dataMap)

    // Section 4: Custom Questions
    await this.fillCustomQuestions(dataMap, profileData)

    // Section 5: Demographic Information (optional)
    await this.fillDemographicInfo(profileData)

    return {
      success: true,
      filledFields: this.filledFields,
    }
  }

  /**
   * Fill personal information fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillPersonalInfo(dataMap) {
    // Greenhouse uses specific IDs and names for fields
    const fieldMappings = [
      { field: 'firstName', selectors: ['#first_name', 'input[name="first_name"]'] },
      { field: 'lastName', selectors: ['#last_name', 'input[name="last_name"]'] },
      { field: 'email', selectors: ['#email', 'input[name="email"]'] },
      { field: 'phone', selectors: ['#phone', 'input[name="phone"]'] },
      { field: 'address', selectors: ['#address', 'input[name="address"]'] },
      { field: 'city', selectors: ['#city', 'input[name="city"]'] },
      { field: 'state', selectors: ['#state', 'input[name="state"]', 'select[name="state"]'] },
      { field: 'zipCode', selectors: ['#zip', 'input[name="zip"]', 'input[name="postal_code"]'] },
    ]

    for (const { field, selectors } of fieldMappings) {
      if (!dataMap[field]) continue

      for (const selector of selectors) {
        const input = document.querySelector(selector)
        if (input) {
          await this.fillField(input, dataMap[field])
          break
        }
      }
    }

    // Handle country dropdown (often a select element)
    const countrySelect = document.querySelector('#country, select[name="country"]')
    if (countrySelect && dataMap.country) {
      await this.fillCountrySelect(countrySelect, dataMap.country)
    }
  }

  /**
   * Fill country select dropdown
   * @param {HTMLSelectElement} select Country select element
   * @param {string} country Country name or code
   */
  async fillCountrySelect(select, country) {
    const countryLower = country.toLowerCase()

    // Common country mappings
    const countryMappings = {
      'us': 'united states',
      'usa': 'united states',
      'uk': 'united kingdom',
      'gb': 'united kingdom',
    }

    const searchTerm = countryMappings[countryLower] || countryLower

    for (const option of select.options) {
      const optionText = option.text.toLowerCase()
      const optionValue = option.value.toLowerCase()

      if (
        optionText.includes(searchTerm) ||
        optionValue === countryLower ||
        searchTerm.includes(optionText)
      ) {
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        this.filledFields.push({ name: 'country', type: 'select' })
        return
      }
    }
  }

  /**
   * Handle resume and cover letter uploads
   * @param {Object} profileData Profile data with document info
   */
  async handleDocuments(profileData) {
    // Resume upload
    const resumeInput = document.querySelector([
      'input[type="file"][name*="resume"]',
      'input[type="file"][id*="resume"]',
      'input[type="file"][data-field="resume"]',
      '.resume-upload input[type="file"]',
    ].join(', '))

    if (resumeInput) {
      console.log('[ResuBoost] Resume upload field found')
      // TODO: Implement file upload
      // The actual upload requires setting the files property
      // which needs to be done via DataTransfer API
    }

    // Cover letter upload
    const coverLetterInput = document.querySelector([
      'input[type="file"][name*="cover"]',
      'input[type="file"][id*="cover"]',
      'input[type="file"][data-field="cover_letter"]',
    ].join(', '))

    if (coverLetterInput) {
      console.log('[ResuBoost] Cover letter upload field found')
      // TODO: Implement file upload
    }

    // Cover letter text field
    const coverLetterText = document.querySelector([
      'textarea[name*="cover"]',
      '#cover_letter',
      '[data-field="cover_letter_text"] textarea',
    ].join(', '))

    if (coverLetterText && profileData.coverLetter) {
      await this.fillField(coverLetterText, profileData.coverLetter)
    }
  }

  /**
   * Fill link fields (LinkedIn, Portfolio, etc.)
   * @param {Object} dataMap Mapped profile data
   */
  async fillLinks(dataMap) {
    const linkMappings = [
      {
        field: 'linkedIn',
        selectors: [
          'input[name*="linkedin"]',
          'input[id*="linkedin"]',
          'input[placeholder*="LinkedIn"]',
        ],
      },
      {
        field: 'website',
        selectors: [
          'input[name*="website"]',
          'input[name*="portfolio"]',
          'input[id*="website"]',
          'input[placeholder*="Website"]',
          'input[placeholder*="Portfolio"]',
        ],
      },
      {
        field: 'github',
        selectors: [
          'input[name*="github"]',
          'input[id*="github"]',
          'input[placeholder*="GitHub"]',
        ],
      },
    ]

    for (const { field, selectors } of linkMappings) {
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
   * Fill custom screening questions
   * @param {Object} dataMap Mapped profile data
   * @param {Object} profileData Full profile data
   */
  async fillCustomQuestions(dataMap, profileData) {
    // Get all question containers
    const questions = document.querySelectorAll([
      '.field',
      '.application-question',
      '[data-controller="application"] .field',
    ].join(', '))

    for (const question of questions) {
      const labelElement = question.querySelector('label')
      const labelText = (labelElement?.textContent || '').toLowerCase()

      // Years of experience
      if (this.matchesPattern(labelText, ['years', 'experience'])) {
        const input = question.querySelector('input, select')
        if (input && dataMap.yearsExperience) {
          await this.fillField(input, dataMap.yearsExperience.toString())
        }
      }

      // Salary expectations
      if (this.matchesPattern(labelText, ['salary', 'compensation', 'pay'])) {
        const input = question.querySelector('input')
        if (input && dataMap.salary) {
          await this.fillField(input, dataMap.salary.toString())
        }
      }

      // Start date
      if (this.matchesPattern(labelText, ['start date', 'available', 'when can you'])) {
        const input = question.querySelector('input')
        if (input && profileData.availableDate) {
          await this.fillField(input, profileData.availableDate)
        }
      }

      // Work authorization - Yes/No radio buttons
      if (this.matchesPattern(labelText, ['authorized', 'eligible', 'legally'])) {
        await this.fillYesNoQuestion(question, profileData.workAuthorization !== false)
      }

      // Sponsorship required
      if (this.matchesPattern(labelText, ['sponsorship', 'visa'])) {
        await this.fillYesNoQuestion(question, profileData.requiresSponsorship === true)
      }

      // How did you hear about us
      if (this.matchesPattern(labelText, ['how did you hear', 'source', 'referred'])) {
        const select = question.querySelector('select')
        if (select) {
          // Try to select a generic option
          await this.selectFirstValidOption(select)
        }
      }
    }
  }

  /**
   * Fill Yes/No radio button question
   * @param {HTMLElement} container Question container
   * @param {boolean} value True for Yes, False for No
   */
  async fillYesNoQuestion(container, value) {
    const radios = container.querySelectorAll('input[type="radio"]')

    for (const radio of radios) {
      const labelText = this.getLabelText(radio).toLowerCase()
      const radioValue = radio.value.toLowerCase()

      const isYes = radioValue === 'yes' || radioValue === 'true' || labelText.includes('yes')
      const isNo = radioValue === 'no' || radioValue === 'false' || labelText.includes('no')

      if ((value && isYes) || (!value && isNo)) {
        radio.click()
        this.filledFields.push({ name: radio.name, type: 'radio' })
        return
      }
    }
  }

  /**
   * Select first valid option in a select dropdown
   * @param {HTMLSelectElement} select Select element
   */
  async selectFirstValidOption(select) {
    // Skip the first option if it's a placeholder
    for (let i = 0; i < select.options.length; i++) {
      const option = select.options[i]
      if (option.value && option.value !== '' && !option.disabled) {
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        this.filledFields.push({ name: select.name || select.id, type: 'select' })
        return
      }
    }
  }

  /**
   * Fill demographic information (optional EEOC questions)
   * @param {Object} profileData Profile data with demographic info
   */
  async fillDemographicInfo(profileData) {
    // These are voluntary and should respect user preferences
    if (!profileData.demographics) {
      return
    }

    const demographics = profileData.demographics

    // Gender
    if (demographics.gender) {
      const genderSelect = document.querySelector('select[name*="gender"], #gender')
      if (genderSelect) {
        await this.fillSelect(genderSelect, demographics.gender)
      }
    }

    // Ethnicity
    if (demographics.ethnicity) {
      const ethnicitySelect = document.querySelector('select[name*="race"], select[name*="ethnicity"]')
      if (ethnicitySelect) {
        await this.fillSelect(ethnicitySelect, demographics.ethnicity)
      }
    }

    // Veteran status
    if (demographics.veteranStatus) {
      const veteranSelect = document.querySelector('select[name*="veteran"]')
      if (veteranSelect) {
        await this.fillSelect(veteranSelect, demographics.veteranStatus)
      }
    }

    // Disability status
    if (demographics.disabilityStatus) {
      const disabilitySelect = document.querySelector('select[name*="disability"]')
      if (disabilitySelect) {
        await this.fillSelect(disabilitySelect, demographics.disabilityStatus)
      }
    }
  }

  /**
   * Check if text matches any pattern
   * @param {string} text Text to check
   * @param {string[]} patterns Patterns to match
   * @returns {boolean} True if matches
   */
  matchesPattern(text, patterns) {
    return patterns.some((pattern) => text.includes(pattern))
  }

  /**
   * Extract job details from Greenhouse job page
   * @returns {Object} Job details
   */
  extractJobDetails() {
    return {
      title: this.extractText([
        '.job-title',
        '.app-title',
        'h1.posting-headline',
        '#header .app-title',
      ]),
      company: this.extractText([
        '.company-name',
        '.posting-intro .company-name',
        '[data-company-name]',
      ]),
      location: this.extractText([
        '.location',
        '.posting-location',
        '.job-location',
      ]),
      description: this.extractText([
        '#content',
        '.content',
        '.job-description',
        '[data-description]',
      ]),
      department: this.extractText([
        '.department',
        '.posting-department',
      ]),
    }
  }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.GreenhouseFiller = GreenhouseFiller
}
