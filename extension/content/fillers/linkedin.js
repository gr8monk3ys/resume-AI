/**
 * LinkedIn Form Filler
 * Handles LinkedIn Easy Apply and job application forms
 *
 * LinkedIn Easy Apply forms are multi-step modals with various field types:
 * - Contact info (often pre-filled from LinkedIn profile)
 * - Resume/document upload
 * - Custom screening questions (text, select, radio, checkbox)
 * - Work authorization questions
 * - Education and experience sections
 */

class LinkedInFiller extends GenericFiller {
  constructor() {
    super()
    this.platform = 'linkedin'
    // Track current step in multi-step forms
    this.currentStep = 0
    this.totalSteps = 0
  }

  /**
   * LinkedIn-specific selectors organized by category
   * These selectors target LinkedIn's Easy Apply modal elements
   */
  static SELECTORS = {
    // Modal and form containers
    modal: [
      '.jobs-easy-apply-modal',
      '[data-test-modal]',
      '.artdeco-modal--layer-default',
    ],
    form: [
      '.jobs-easy-apply-form-section__grouping',
      '[data-test-form-element]',
      '.fb-dash-form-element',
    ],

    // Contact information fields
    contact: {
      firstName: [
        'input[name="firstName"]',
        '[data-test-single-line-text-input="firstName"]',
        'input[id*="firstName"]',
        '[aria-label*="First name"]',
      ],
      lastName: [
        'input[name="lastName"]',
        '[data-test-single-line-text-input="lastName"]',
        'input[id*="lastName"]',
        '[aria-label*="Last name"]',
      ],
      email: [
        'input[name="email"]',
        '[data-test-single-line-text-input="email"]',
        'input[id*="email"]',
        'input[type="email"]',
        '[aria-label*="Email"]',
      ],
      phone: [
        'input[name="phone"]',
        'input[name="phoneNumber"]',
        '[data-test-single-line-text-input="phone"]',
        'input[id*="phone"]',
        'input[type="tel"]',
        '[aria-label*="Phone"]',
        '[aria-label*="Mobile"]',
      ],
      address: [
        'input[name="address"]',
        'input[id*="address"]',
        '[aria-label*="Address"]',
        '[aria-label*="Street"]',
      ],
      city: [
        'input[name="city"]',
        'input[id*="city"]',
        '[aria-label*="City"]',
        '[data-test-single-line-text-input*="city"]',
      ],
      state: [
        'select[name="state"]',
        'input[name="state"]',
        '[aria-label*="State"]',
        '[aria-label*="Province"]',
      ],
      zipCode: [
        'input[name="zipCode"]',
        'input[name="postalCode"]',
        'input[id*="zip"]',
        '[aria-label*="Postal"]',
        '[aria-label*="ZIP"]',
      ],
    },

    // Resume and document upload
    documents: {
      uploadButton: [
        'button[aria-label*="Upload resume"]',
        'button[aria-label*="Upload CV"]',
        '[data-test-document-upload-button]',
        '.jobs-document-upload__button',
        'button.jobs-document-upload-redesign-card__upload-button',
      ],
      fileInput: [
        'input[type="file"][name*="resume"]',
        'input[type="file"][name*="document"]',
        '.jobs-document-upload input[type="file"]',
      ],
      previousResume: [
        '.jobs-document-upload__container input[type="radio"]',
        '[data-test-document-select]',
        '.jobs-document-upload-redesign-card__container input[type="radio"]',
      ],
      coverLetterText: [
        'textarea[name*="coverLetter"]',
        '[aria-label*="cover letter"]',
        '[data-test-text-area="coverLetter"]',
      ],
    },

    // Navigation buttons
    navigation: {
      next: [
        'button[aria-label="Continue to next step"]',
        'button[data-test-easy-apply-next-button]',
        'button[data-easy-apply-next-button]',
        '.jobs-easy-apply-footer button[aria-label*="Next"]',
        '.artdeco-button--primary:not([aria-label*="Submit"]):not([aria-label*="Review"])',
      ],
      review: [
        'button[aria-label="Review your application"]',
        'button[data-test-easy-apply-review-button]',
        'button[aria-label*="Review"]',
      ],
      submit: [
        'button[aria-label="Submit application"]',
        'button[data-test-easy-apply-submit-button]',
        'button[aria-label*="Submit"]',
      ],
      back: [
        'button[aria-label="Back"]',
        'button[data-test-easy-apply-back-button]',
      ],
    },

    // Progress indicator
    progress: [
      '.jobs-easy-apply-progress',
      '[data-test-progress-bar]',
      '.artdeco-completeness-meter-linear',
    ],

    // Question containers
    questions: {
      container: [
        '.jobs-easy-apply-form-section__grouping',
        '[data-test-form-element]',
        '.fb-dash-form-element',
        '.jobs-easy-apply-form-element',
      ],
      label: [
        'label',
        '.fb-dash-form-element__label',
        '.jobs-easy-apply-form-element__label',
        '.t-14.t-bold',
      ],
      required: [
        '.fb-dash-form-element__required-icon',
        '[aria-required="true"]',
        '.required',
      ],
    },

    // Radio button groups (Yes/No questions)
    radio: {
      group: [
        '[data-test-text-entity-list-form-component]',
        '.fb-text-selectable-option',
        '.jobs-easy-apply-form-section fieldset',
      ],
      option: [
        'input[type="radio"]',
        '.fb-text-selectable-option__option input',
      ],
    },

    // Dropdown/Select fields
    dropdown: {
      trigger: [
        'button[data-test-dropdown-trigger]',
        '.artdeco-dropdown__trigger',
        'select',
      ],
      option: [
        '[data-test-dropdown-option]',
        '.artdeco-dropdown__item',
        'option',
      ],
    },

    // Experience and education sections
    experience: {
      addButton: [
        'button[aria-label*="Add work experience"]',
        'button[aria-label*="Add position"]',
        '[data-test-add-work-experience]',
      ],
      title: [
        'input[name*="title"]',
        '[aria-label*="Title"]',
        '[data-test-single-line-text-input*="title"]',
      ],
      company: [
        'input[name*="company"]',
        '[aria-label*="Company"]',
        '[data-test-single-line-text-input*="company"]',
      ],
      startDate: [
        'input[name*="startDate"]',
        '[aria-label*="Start date"]',
      ],
      endDate: [
        'input[name*="endDate"]',
        '[aria-label*="End date"]',
      ],
      current: [
        'input[type="checkbox"][name*="current"]',
        '[aria-label*="current"]',
      ],
    },

    education: {
      addButton: [
        'button[aria-label*="Add education"]',
        '[data-test-add-education]',
      ],
      school: [
        'input[name*="school"]',
        '[aria-label*="School"]',
        '[data-test-single-line-text-input*="school"]',
      ],
      degree: [
        'input[name*="degree"]',
        'select[name*="degree"]',
        '[aria-label*="Degree"]',
      ],
      field: [
        'input[name*="field"]',
        '[aria-label*="Field of study"]',
      ],
      graduationDate: [
        'input[name*="graduation"]',
        '[aria-label*="Graduation"]',
      ],
    },
  }

  /**
   * Fill LinkedIn application form
   * @param {Object} profileData User profile data
   * @returns {Object} Result with filled fields and any errors
   */
  async fill(profileData) {
    this.filledFields = []
    this.errors = []

    try {
      const dataMap = this.mapProfileData(profileData)

      // Detect if we're in Easy Apply modal
      const isEasyApply = this.isEasyApplyModal()
      console.log(`[ResuBoost] LinkedIn Easy Apply modal detected: ${isEasyApply}`)

      // Get current step info
      this.detectCurrentStep()

      // Fill fields based on what's visible on current step
      await this.fillVisibleFields(dataMap, profileData)

      // Log success
      console.log(`[ResuBoost] Filled ${this.filledFields.length} fields on LinkedIn`)

      return {
        success: true,
        filledFields: this.filledFields,
        errors: this.errors,
        currentStep: this.currentStep,
        totalSteps: this.totalSteps,
      }
    } catch (error) {
      console.error('[ResuBoost] LinkedIn fill error:', error)
      this.errors.push({ type: 'general', message: error.message })
      return {
        success: false,
        filledFields: this.filledFields,
        errors: this.errors,
      }
    }
  }

  /**
   * Check if Easy Apply modal is open
   * @returns {boolean} True if modal is present
   */
  isEasyApplyModal() {
    return LinkedInFiller.SELECTORS.modal.some(
      (selector) => document.querySelector(selector) !== null
    )
  }

  /**
   * Detect current step in multi-step form
   */
  detectCurrentStep() {
    try {
      // Look for progress indicator
      const progressBar = document.querySelector(
        LinkedInFiller.SELECTORS.progress.join(', ')
      )

      if (progressBar) {
        // Try to extract step info from progress bar
        const progressText = progressBar.textContent || ''
        const stepMatch = progressText.match(/(\d+)\s*(?:of|\/)\s*(\d+)/i)

        if (stepMatch) {
          this.currentStep = parseInt(stepMatch[1], 10)
          this.totalSteps = parseInt(stepMatch[2], 10)
          console.log(`[ResuBoost] LinkedIn step ${this.currentStep} of ${this.totalSteps}`)
        }
      }

      // Also check aria-valuenow on progress meter
      const meter = document.querySelector('[role="progressbar"]')
      if (meter) {
        const value = meter.getAttribute('aria-valuenow')
        const max = meter.getAttribute('aria-valuemax')
        if (value && max) {
          console.log(`[ResuBoost] Progress: ${value}/${max}`)
        }
      }
    } catch (error) {
      console.warn('[ResuBoost] Could not detect step:', error)
    }
  }

  /**
   * Fill all visible fields on current step
   * @param {Object} dataMap Mapped profile data
   * @param {Object} profileData Full profile data
   */
  async fillVisibleFields(dataMap, profileData) {
    // Fill contact information
    await this.fillContactInfo(dataMap)

    // Handle resume upload section
    await this.handleResumeUpload(profileData)

    // Fill cover letter if present
    await this.fillCoverLetter(profileData)

    // Fill additional screening questions
    await this.fillAdditionalQuestions(dataMap, profileData)

    // Fill work authorization questions
    await this.fillWorkAuthQuestions(profileData)

    // Fill experience if visible
    await this.fillExperienceSection(profileData)

    // Fill education if visible
    await this.fillEducationSection(profileData)
  }

  /**
   * Fill contact information fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillContactInfo(dataMap) {
    const contactFields = LinkedInFiller.SELECTORS.contact

    for (const [field, selectors] of Object.entries(contactFields)) {
      if (!dataMap[field]) continue

      try {
        const input = this.findElement(selectors)
        if (input && !input.disabled && !input.readOnly) {
          // Check if field already has correct value
          if (input.value !== dataMap[field]) {
            await this.fillField(input, dataMap[field])
            console.log(`[ResuBoost] Filled contact field: ${field}`)
          }
        }
      } catch (error) {
        this.errors.push({ type: 'contact', field, message: error.message })
        console.warn(`[ResuBoost] Could not fill ${field}:`, error)
      }
    }
  }

  /**
   * Handle resume file upload section
   * @param {Object} profileData Profile data with resume info
   */
  async handleResumeUpload(profileData) {
    try {
      const docSelectors = LinkedInFiller.SELECTORS.documents

      // First, check for previously uploaded resume option
      const previousResumeRadio = this.findElement(docSelectors.previousResume)
      if (previousResumeRadio && !previousResumeRadio.checked) {
        // Select the first/most recent resume
        previousResumeRadio.click()
        await this.delay(200)
        this.filledFields.push({ name: 'resume', type: 'select_existing' })
        console.log('[ResuBoost] Selected existing resume')
        return
      }

      // Check for file input for new upload
      const fileInput = this.findElement(docSelectors.fileInput)
      if (fileInput && profileData.resumeFile) {
        // Note: Actual file upload requires DataTransfer API
        console.log('[ResuBoost] Resume file input found - manual upload may be required')
        this.filledFields.push({ name: 'resume', type: 'file_input_found' })
      }

      // Check for upload button
      const uploadButton = this.findElement(docSelectors.uploadButton)
      if (uploadButton) {
        console.log('[ResuBoost] Resume upload button found')
        // Don't auto-click - user needs to select file manually
      }
    } catch (error) {
      this.errors.push({ type: 'resume', message: error.message })
      console.warn('[ResuBoost] Resume upload handling error:', error)
    }
  }

  /**
   * Fill cover letter text area if present
   * @param {Object} profileData Profile data with cover letter
   */
  async fillCoverLetter(profileData) {
    if (!profileData.coverLetter) return

    try {
      const textarea = this.findElement(LinkedInFiller.SELECTORS.documents.coverLetterText)
      if (textarea && !textarea.value) {
        await this.fillField(textarea, profileData.coverLetter)
        console.log('[ResuBoost] Filled cover letter')
      }
    } catch (error) {
      this.errors.push({ type: 'coverLetter', message: error.message })
      console.warn('[ResuBoost] Cover letter fill error:', error)
    }
  }

  /**
   * Fill additional screening questions
   * @param {Object} dataMap Mapped profile data
   * @param {Object} profileData Full profile data
   */
  async fillAdditionalQuestions(dataMap, profileData) {
    try {
      const questionContainers = document.querySelectorAll(
        LinkedInFiller.SELECTORS.questions.container.join(', ')
      )

      for (const container of questionContainers) {
        await this.fillQuestionContainer(container, dataMap, profileData)
      }
    } catch (error) {
      this.errors.push({ type: 'questions', message: error.message })
      console.warn('[ResuBoost] Questions fill error:', error)
    }
  }

  /**
   * Fill a single question container based on its type
   * @param {HTMLElement} container Question container
   * @param {Object} dataMap Mapped profile data
   * @param {Object} profileData Full profile data
   */
  async fillQuestionContainer(container, dataMap, profileData) {
    const labelElement = container.querySelector(
      LinkedInFiller.SELECTORS.questions.label.join(', ')
    )
    const labelText = (labelElement?.textContent || '').toLowerCase().trim()

    if (!labelText) return

    // Skip if already processed
    if (container.dataset.resuboostFilled === 'true') return

    // Determine field type and fill accordingly
    const input = container.querySelector('input[type="text"], input[type="number"], input[type="url"]')
    const select = container.querySelector('select')
    const textarea = container.querySelector('textarea')
    const radioGroup = container.querySelectorAll('input[type="radio"]')

    try {
      // Years of experience
      if (this.matchesPattern(labelText, ['years', 'experience', 'how many years', 'how long'])) {
        if (input && dataMap.yearsExperience) {
          await this.fillField(input, dataMap.yearsExperience.toString())
          container.dataset.resuboostFilled = 'true'
        } else if (select && dataMap.yearsExperience) {
          await this.fillSelectByValue(select, dataMap.yearsExperience.toString())
          container.dataset.resuboostFilled = 'true'
        }
      }
      // LinkedIn profile
      else if (this.matchesPattern(labelText, ['linkedin', 'profile url'])) {
        if (input && dataMap.linkedIn) {
          await this.fillField(input, dataMap.linkedIn)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Website/Portfolio
      else if (this.matchesPattern(labelText, ['website', 'portfolio', 'personal site'])) {
        if (input && dataMap.website) {
          await this.fillField(input, dataMap.website)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // GitHub
      else if (this.matchesPattern(labelText, ['github'])) {
        if (input && dataMap.github) {
          await this.fillField(input, dataMap.github)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Salary expectations
      else if (this.matchesPattern(labelText, ['salary', 'compensation', 'pay', 'rate'])) {
        if (input && dataMap.salary) {
          await this.fillField(input, dataMap.salary.toString())
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Start date / Availability
      else if (this.matchesPattern(labelText, ['start date', 'when can you', 'available', 'notice period'])) {
        if (input && profileData.availableDate) {
          await this.fillField(input, profileData.availableDate)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Location / City
      else if (this.matchesPattern(labelText, ['current location', 'where are you', 'city'])) {
        const location = this.formatLocation(dataMap)
        if (input && location) {
          await this.fillField(input, location)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // How did you hear about us
      else if (this.matchesPattern(labelText, ['how did you hear', 'source', 'find out', 'referred'])) {
        if (select) {
          await this.selectFirstValidOption(select)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Generic text questions - try to match with answer templates
      else if (textarea) {
        const answer = this.findAnswerTemplate(labelText, profileData.answerTemplates)
        if (answer) {
          await this.fillField(textarea, answer)
          container.dataset.resuboostFilled = 'true'
        }
      }
    } catch (error) {
      console.warn(`[ResuBoost] Could not fill question "${labelText}":`, error)
    }
  }

  /**
   * Fill work authorization and sponsorship questions
   * @param {Object} profileData Profile data with authorization info
   */
  async fillWorkAuthQuestions(profileData) {
    try {
      const radioGroups = document.querySelectorAll(
        LinkedInFiller.SELECTORS.radio.group.join(', ')
      )

      for (const group of radioGroups) {
        const groupText = (group.textContent || '').toLowerCase()
        const radios = group.querySelectorAll('input[type="radio"]')

        if (radios.length === 0) continue

        // Work authorization question
        if (this.matchesPattern(groupText, ['authorized to work', 'legally authorized', 'eligible to work', 'work in the', 'right to work'])) {
          await this.selectYesNoRadio(radios, profileData.workAuthorization !== false)
          console.log('[ResuBoost] Filled work authorization question')
        }
        // Sponsorship requirement
        else if (this.matchesPattern(groupText, ['sponsorship', 'visa', 'require sponsorship', 'need sponsorship'])) {
          await this.selectYesNoRadio(radios, profileData.requiresSponsorship === true)
          console.log('[ResuBoost] Filled sponsorship question')
        }
        // Remote work preference
        else if (this.matchesPattern(groupText, ['remote', 'work from home', 'on-site', 'hybrid'])) {
          if (profileData.openToRemote !== undefined) {
            await this.selectYesNoRadio(radios, profileData.openToRemote)
            console.log('[ResuBoost] Filled remote work question')
          }
        }
        // Relocation
        else if (this.matchesPattern(groupText, ['relocate', 'willing to move', 'relocation'])) {
          if (profileData.willingToRelocate !== undefined) {
            await this.selectYesNoRadio(radios, profileData.willingToRelocate)
            console.log('[ResuBoost] Filled relocation question')
          }
        }
        // Background check consent
        else if (this.matchesPattern(groupText, ['background check', 'consent to'])) {
          // Typically should be yes for job applications
          await this.selectYesNoRadio(radios, true)
          console.log('[ResuBoost] Filled background check consent')
        }
        // Drug test
        else if (this.matchesPattern(groupText, ['drug test', 'drug screen'])) {
          await this.selectYesNoRadio(radios, true)
          console.log('[ResuBoost] Filled drug test question')
        }
        // 18+ years old
        else if (this.matchesPattern(groupText, ['18 years', 'age', 'legally of age'])) {
          await this.selectYesNoRadio(radios, true)
          console.log('[ResuBoost] Filled age verification')
        }
      }
    } catch (error) {
      this.errors.push({ type: 'workAuth', message: error.message })
      console.warn('[ResuBoost] Work auth questions error:', error)
    }
  }

  /**
   * Select Yes or No radio button
   * @param {NodeList} radios Radio button elements
   * @param {boolean} selectYes True to select Yes, false for No
   */
  async selectYesNoRadio(radios, selectYes) {
    for (const radio of radios) {
      const labelText = this.getLabelText(radio).toLowerCase()
      const radioValue = (radio.value || '').toLowerCase()

      const isYes = radioValue === 'yes' ||
                    radioValue === 'true' ||
                    radioValue === '1' ||
                    labelText.includes('yes')

      const isNo = radioValue === 'no' ||
                   radioValue === 'false' ||
                   radioValue === '0' ||
                   labelText.includes('no')

      if ((selectYes && isYes) || (!selectYes && isNo)) {
        if (!radio.checked) {
          radio.click()
          await this.delay(100)
          this.filledFields.push({ name: radio.name || 'radio', type: 'radio' })
        }
        return
      }
    }
  }

  /**
   * Fill experience section if visible
   * @param {Object} profileData Profile data with experience
   */
  async fillExperienceSection(profileData) {
    if (!profileData.experience || profileData.experience.length === 0) return

    try {
      const expSelectors = LinkedInFiller.SELECTORS.experience

      // Check if experience section is visible
      const titleInput = this.findElement(expSelectors.title)
      const companyInput = this.findElement(expSelectors.company)

      if (titleInput || companyInput) {
        const exp = profileData.experience[0] // Most recent

        if (titleInput && exp.title) {
          await this.fillField(titleInput, exp.title)
        }
        if (companyInput && exp.company) {
          await this.fillField(companyInput, exp.company)
        }

        console.log('[ResuBoost] Filled experience section')
      }
    } catch (error) {
      this.errors.push({ type: 'experience', message: error.message })
      console.warn('[ResuBoost] Experience section error:', error)
    }
  }

  /**
   * Fill education section if visible
   * @param {Object} profileData Profile data with education
   */
  async fillEducationSection(profileData) {
    if (!profileData.education || profileData.education.length === 0) return

    try {
      const eduSelectors = LinkedInFiller.SELECTORS.education

      // Check if education section is visible
      const schoolInput = this.findElement(eduSelectors.school)
      const degreeInput = this.findElement(eduSelectors.degree)

      if (schoolInput || degreeInput) {
        const edu = profileData.education[0] // Most recent

        if (schoolInput && edu.school) {
          await this.fillField(schoolInput, edu.school)
        }
        if (degreeInput && edu.degree) {
          if (degreeInput.tagName === 'SELECT') {
            await this.fillSelect(degreeInput, edu.degree)
          } else {
            await this.fillField(degreeInput, edu.degree)
          }
        }

        const fieldInput = this.findElement(eduSelectors.field)
        if (fieldInput && edu.field) {
          await this.fillField(fieldInput, edu.field)
        }

        console.log('[ResuBoost] Filled education section')
      }
    } catch (error) {
      this.errors.push({ type: 'education', message: error.message })
      console.warn('[ResuBoost] Education section error:', error)
    }
  }

  /**
   * Find first matching element from array of selectors
   * @param {string[]} selectors CSS selectors to try
   * @returns {HTMLElement|null} First matching element
   */
  findElement(selectors) {
    if (!Array.isArray(selectors)) {
      return document.querySelector(selectors)
    }

    for (const selector of selectors) {
      try {
        const element = document.querySelector(selector)
        if (element) return element
      } catch (e) {
        continue
      }
    }
    return null
  }

  /**
   * Fill select dropdown by matching value
   * @param {HTMLSelectElement} select Select element
   * @param {string} value Value to match
   */
  async fillSelectByValue(select, value) {
    const valueLower = value.toLowerCase()

    for (const option of select.options) {
      const optionText = (option.text || '').toLowerCase()
      const optionValue = (option.value || '').toLowerCase()

      // Try exact match first
      if (optionValue === valueLower || optionText === valueLower) {
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        this.filledFields.push({ name: select.name || select.id, type: 'select' })
        return
      }

      // Try partial match for ranges like "3-5 years"
      if (optionText.includes(valueLower) || valueLower.includes(optionText)) {
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        this.filledFields.push({ name: select.name || select.id, type: 'select' })
        return
      }

      // Handle numeric ranges
      const numValue = parseInt(value, 10)
      if (!isNaN(numValue)) {
        const rangeMatch = optionText.match(/(\d+)\s*[-to]+\s*(\d+)/)
        if (rangeMatch) {
          const min = parseInt(rangeMatch[1], 10)
          const max = parseInt(rangeMatch[2], 10)
          if (numValue >= min && numValue <= max) {
            select.value = option.value
            select.dispatchEvent(new Event('change', { bubbles: true }))
            this.filledFields.push({ name: select.name || select.id, type: 'select' })
            return
          }
        }
      }
    }
  }

  /**
   * Select first valid (non-placeholder) option
   * @param {HTMLSelectElement} select Select element
   */
  async selectFirstValidOption(select) {
    for (let i = 0; i < select.options.length; i++) {
      const option = select.options[i]
      if (option.value && option.value !== '' && !option.disabled) {
        // Skip common placeholder texts
        const text = option.text.toLowerCase()
        if (text.includes('select') || text.includes('choose') || text === '') {
          continue
        }
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        this.filledFields.push({ name: select.name || select.id, type: 'select' })
        return
      }
    }
  }

  /**
   * Format location string from data map
   * @param {Object} dataMap Data map with location fields
   * @returns {string} Formatted location
   */
  formatLocation(dataMap) {
    const parts = [dataMap.city, dataMap.state, dataMap.country].filter(Boolean)
    return parts.join(', ')
  }

  /**
   * Find matching answer template for a question
   * @param {string} questionText Question text
   * @param {Object} templates Answer templates from profile
   * @returns {string|null} Matching answer or null
   */
  findAnswerTemplate(questionText, templates) {
    if (!templates) return null

    // Check for keyword matches in templates
    for (const [keyword, answer] of Object.entries(templates)) {
      if (questionText.includes(keyword.toLowerCase())) {
        return answer
      }
    }
    return null
  }

  /**
   * Check if text matches any of the patterns
   * @param {string} text Text to check
   * @param {string[]} patterns Patterns to match
   * @returns {boolean} True if any pattern matches
   */
  matchesPattern(text, patterns) {
    return patterns.some((pattern) => text.includes(pattern.toLowerCase()))
  }

  /**
   * Utility delay function
   * @param {number} ms Milliseconds to wait
   */
  delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }

  /**
   * Click next button to proceed to next step
   * @returns {boolean} True if next button was clicked
   */
  async clickNextButton() {
    try {
      const nextButton = this.findElement(LinkedInFiller.SELECTORS.navigation.next)
      if (nextButton && !nextButton.disabled) {
        nextButton.click()
        await this.delay(500) // Wait for page transition
        return true
      }
    } catch (error) {
      console.warn('[ResuBoost] Could not click next:', error)
    }
    return false
  }

  /**
   * Check if we're on the review step
   * @returns {boolean} True if on review step
   */
  isReviewStep() {
    return !!this.findElement(LinkedInFiller.SELECTORS.navigation.submit)
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
        '.topcard__title',
        '.job-view-layout h1',
      ]),
      company: this.extractText([
        '.job-details-jobs-unified-top-card__company-name',
        '.jobs-unified-top-card__company-name',
        '.jobs-details__main-company-name',
        '.topcard__org-name-link',
        '.jobs-company__name',
      ]),
      location: this.extractText([
        '.job-details-jobs-unified-top-card__bullet',
        '.jobs-unified-top-card__bullet',
        '.jobs-details__main-location',
        '.topcard__flavor--bullet',
      ]),
      description: this.extractText([
        '.jobs-description__content',
        '.jobs-box__html-content',
        '#job-details',
        '.jobs-description-content__text',
        '.description__text',
      ]),
      postedDate: this.extractText([
        '.jobs-unified-top-card__posted-date',
        '.job-details-jobs-unified-top-card__primary-description-without-tagline',
        '.posted-time-ago__text',
      ]),
      applicants: this.extractText([
        '.jobs-unified-top-card__applicant-count',
        '.num-applicants__caption',
      ]),
      salary: this.extractText([
        '.job-details-jobs-unified-top-card__job-insight',
        '.compensation__salary',
      ]),
      jobType: this.extractText([
        '.jobs-unified-top-card__workplace-type',
        '.workplace-type',
      ]),
    }
  }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.LinkedInFiller = LinkedInFiller
}
