/**
 * Lever Form Filler
 * Handles Lever ATS job application forms
 */

class LeverFiller extends GenericFiller {
  constructor() {
    super()
    this.platform = 'lever'
  }

  /**
   * Fill Lever application form
   * @param {Object} profileData User profile data
   * @returns {Object} Result with filled fields
   */
  async fill(profileData) {
    this.filledFields = []
    const dataMap = this.mapProfileData(profileData)

    // Lever forms have a specific structure
    // with main fields and custom questions

    // Main application fields
    await this.fillMainFields(dataMap)

    // Resume upload
    await this.handleResume(profileData)

    // Links section
    await this.fillLinks(dataMap)

    // Additional information (custom questions)
    await this.fillAdditionalInfo(dataMap, profileData)

    return {
      success: true,
      filledFields: this.filledFields,
    }
  }

  /**
   * Fill main application fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillMainFields(dataMap) {
    // Lever uses specific input names
    const fieldMappings = [
      {
        field: 'fullName',
        selectors: ['input[name="name"]', '#name', '[data-qa="name-input"]'],
        value: `${dataMap.firstName} ${dataMap.lastName}`.trim(),
      },
      {
        field: 'email',
        selectors: ['input[name="email"]', '#email', '[data-qa="email-input"]'],
        value: dataMap.email,
      },
      {
        field: 'phone',
        selectors: ['input[name="phone"]', '#phone', '[data-qa="phone-input"]'],
        value: dataMap.phone,
      },
      {
        field: 'currentCompany',
        selectors: ['input[name="org"]', '#org', '[data-qa="org-input"]'],
        value: dataMap.currentCompany,
      },
    ]

    for (const { field, selectors, value } of fieldMappings) {
      if (!value) continue

      for (const selector of selectors) {
        const input = document.querySelector(selector)
        if (input) {
          await this.fillField(input, value)
          break
        }
      }
    }
  }

  /**
   * Handle resume upload
   * @param {Object} profileData Profile data with resume info
   */
  async handleResume(profileData) {
    // Lever's resume upload section
    const resumeSection = document.querySelector('.application-resume, [data-qa="resume-section"]')

    if (!resumeSection) return

    // Check for file input
    const fileInput = resumeSection.querySelector('input[type="file"]')

    if (fileInput) {
      console.log('[ResuBoost] Resume file input found')
      // TODO: Implement actual file upload via DataTransfer API
    }

    // Check for LinkedIn import button (Lever often has this)
    const linkedInImport = resumeSection.querySelector('[data-source="linkedin"], .resume-import-linkedin')

    if (linkedInImport) {
      console.log('[ResuBoost] LinkedIn import option available')
    }

    // Paste resume text if textarea is available
    const resumeText = resumeSection.querySelector('textarea')

    if (resumeText && profileData.resumeText) {
      await this.fillField(resumeText, profileData.resumeText)
    }
  }

  /**
   * Fill link fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillLinks(dataMap) {
    // Lever's links section
    const linksSection = document.querySelector('.application-urls, [data-qa="urls-section"]')

    if (!linksSection) {
      // Try individual link inputs
      await this.fillIndividualLinks(dataMap)
      return
    }

    // Get all link inputs in the section
    const linkInputs = linksSection.querySelectorAll('input[type="url"], input[type="text"]')

    const linksToFill = [
      dataMap.linkedIn,
      dataMap.website,
      dataMap.github,
    ].filter(Boolean)

    for (let i = 0; i < Math.min(linkInputs.length, linksToFill.length); i++) {
      await this.fillField(linkInputs[i], linksToFill[i])
    }

    // Click "Add another link" if we have more links
    if (linksToFill.length > linkInputs.length) {
      const addButton = linksSection.querySelector('[data-qa="add-url"], .add-url-button, button:contains("Add")')

      if (addButton) {
        // TODO: Handle dynamic link addition
        console.log('[ResuBoost] Additional links available but not filled')
      }
    }
  }

  /**
   * Fill individual link inputs (when not in a links section)
   * @param {Object} dataMap Mapped profile data
   */
  async fillIndividualLinks(dataMap) {
    const linkMappings = [
      {
        field: 'linkedIn',
        selectors: [
          'input[name*="linkedin"]',
          'input[placeholder*="LinkedIn"]',
          '[data-qa="linkedin-input"]',
        ],
      },
      {
        field: 'website',
        selectors: [
          'input[name*="portfolio"]',
          'input[name*="website"]',
          'input[placeholder*="Portfolio"]',
          '[data-qa="portfolio-input"]',
        ],
      },
      {
        field: 'github',
        selectors: [
          'input[name*="github"]',
          'input[placeholder*="GitHub"]',
          '[data-qa="github-input"]',
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
   * Fill additional information and custom questions
   * @param {Object} dataMap Mapped profile data
   * @param {Object} profileData Full profile data
   */
  async fillAdditionalInfo(dataMap, profileData) {
    // Get all question groups
    const questionGroups = document.querySelectorAll([
      '.application-question',
      '[data-qa="custom-question"]',
      '.additional-information .application-field',
    ].join(', '))

    for (const group of questionGroups) {
      const label = group.querySelector('label, .label')
      const labelText = (label?.textContent || '').toLowerCase()

      // Handle different question types
      if (this.hasTextInput(group)) {
        await this.fillTextQuestion(group, labelText, dataMap, profileData)
      } else if (this.hasSelect(group)) {
        await this.fillSelectQuestion(group, labelText, profileData)
      } else if (this.hasRadio(group)) {
        await this.fillRadioQuestion(group, labelText, profileData)
      } else if (this.hasCheckbox(group)) {
        await this.fillCheckboxQuestion(group, labelText, profileData)
      } else if (this.hasTextarea(group)) {
        await this.fillTextareaQuestion(group, labelText, profileData)
      }
    }
  }

  /**
   * Check if group has text input
   * @param {HTMLElement} group Question group
   * @returns {boolean} True if has text input
   */
  hasTextInput(group) {
    return !!group.querySelector('input[type="text"], input[type="number"], input[type="url"]')
  }

  /**
   * Check if group has select
   * @param {HTMLElement} group Question group
   * @returns {boolean} True if has select
   */
  hasSelect(group) {
    return !!group.querySelector('select')
  }

  /**
   * Check if group has radio buttons
   * @param {HTMLElement} group Question group
   * @returns {boolean} True if has radio
   */
  hasRadio(group) {
    return !!group.querySelector('input[type="radio"]')
  }

  /**
   * Check if group has checkbox
   * @param {HTMLElement} group Question group
   * @returns {boolean} True if has checkbox
   */
  hasCheckbox(group) {
    return !!group.querySelector('input[type="checkbox"]')
  }

  /**
   * Check if group has textarea
   * @param {HTMLElement} group Question group
   * @returns {boolean} True if has textarea
   */
  hasTextarea(group) {
    return !!group.querySelector('textarea')
  }

  /**
   * Fill text input question
   * @param {HTMLElement} group Question group
   * @param {string} labelText Label text
   * @param {Object} dataMap Mapped data
   * @param {Object} profileData Full profile data
   */
  async fillTextQuestion(group, labelText, dataMap, profileData) {
    const input = group.querySelector('input[type="text"], input[type="number"], input[type="url"]')
    if (!input) return

    // Years of experience
    if (this.matchesPattern(labelText, ['years', 'experience'])) {
      if (dataMap.yearsExperience) {
        await this.fillField(input, dataMap.yearsExperience.toString())
      }
    }
    // Salary expectations
    else if (this.matchesPattern(labelText, ['salary', 'compensation'])) {
      if (dataMap.salary) {
        await this.fillField(input, dataMap.salary.toString())
      }
    }
    // Location
    else if (this.matchesPattern(labelText, ['location', 'city', 'where are you'])) {
      const location = `${dataMap.city}${dataMap.state ? ', ' + dataMap.state : ''}`
      if (location.trim()) {
        await this.fillField(input, location)
      }
    }
    // Start date
    else if (this.matchesPattern(labelText, ['start', 'available', 'when'])) {
      if (profileData.availableDate) {
        await this.fillField(input, profileData.availableDate)
      }
    }
  }

  /**
   * Fill select question
   * @param {HTMLElement} group Question group
   * @param {string} labelText Label text
   * @param {Object} profileData Profile data
   */
  async fillSelectQuestion(group, labelText, profileData) {
    const select = group.querySelector('select')
    if (!select) return

    // How did you hear about us
    if (this.matchesPattern(labelText, ['hear', 'source', 'find'])) {
      await this.selectFirstValidOption(select)
    }
    // Work authorization
    else if (this.matchesPattern(labelText, ['authorized', 'eligible'])) {
      const value = profileData.workAuthorization ? 'yes' : 'no'
      await this.fillSelect(select, value)
    }
  }

  /**
   * Fill radio button question
   * @param {HTMLElement} group Question group
   * @param {string} labelText Label text
   * @param {Object} profileData Profile data
   */
  async fillRadioQuestion(group, labelText, profileData) {
    const radios = group.querySelectorAll('input[type="radio"]')
    if (!radios.length) return

    // Work authorization
    if (this.matchesPattern(labelText, ['authorized', 'eligible', 'legally'])) {
      await this.selectRadioByValue(radios, profileData.workAuthorization !== false)
    }
    // Sponsorship
    else if (this.matchesPattern(labelText, ['sponsorship', 'visa'])) {
      await this.selectRadioByValue(radios, profileData.requiresSponsorship === true)
    }
    // Remote work
    else if (this.matchesPattern(labelText, ['remote', 'work from home', 'hybrid'])) {
      await this.selectRadioByValue(radios, profileData.openToRemote === true)
    }
  }

  /**
   * Select radio by boolean value (Yes/No)
   * @param {NodeList} radios Radio buttons
   * @param {boolean} value Value to select
   */
  async selectRadioByValue(radios, value) {
    for (const radio of radios) {
      const label = this.getLabelText(radio).toLowerCase()
      const radioValue = radio.value.toLowerCase()

      const isYes = radioValue === 'yes' || radioValue === 'true' || label.includes('yes')
      const isNo = radioValue === 'no' || radioValue === 'false' || label.includes('no')

      if ((value && isYes) || (!value && isNo)) {
        radio.click()
        this.filledFields.push({ name: radio.name, type: 'radio' })
        return
      }
    }
  }

  /**
   * Fill checkbox question
   * @param {HTMLElement} group Question group
   * @param {string} labelText Label text
   * @param {Object} profileData Profile data
   */
  async fillCheckboxQuestion(group, labelText, profileData) {
    // Terms and conditions - check if required
    if (this.matchesPattern(labelText, ['agree', 'terms', 'acknowledge', 'consent'])) {
      const checkbox = group.querySelector('input[type="checkbox"]')
      if (checkbox && !checkbox.checked) {
        checkbox.click()
        this.filledFields.push({ name: checkbox.name || 'terms', type: 'checkbox' })
      }
    }
  }

  /**
   * Fill textarea question
   * @param {HTMLElement} group Question group
   * @param {string} labelText Label text
   * @param {Object} profileData Profile data
   */
  async fillTextareaQuestion(group, labelText, profileData) {
    const textarea = group.querySelector('textarea')
    if (!textarea) return

    // Cover letter
    if (this.matchesPattern(labelText, ['cover letter', 'why', 'interested'])) {
      if (profileData.coverLetter) {
        await this.fillField(textarea, profileData.coverLetter)
      }
    }
    // Additional information
    else if (this.matchesPattern(labelText, ['additional', 'anything else', 'comments'])) {
      if (profileData.additionalInfo) {
        await this.fillField(textarea, profileData.additionalInfo)
      }
    }
  }

  /**
   * Select first valid option in dropdown
   * @param {HTMLSelectElement} select Select element
   */
  async selectFirstValidOption(select) {
    for (let i = 0; i < select.options.length; i++) {
      const option = select.options[i]
      if (option.value && !option.disabled && option.value !== '') {
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        this.filledFields.push({ name: select.name || select.id, type: 'select' })
        return
      }
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
   * Extract job details from Lever job page
   * @returns {Object} Job details
   */
  extractJobDetails() {
    return {
      title: this.extractText([
        '.posting-headline h2',
        '.posting-title',
        '[data-qa="posting-name"]',
      ]),
      company: this.extractText([
        '.posting-headline .company-name',
        '.main-header-logo img[alt]',
      ]),
      location: this.extractText([
        '.posting-categories .location',
        '.posting-headline .location',
        '[data-qa="posting-location"]',
      ]),
      description: this.extractText([
        '.posting-description',
        '[data-qa="posting-description"]',
        '.content',
      ]),
      commitment: this.extractText([
        '.posting-categories .commitment',
        '[data-qa="posting-commitment"]',
      ]),
      team: this.extractText([
        '.posting-categories .team',
        '[data-qa="posting-team"]',
      ]),
    }
  }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.LeverFiller = LeverFiller
}
