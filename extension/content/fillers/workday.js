/**
 * Workday Form Filler
 * Handles Workday ATS job application forms
 *
 * Note: Workday forms are complex and vary significantly between companies.
 * This filler provides a best-effort approach to fill common fields.
 */

class WorkdayFiller extends GenericFiller {
  constructor() {
    super()
    this.platform = 'workday'
  }

  /**
   * Fill Workday application form
   * @param {Object} profileData User profile data
   * @returns {Object} Result with filled fields
   */
  async fill(profileData) {
    this.filledFields = []
    const dataMap = this.mapProfileData(profileData)

    // Workday often uses multi-page forms
    // We need to handle whatever page we're on

    // Wait for Workday's dynamic content to load
    await this.waitForWorkdayLoad()

    // Detect which section/page we're on
    const currentSection = this.detectCurrentSection()

    switch (currentSection) {
      case 'personal':
        await this.fillPersonalInfo(dataMap)
        break
      case 'contact':
        await this.fillContactInfo(dataMap)
        break
      case 'experience':
        await this.fillExperience(profileData)
        break
      case 'education':
        await this.fillEducation(profileData)
        break
      case 'resume':
        await this.handleResume(profileData)
        break
      case 'questions':
        await this.fillCustomQuestions(dataMap, profileData)
        break
      default:
        // Try to fill all visible fields
        await this.fillAllVisibleFields(dataMap, profileData)
    }

    return {
      success: true,
      filledFields: this.filledFields,
    }
  }

  /**
   * Wait for Workday's dynamic content to load
   */
  async waitForWorkdayLoad() {
    return new Promise((resolve) => {
      // Check for loading indicators
      const checkLoading = () => {
        const loadingIndicator = document.querySelector([
          '[data-automation-id="loading"]',
          '.wd-loading',
          '.loading-overlay',
        ].join(', '))

        if (!loadingIndicator || loadingIndicator.style.display === 'none') {
          resolve()
        } else {
          setTimeout(checkLoading, 100)
        }
      }

      setTimeout(checkLoading, 500)
    })
  }

  /**
   * Detect current section of the application
   * @returns {string} Section name
   */
  detectCurrentSection() {
    const sectionIndicators = {
      personal: ['personal information', 'about you', 'my information'],
      contact: ['contact information', 'contact details', 'how can we reach you'],
      experience: ['work experience', 'employment history', 'professional experience'],
      education: ['education', 'academic', 'degree'],
      resume: ['resume', 'cv', 'upload'],
      questions: ['additional questions', 'screening questions', 'questionnaire'],
    }

    // Check page header or section title
    const headers = document.querySelectorAll([
      '[data-automation-id="pageHeaderTitle"]',
      '.wd-section-title',
      'h2',
      '.header-title',
    ].join(', '))

    for (const header of headers) {
      const headerText = (header.textContent || '').toLowerCase()

      for (const [section, indicators] of Object.entries(sectionIndicators)) {
        if (indicators.some((indicator) => headerText.includes(indicator))) {
          return section
        }
      }
    }

    return 'unknown'
  }

  /**
   * Fill personal information fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillPersonalInfo(dataMap) {
    const fieldMappings = [
      {
        field: 'firstName',
        automationIds: ['legalNameSection_firstName', 'firstName', 'name_first'],
      },
      {
        field: 'lastName',
        automationIds: ['legalNameSection_lastName', 'lastName', 'name_last'],
      },
      {
        field: 'country',
        automationIds: ['countryDropdown', 'country'],
      },
    ]

    for (const { field, automationIds } of fieldMappings) {
      if (!dataMap[field]) continue

      for (const automationId of automationIds) {
        const input = this.findWorkdayInput(automationId)
        if (input) {
          await this.fillWorkdayField(input, dataMap[field])
          break
        }
      }
    }
  }

  /**
   * Fill contact information fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillContactInfo(dataMap) {
    const fieldMappings = [
      { field: 'email', automationIds: ['email', 'emailAddress'] },
      { field: 'phone', automationIds: ['phone-number', 'phoneNumber', 'phone'] },
      { field: 'address', automationIds: ['addressSection_addressLine1', 'address'] },
      { field: 'city', automationIds: ['addressSection_city', 'city'] },
      { field: 'state', automationIds: ['addressSection_region', 'state', 'province'] },
      { field: 'zipCode', automationIds: ['addressSection_postalCode', 'postalCode', 'zip'] },
    ]

    for (const { field, automationIds } of fieldMappings) {
      if (!dataMap[field]) continue

      for (const automationId of automationIds) {
        const input = this.findWorkdayInput(automationId)
        if (input) {
          await this.fillWorkdayField(input, dataMap[field])
          break
        }
      }
    }
  }

  /**
   * Fill work experience section
   * @param {Object} profileData Profile data with experience
   */
  async fillExperience(profileData) {
    // TODO: Handle work experience entries
    // Workday often requires adding experience entries one at a time
    // This would need to click "Add", fill fields, save, repeat

    console.log('[ResuBoost] Work experience section detected - manual entry recommended')

    if (profileData.experience && profileData.experience.length > 0) {
      const exp = profileData.experience[0] // Fill first/most recent

      const titleInput = this.findWorkdayInput('jobTitle')
      if (titleInput && exp.title) {
        await this.fillWorkdayField(titleInput, exp.title)
      }

      const companyInput = this.findWorkdayInput('company')
      if (companyInput && exp.company) {
        await this.fillWorkdayField(companyInput, exp.company)
      }
    }
  }

  /**
   * Fill education section
   * @param {Object} profileData Profile data with education
   */
  async fillEducation(profileData) {
    // TODO: Handle education entries
    console.log('[ResuBoost] Education section detected - manual entry recommended')

    if (profileData.education && profileData.education.length > 0) {
      const edu = profileData.education[0]

      const schoolInput = this.findWorkdayInput('school')
      if (schoolInput && edu.school) {
        await this.fillWorkdayField(schoolInput, edu.school)
      }

      const degreeInput = this.findWorkdayInput('degree')
      if (degreeInput && edu.degree) {
        await this.fillWorkdayField(degreeInput, edu.degree)
      }
    }
  }

  /**
   * Handle resume upload
   * @param {Object} profileData Profile data with resume
   */
  async handleResume(profileData) {
    const uploadButton = document.querySelector([
      '[data-automation-id="file-upload-input-ref"]',
      'input[type="file"]',
      '[data-automation-id="resumeUpload"]',
    ].join(', '))

    if (uploadButton) {
      console.log('[ResuBoost] Resume upload found - manual upload required')
      // TODO: Implement file upload via DataTransfer API
    }

    // Check for "Use LinkedIn" or "Use existing resume" options
    const importOptions = document.querySelectorAll([
      '[data-automation-id="linkedInImport"]',
      '[data-automation-id="parseResumeButton"]',
    ].join(', '))

    if (importOptions.length > 0) {
      console.log('[ResuBoost] Resume import options available')
    }
  }

  /**
   * Fill custom screening questions
   * @param {Object} dataMap Mapped profile data
   * @param {Object} profileData Full profile data
   */
  async fillCustomQuestions(dataMap, profileData) {
    const questionContainers = document.querySelectorAll([
      '[data-automation-id="questionItem"]',
      '.wd-FormInputComponent',
      '[data-automation-id^="formField"]',
    ].join(', '))

    for (const container of questionContainers) {
      const labelElement = container.querySelector('label, [data-automation-id="formLabel"]')
      const labelText = (labelElement?.textContent || '').toLowerCase()

      // Find input within container
      const input = container.querySelector('input, select, textarea')
      if (!input) continue

      // Match and fill based on label
      if (this.matchesPattern(labelText, ['years', 'experience'])) {
        if (dataMap.yearsExperience) {
          await this.fillWorkdayField(input, dataMap.yearsExperience.toString())
        }
      } else if (this.matchesPattern(labelText, ['salary', 'compensation'])) {
        if (dataMap.salary) {
          await this.fillWorkdayField(input, dataMap.salary.toString())
        }
      } else if (this.matchesPattern(labelText, ['authorized', 'eligible', 'legally'])) {
        await this.fillYesNoField(container, profileData.workAuthorization !== false)
      } else if (this.matchesPattern(labelText, ['sponsorship', 'visa'])) {
        await this.fillYesNoField(container, profileData.requiresSponsorship === true)
      } else if (this.matchesPattern(labelText, ['linkedin'])) {
        if (dataMap.linkedIn) {
          await this.fillWorkdayField(input, dataMap.linkedIn)
        }
      }
    }
  }

  /**
   * Fill all visible fields (fallback)
   * @param {Object} dataMap Mapped profile data
   * @param {Object} profileData Full profile data
   */
  async fillAllVisibleFields(dataMap, profileData) {
    await this.fillPersonalInfo(dataMap)
    await this.fillContactInfo(dataMap)
    await this.fillCustomQuestions(dataMap, profileData)
  }

  /**
   * Find Workday input by automation ID
   * @param {string} automationId Workday automation ID
   * @returns {HTMLElement|null} Input element
   */
  findWorkdayInput(automationId) {
    // Try exact match first
    let input = document.querySelector(`[data-automation-id="${automationId}"]`)
    if (input) return input

    // Try partial match
    input = document.querySelector(`[data-automation-id*="${automationId}"]`)
    if (input) return input

    // Try by name
    input = document.querySelector(`input[name*="${automationId}"], select[name*="${automationId}"]`)
    if (input) return input

    return null
  }

  /**
   * Fill a Workday field with proper event handling
   * @param {HTMLElement} input Input element
   * @param {string} value Value to fill
   */
  async fillWorkdayField(input, value) {
    if (!input || !value) return

    // Workday uses custom components, need to handle specially
    const isWorkdayDropdown = input.closest('[data-automation-id*="dropdown"]') !== null

    if (isWorkdayDropdown || input.tagName === 'SELECT') {
      await this.fillWorkdayDropdown(input, value)
    } else {
      // Clear existing value
      input.focus()
      input.value = ''

      // Set new value
      input.value = value

      // Trigger events in order Workday expects
      input.dispatchEvent(new Event('input', { bubbles: true }))
      input.dispatchEvent(new Event('change', { bubbles: true }))

      // Workday often uses blur to validate
      input.dispatchEvent(new Event('blur', { bubbles: true }))

      this.filledFields.push({ name: input.name || input.getAttribute('data-automation-id'), type: 'text' })
    }
  }

  /**
   * Fill Workday dropdown/select
   * @param {HTMLElement} element Dropdown element
   * @param {string} value Value to select
   */
  async fillWorkdayDropdown(element, value) {
    // Workday dropdowns are often custom components
    // Click to open dropdown
    element.click()

    // Wait for dropdown to open
    await new Promise((resolve) => setTimeout(resolve, 200))

    // Find options
    const options = document.querySelectorAll([
      '[data-automation-id*="promptOption"]',
      '[role="option"]',
      '.wd-ListItem',
    ].join(', '))

    const valueLower = value.toLowerCase()

    for (const option of options) {
      const optionText = (option.textContent || '').toLowerCase()

      if (optionText.includes(valueLower) || valueLower.includes(optionText)) {
        option.click()
        this.filledFields.push({ name: element.name || 'dropdown', type: 'select' })
        return
      }
    }

    // If no match found, close dropdown
    document.body.click()
  }

  /**
   * Fill Yes/No question field
   * @param {HTMLElement} container Question container
   * @param {boolean} value True for Yes, False for No
   */
  async fillYesNoField(container, value) {
    // Check for radio buttons
    const radios = container.querySelectorAll('input[type="radio"]')

    if (radios.length > 0) {
      for (const radio of radios) {
        const label = this.getLabelText(radio).toLowerCase()
        const radioValue = radio.value.toLowerCase()

        const isYes = radioValue === 'yes' || radioValue === '1' || radioValue === 'true' || label.includes('yes')
        const isNo = radioValue === 'no' || radioValue === '0' || radioValue === 'false' || label.includes('no')

        if ((value && isYes) || (!value && isNo)) {
          radio.click()
          this.filledFields.push({ name: radio.name, type: 'radio' })
          return
        }
      }
    }

    // Check for dropdown
    const select = container.querySelector('select')
    if (select) {
      const optionValue = value ? 'yes' : 'no'
      await this.fillSelect(select, optionValue)
    }
  }

  /**
   * Check if text matches patterns
   * @param {string} text Text to check
   * @param {string[]} patterns Patterns to match
   * @returns {boolean} True if matches
   */
  matchesPattern(text, patterns) {
    return patterns.some((pattern) => text.includes(pattern))
  }

  /**
   * Extract job details from Workday job page
   * @returns {Object} Job details
   */
  extractJobDetails() {
    return {
      title: this.extractText([
        '[data-automation-id="jobPostingHeader"]',
        '.css-1q2dra3 h2',
        '[data-automation-id="jobTitle"]',
      ]),
      company: this.extractText([
        '[data-automation-id="companyName"]',
        '.css-1q2dra3 .company',
      ]),
      location: this.extractText([
        '[data-automation-id="locations"]',
        '[data-automation-id="jobPostingLocation"]',
        '.locations',
      ]),
      description: this.extractText([
        '[data-automation-id="jobPostingDescription"]',
        '.job-description',
      ]),
      jobId: this.extractText([
        '[data-automation-id="jobReqId"]',
        '[data-automation-id="jobPostingJobReqId"]',
      ]),
      postedDate: this.extractText([
        '[data-automation-id="postedOn"]',
        '[data-automation-id="jobPostingDate"]',
      ]),
    }
  }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.WorkdayFiller = WorkdayFiller
}
