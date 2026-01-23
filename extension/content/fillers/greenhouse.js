/**
 * Greenhouse Form Filler
 * Handles Greenhouse ATS job application forms
 *
 * Greenhouse forms are typically single-page applications with sections:
 * - Personal information (name, email, phone)
 * - Resume and cover letter upload
 * - Social/professional links
 * - Custom screening questions (varies by employer)
 * - EEOC demographic questions (optional)
 */

class GreenhouseFiller extends GenericFiller {
  constructor() {
    super()
    this.platform = 'greenhouse'
    this.errors = []
  }

  /**
   * Greenhouse-specific selectors organized by category
   * These selectors target Greenhouse's standard form structure
   */
  static SELECTORS = {
    // Form container
    form: [
      '#application-form',
      '.application-form',
      '#main_app_form',
      'form[data-controller="application"]',
    ],

    // Personal information fields
    personal: {
      firstName: [
        '#first_name',
        'input[name="first_name"]',
        'input[id*="first_name"]',
        'input[name*="first"]',
        '[data-qa="first-name-input"]',
        'input[autocomplete="given-name"]',
      ],
      lastName: [
        '#last_name',
        'input[name="last_name"]',
        'input[id*="last_name"]',
        'input[name*="last"]',
        '[data-qa="last-name-input"]',
        'input[autocomplete="family-name"]',
      ],
      email: [
        '#email',
        'input[name="email"]',
        'input[type="email"]',
        '[data-qa="email-input"]',
        'input[autocomplete="email"]',
      ],
      phone: [
        '#phone',
        'input[name="phone"]',
        'input[name="phone_number"]',
        'input[type="tel"]',
        '[data-qa="phone-input"]',
        'input[autocomplete="tel"]',
      ],
      location: [
        '#location',
        'input[name="location"]',
        '[data-qa="location-input"]',
      ],
    },

    // Address fields
    address: {
      street: [
        '#address',
        'input[name="address"]',
        'input[name*="street"]',
        'input[name*="address_line"]',
        'input[autocomplete="street-address"]',
      ],
      city: [
        '#city',
        'input[name="city"]',
        'input[autocomplete="address-level2"]',
      ],
      state: [
        '#state',
        'input[name="state"]',
        'select[name="state"]',
        'input[name*="province"]',
        'input[autocomplete="address-level1"]',
      ],
      zipCode: [
        '#zip',
        'input[name="zip"]',
        'input[name="postal_code"]',
        'input[name*="zip"]',
        'input[autocomplete="postal-code"]',
      ],
      country: [
        '#country',
        'select[name="country"]',
        'input[name="country"]',
        'select[id*="country"]',
      ],
    },

    // Document uploads
    documents: {
      resume: {
        input: [
          'input[type="file"][name*="resume"]',
          'input[type="file"][id*="resume"]',
          'input[type="file"][data-field="resume"]',
          '.resume-upload input[type="file"]',
          '[data-qa="resume-upload"] input[type="file"]',
          'input[type="file"][accept*=".pdf"]',
        ],
        button: [
          'button[aria-label*="resume"]',
          '.resume-upload-btn',
          '[data-qa="resume-upload-btn"]',
        ],
        dropzone: [
          '.resume-dropzone',
          '[data-qa="resume-dropzone"]',
          '.application-dropzone',
        ],
      },
      coverLetter: {
        input: [
          'input[type="file"][name*="cover"]',
          'input[type="file"][id*="cover"]',
          'input[type="file"][data-field="cover_letter"]',
          '.cover-letter-upload input[type="file"]',
        ],
        textarea: [
          'textarea[name*="cover"]',
          '#cover_letter',
          '[data-field="cover_letter_text"] textarea',
          'textarea[id*="cover_letter"]',
          '[data-qa="cover-letter-textarea"]',
        ],
      },
    },

    // Professional links
    links: {
      linkedin: [
        'input[name*="linkedin"]',
        'input[id*="linkedin"]',
        'input[placeholder*="LinkedIn"]',
        'input[placeholder*="linkedin.com"]',
        '[data-qa="linkedin-input"]',
      ],
      website: [
        'input[name*="website"]',
        'input[name*="portfolio"]',
        'input[id*="website"]',
        'input[placeholder*="Website"]',
        'input[placeholder*="Portfolio"]',
        '[data-qa="website-input"]',
      ],
      github: [
        'input[name*="github"]',
        'input[id*="github"]',
        'input[placeholder*="GitHub"]',
        'input[placeholder*="github.com"]',
        '[data-qa="github-input"]',
      ],
      twitter: [
        'input[name*="twitter"]',
        'input[id*="twitter"]',
        'input[placeholder*="Twitter"]',
      ],
    },

    // Question containers
    questions: {
      container: [
        '.field',
        '.application-question',
        '[data-controller="application"] .field',
        '.form-field',
        '.custom-question',
        '[data-qa="custom-question"]',
      ],
      label: [
        'label',
        '.field-label',
        '.form-label',
      ],
      required: [
        '.required',
        '[aria-required="true"]',
        'label .required-asterisk',
      ],
    },

    // Dropdown/Select elements
    dropdown: {
      select: [
        'select',
        '.custom-select',
        '[data-qa="select-input"]',
      ],
      option: [
        'option',
      ],
    },

    // Radio/Checkbox groups
    choice: {
      radioGroup: [
        '.radio-group',
        'fieldset',
        '[role="radiogroup"]',
      ],
      radio: [
        'input[type="radio"]',
      ],
      checkbox: [
        'input[type="checkbox"]',
      ],
      checkboxGroup: [
        '.checkbox-group',
        '[role="group"]',
      ],
    },

    // EEOC/Demographics
    demographics: {
      gender: [
        'select[name*="gender"]',
        '#gender',
        '[data-qa="gender-select"]',
      ],
      ethnicity: [
        'select[name*="race"]',
        'select[name*="ethnicity"]',
        '#ethnicity',
        '[data-qa="ethnicity-select"]',
      ],
      veteran: [
        'select[name*="veteran"]',
        '#veteran_status',
        '[data-qa="veteran-select"]',
      ],
      disability: [
        'select[name*="disability"]',
        '#disability_status',
        '[data-qa="disability-select"]',
      ],
    },

    // Submit button
    submit: [
      'button[type="submit"]',
      'input[type="submit"]',
      '#submit_app',
      '[data-qa="submit-application"]',
    ],
  }

  /**
   * Fill Greenhouse application form
   * @param {Object} profileData User profile data
   * @returns {Object} Result with filled fields
   */
  async fill(profileData) {
    this.filledFields = []
    this.errors = []

    try {
      const dataMap = this.mapProfileData(profileData)

      console.log('[ResuBoost] Starting Greenhouse form fill')

      // Section 1: Personal Information
      await this.fillPersonalInfo(dataMap)

      // Section 2: Address Information
      await this.fillAddressInfo(dataMap)

      // Section 3: Resume and Cover Letter
      await this.handleDocuments(profileData)

      // Section 4: Links (LinkedIn, Portfolio, etc.)
      await this.fillLinks(dataMap)

      // Section 5: Custom Questions
      await this.fillCustomQuestions(dataMap, profileData)

      // Section 6: Demographic Information (optional)
      await this.fillDemographicInfo(profileData)

      console.log(`[ResuBoost] Filled ${this.filledFields.length} fields on Greenhouse`)

      return {
        success: true,
        filledFields: this.filledFields,
        errors: this.errors,
      }
    } catch (error) {
      console.error('[ResuBoost] Greenhouse fill error:', error)
      this.errors.push({ type: 'general', message: error.message })
      return {
        success: false,
        filledFields: this.filledFields,
        errors: this.errors,
      }
    }
  }

  /**
   * Fill personal information fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillPersonalInfo(dataMap) {
    const fields = GreenhouseFiller.SELECTORS.personal

    for (const [fieldName, selectors] of Object.entries(fields)) {
      if (!dataMap[fieldName]) continue

      try {
        const input = this.findElement(selectors)
        if (input && !input.disabled && !input.readOnly) {
          if (input.value !== dataMap[fieldName]) {
            await this.fillField(input, dataMap[fieldName])
            console.log(`[ResuBoost] Filled personal field: ${fieldName}`)
          }
        }
      } catch (error) {
        this.errors.push({ type: 'personal', field: fieldName, message: error.message })
        console.warn(`[ResuBoost] Could not fill ${fieldName}:`, error)
      }
    }
  }

  /**
   * Fill address information fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillAddressInfo(dataMap) {
    const addressFields = GreenhouseFiller.SELECTORS.address

    for (const [fieldName, selectors] of Object.entries(addressFields)) {
      const dataKey = fieldName === 'street' ? 'address' : fieldName
      if (!dataMap[dataKey]) continue

      try {
        const element = this.findElement(selectors)
        if (element && !element.disabled) {
          if (element.tagName === 'SELECT') {
            await this.fillCountryOrStateSelect(element, dataMap[dataKey])
          } else if (element.value !== dataMap[dataKey]) {
            await this.fillField(element, dataMap[dataKey])
          }
          console.log(`[ResuBoost] Filled address field: ${fieldName}`)
        }
      } catch (error) {
        this.errors.push({ type: 'address', field: fieldName, message: error.message })
        console.warn(`[ResuBoost] Could not fill ${fieldName}:`, error)
      }
    }
  }

  /**
   * Fill country or state select dropdown with smart matching
   * @param {HTMLSelectElement} select Select element
   * @param {string} value Country or state name/code
   */
  async fillCountryOrStateSelect(select, value) {
    const valueLower = value.toLowerCase()

    // Common abbreviation mappings
    const mappings = {
      // Countries
      'us': 'united states',
      'usa': 'united states',
      'uk': 'united kingdom',
      'gb': 'united kingdom',
      'ca': 'canada',
      'au': 'australia',
      'de': 'germany',
      'fr': 'france',
      // US States
      'ca': 'california',
      'ny': 'new york',
      'tx': 'texas',
      'wa': 'washington',
      'fl': 'florida',
      'il': 'illinois',
      'pa': 'pennsylvania',
      'oh': 'ohio',
      'ga': 'georgia',
      'nc': 'north carolina',
      'mi': 'michigan',
      'nj': 'new jersey',
      'va': 'virginia',
      'ma': 'massachusetts',
      'az': 'arizona',
      'co': 'colorado',
    }

    const searchTerm = mappings[valueLower] || valueLower

    for (const option of select.options) {
      const optionText = option.text.toLowerCase()
      const optionValue = option.value.toLowerCase()

      if (
        optionText === searchTerm ||
        optionValue === searchTerm ||
        optionText.includes(searchTerm) ||
        searchTerm.includes(optionText) ||
        optionValue === valueLower
      ) {
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        this.filledFields.push({ name: select.name || select.id || 'select', type: 'select' })
        return
      }
    }
  }

  /**
   * Handle resume and cover letter uploads
   * @param {Object} profileData Profile data with document info
   */
  async handleDocuments(profileData) {
    // Handle resume upload
    await this.handleResumeUpload(profileData)

    // Handle cover letter
    await this.handleCoverLetter(profileData)
  }

  /**
   * Handle resume file upload
   * @param {Object} profileData Profile data with resume
   */
  async handleResumeUpload(profileData) {
    try {
      const resumeSelectors = GreenhouseFiller.SELECTORS.documents.resume

      // Find file input
      const fileInput = this.findElement(resumeSelectors.input)

      if (fileInput) {
        console.log('[ResuBoost] Resume upload field found')

        // If we have a resume file blob/data, try to upload it
        if (profileData.resumeFile && profileData.resumeFileName) {
          try {
            await this.uploadFile(fileInput, profileData.resumeFile, profileData.resumeFileName)
            this.filledFields.push({ name: 'resume', type: 'file_upload' })
            console.log('[ResuBoost] Resume file uploaded')
          } catch (uploadError) {
            console.warn('[ResuBoost] Could not auto-upload resume:', uploadError)
            this.filledFields.push({ name: 'resume', type: 'file_input_found' })
          }
        } else {
          this.filledFields.push({ name: 'resume', type: 'file_input_found' })
        }
      }

      // Check for dropzone
      const dropzone = this.findElement(resumeSelectors.dropzone)
      if (dropzone && !fileInput) {
        console.log('[ResuBoost] Resume dropzone found - manual upload required')
      }
    } catch (error) {
      this.errors.push({ type: 'resume', message: error.message })
      console.warn('[ResuBoost] Resume upload error:', error)
    }
  }

  /**
   * Upload file to input using DataTransfer API
   * @param {HTMLInputElement} input File input element
   * @param {Blob|File} file File to upload
   * @param {string} fileName File name
   */
  async uploadFile(input, file, fileName) {
    try {
      // Create a File object if we have a Blob
      const fileObj = file instanceof File ? file : new File([file], fileName, { type: file.type || 'application/pdf' })

      // Use DataTransfer to set files
      const dataTransfer = new DataTransfer()
      dataTransfer.items.add(fileObj)
      input.files = dataTransfer.files

      // Trigger events
      input.dispatchEvent(new Event('change', { bubbles: true }))
      input.dispatchEvent(new Event('input', { bubbles: true }))

      // Wait for upload processing
      await this.delay(500)
    } catch (error) {
      throw new Error(`File upload failed: ${error.message}`)
    }
  }

  /**
   * Handle cover letter (textarea or file)
   * @param {Object} profileData Profile data with cover letter
   */
  async handleCoverLetter(profileData) {
    try {
      const coverLetterSelectors = GreenhouseFiller.SELECTORS.documents.coverLetter

      // Try textarea first (more common)
      const textarea = this.findElement(coverLetterSelectors.textarea)
      if (textarea && profileData.coverLetter) {
        if (!textarea.value) {
          await this.fillField(textarea, profileData.coverLetter)
          console.log('[ResuBoost] Cover letter text filled')
        }
        return
      }

      // Check for file upload
      const fileInput = this.findElement(coverLetterSelectors.input)
      if (fileInput) {
        console.log('[ResuBoost] Cover letter file input found')
        if (profileData.coverLetterFile && profileData.coverLetterFileName) {
          try {
            await this.uploadFile(fileInput, profileData.coverLetterFile, profileData.coverLetterFileName)
            this.filledFields.push({ name: 'cover_letter', type: 'file_upload' })
          } catch (uploadError) {
            console.warn('[ResuBoost] Could not auto-upload cover letter:', uploadError)
          }
        }
      }
    } catch (error) {
      this.errors.push({ type: 'coverLetter', message: error.message })
      console.warn('[ResuBoost] Cover letter error:', error)
    }
  }

  /**
   * Fill link fields (LinkedIn, Portfolio, etc.)
   * @param {Object} dataMap Mapped profile data
   */
  async fillLinks(dataMap) {
    const linkFields = GreenhouseFiller.SELECTORS.links

    for (const [fieldName, selectors] of Object.entries(linkFields)) {
      if (!dataMap[fieldName]) continue

      try {
        const input = this.findElement(selectors)
        if (input && !input.disabled && !input.value) {
          await this.fillField(input, dataMap[fieldName])
          console.log(`[ResuBoost] Filled link field: ${fieldName}`)
        }
      } catch (error) {
        this.errors.push({ type: 'links', field: fieldName, message: error.message })
        console.warn(`[ResuBoost] Could not fill ${fieldName}:`, error)
      }
    }
  }

  /**
   * Fill custom screening questions
   * @param {Object} dataMap Mapped profile data
   * @param {Object} profileData Full profile data
   */
  async fillCustomQuestions(dataMap, profileData) {
    try {
      const questionContainers = document.querySelectorAll(
        GreenhouseFiller.SELECTORS.questions.container.join(', ')
      )

      for (const container of questionContainers) {
        // Skip if already processed
        if (container.dataset.resuboostFilled === 'true') continue

        await this.fillQuestionContainer(container, dataMap, profileData)
      }
    } catch (error) {
      this.errors.push({ type: 'questions', message: error.message })
      console.warn('[ResuBoost] Custom questions error:', error)
    }
  }

  /**
   * Fill a single question container
   * @param {HTMLElement} container Question container
   * @param {Object} dataMap Mapped profile data
   * @param {Object} profileData Full profile data
   */
  async fillQuestionContainer(container, dataMap, profileData) {
    const labelElement = container.querySelector(
      GreenhouseFiller.SELECTORS.questions.label.join(', ')
    )
    const labelText = (labelElement?.textContent || '').toLowerCase().trim()

    if (!labelText) return

    // Find input elements
    const textInput = container.querySelector('input[type="text"], input[type="number"], input[type="url"]')
    const select = container.querySelector('select')
    const textarea = container.querySelector('textarea')
    const radios = container.querySelectorAll('input[type="radio"]')
    const checkboxes = container.querySelectorAll('input[type="checkbox"]')

    try {
      // Years of experience
      if (this.matchesPattern(labelText, ['years', 'experience', 'how many years'])) {
        if (textInput && dataMap.yearsExperience) {
          await this.fillField(textInput, dataMap.yearsExperience.toString())
          container.dataset.resuboostFilled = 'true'
        } else if (select && dataMap.yearsExperience) {
          await this.fillSelectByBestMatch(select, dataMap.yearsExperience.toString())
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Salary expectations
      else if (this.matchesPattern(labelText, ['salary', 'compensation', 'pay', 'desired salary'])) {
        if (textInput && dataMap.salary) {
          await this.fillField(textInput, dataMap.salary.toString())
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Start date / Availability
      else if (this.matchesPattern(labelText, ['start date', 'available', 'when can you', 'earliest start'])) {
        if (textInput && profileData.availableDate) {
          await this.fillField(textInput, profileData.availableDate)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Work authorization
      else if (this.matchesPattern(labelText, ['authorized', 'eligible', 'legally', 'right to work'])) {
        if (radios.length > 0) {
          await this.fillYesNoQuestion(container, profileData.workAuthorization !== false)
          container.dataset.resuboostFilled = 'true'
        } else if (select) {
          const value = profileData.workAuthorization !== false ? 'yes' : 'no'
          await this.fillSelectByBestMatch(select, value)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Sponsorship required
      else if (this.matchesPattern(labelText, ['sponsorship', 'visa', 'sponsor'])) {
        if (radios.length > 0) {
          await this.fillYesNoQuestion(container, profileData.requiresSponsorship === true)
          container.dataset.resuboostFilled = 'true'
        } else if (select) {
          const value = profileData.requiresSponsorship === true ? 'yes' : 'no'
          await this.fillSelectByBestMatch(select, value)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // How did you hear about us / Source
      else if (this.matchesPattern(labelText, ['how did you hear', 'source', 'find out', 'learn about'])) {
        if (select) {
          await this.selectFirstValidOption(select)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Remote/On-site preference
      else if (this.matchesPattern(labelText, ['remote', 'on-site', 'hybrid', 'work location'])) {
        if (radios.length > 0 && profileData.openToRemote !== undefined) {
          await this.fillYesNoQuestion(container, profileData.openToRemote)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Relocation
      else if (this.matchesPattern(labelText, ['relocate', 'willing to move', 'relocation'])) {
        if (radios.length > 0 && profileData.willingToRelocate !== undefined) {
          await this.fillYesNoQuestion(container, profileData.willingToRelocate)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Age verification (18+)
      else if (this.matchesPattern(labelText, ['18 years', 'of age', 'legally of age'])) {
        if (radios.length > 0) {
          await this.fillYesNoQuestion(container, true)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Checkbox agreements (terms, consent, etc.)
      else if (checkboxes.length > 0 && this.matchesPattern(labelText, ['agree', 'consent', 'acknowledge', 'terms'])) {
        for (const checkbox of checkboxes) {
          if (!checkbox.checked) {
            checkbox.click()
            this.filledFields.push({ name: checkbox.name || 'checkbox', type: 'checkbox' })
          }
        }
        container.dataset.resuboostFilled = 'true'
      }
      // Answer templates for essay questions
      else if (textarea) {
        const answer = this.findAnswerTemplate(labelText, profileData.answerTemplates)
        if (answer && !textarea.value) {
          await this.fillField(textarea, answer)
          container.dataset.resuboostFilled = 'true'
        }
      }
    } catch (error) {
      console.warn(`[ResuBoost] Could not fill question "${labelText}":`, error)
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

      const isYes = radioValue === 'yes' ||
                    radioValue === 'true' ||
                    radioValue === '1' ||
                    labelText.includes('yes')

      const isNo = radioValue === 'no' ||
                   radioValue === 'false' ||
                   radioValue === '0' ||
                   labelText.includes('no')

      if ((value && isYes) || (!value && isNo)) {
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
   * Fill select by best matching value
   * @param {HTMLSelectElement} select Select element
   * @param {string} value Value to match
   */
  async fillSelectByBestMatch(select, value) {
    const valueLower = value.toLowerCase()

    // Try exact matches first
    for (const option of select.options) {
      const optionText = (option.text || '').toLowerCase()
      const optionValue = (option.value || '').toLowerCase()

      if (optionValue === valueLower || optionText === valueLower) {
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        this.filledFields.push({ name: select.name || select.id, type: 'select' })
        return
      }
    }

    // Try partial matches
    for (const option of select.options) {
      const optionText = (option.text || '').toLowerCase()

      if (optionText.includes(valueLower) || valueLower.includes(optionText)) {
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        this.filledFields.push({ name: select.name || select.id, type: 'select' })
        return
      }
    }

    // Handle numeric ranges for experience
    const numValue = parseInt(value, 10)
    if (!isNaN(numValue)) {
      for (const option of select.options) {
        const optionText = option.text.toLowerCase()
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
   * Select first valid option in a select dropdown (skip placeholder)
   * @param {HTMLSelectElement} select Select element
   */
  async selectFirstValidOption(select) {
    for (let i = 0; i < select.options.length; i++) {
      const option = select.options[i]
      const text = option.text.toLowerCase()

      // Skip placeholder options
      if (
        !option.value ||
        option.value === '' ||
        option.disabled ||
        text.includes('select') ||
        text.includes('choose') ||
        text.includes('please') ||
        text === '--'
      ) {
        continue
      }

      select.value = option.value
      select.dispatchEvent(new Event('change', { bubbles: true }))
      this.filledFields.push({ name: select.name || select.id, type: 'select' })
      return
    }
  }

  /**
   * Fill demographic information (optional EEOC questions)
   * @param {Object} profileData Profile data with demographic info
   */
  async fillDemographicInfo(profileData) {
    // Only fill if user has opted to share demographics
    if (!profileData.demographics) {
      console.log('[ResuBoost] No demographics data provided, skipping EEOC questions')
      return
    }

    const demographics = profileData.demographics
    const demoSelectors = GreenhouseFiller.SELECTORS.demographics

    try {
      // Gender
      if (demographics.gender) {
        const genderSelect = this.findElement(demoSelectors.gender)
        if (genderSelect) {
          await this.fillSelectByBestMatch(genderSelect, demographics.gender)
        }
      }

      // Ethnicity
      if (demographics.ethnicity) {
        const ethnicitySelect = this.findElement(demoSelectors.ethnicity)
        if (ethnicitySelect) {
          await this.fillSelectByBestMatch(ethnicitySelect, demographics.ethnicity)
        }
      }

      // Veteran status
      if (demographics.veteranStatus) {
        const veteranSelect = this.findElement(demoSelectors.veteran)
        if (veteranSelect) {
          await this.fillSelectByBestMatch(veteranSelect, demographics.veteranStatus)
        }
      }

      // Disability status
      if (demographics.disabilityStatus) {
        const disabilitySelect = this.findElement(demoSelectors.disability)
        if (disabilitySelect) {
          await this.fillSelectByBestMatch(disabilitySelect, demographics.disabilityStatus)
        }
      }

      console.log('[ResuBoost] Demographics section filled')
    } catch (error) {
      this.errors.push({ type: 'demographics', message: error.message })
      console.warn('[ResuBoost] Demographics fill error:', error)
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
   * Find answer template for a question
   * @param {string} questionText Question text
   * @param {Object} templates Answer templates
   * @returns {string|null} Matching answer
   */
  findAnswerTemplate(questionText, templates) {
    if (!templates) return null

    for (const [keyword, answer] of Object.entries(templates)) {
      if (questionText.includes(keyword.toLowerCase())) {
        return answer
      }
    }
    return null
  }

  /**
   * Check if text matches any pattern
   * @param {string} text Text to check
   * @param {string[]} patterns Patterns to match
   * @returns {boolean} True if matches
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
        '[data-qa="job-title"]',
        'h1',
      ]),
      company: this.extractText([
        '.company-name',
        '.posting-intro .company-name',
        '[data-company-name]',
        '[data-qa="company-name"]',
        '.header-logo img[alt]',
      ]),
      location: this.extractText([
        '.location',
        '.posting-location',
        '.job-location',
        '[data-qa="job-location"]',
      ]),
      description: this.extractText([
        '#content',
        '.content',
        '.job-description',
        '[data-description]',
        '.posting-description',
        '[data-qa="job-description"]',
      ]),
      department: this.extractText([
        '.department',
        '.posting-department',
        '[data-qa="department"]',
      ]),
      employmentType: this.extractText([
        '.employment-type',
        '[data-qa="employment-type"]',
      ]),
    }
  }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.GreenhouseFiller = GreenhouseFiller
}
