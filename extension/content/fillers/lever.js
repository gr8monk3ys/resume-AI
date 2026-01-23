/**
 * Lever Form Filler
 * Handles Lever ATS job application forms
 *
 * Lever forms have a specific structure with:
 * - Main application fields (name, email, phone, company)
 * - Resume upload with LinkedIn import option
 * - Professional links section
 * - Custom questions (varies by employer)
 * - Additional information section
 */

class LeverFiller extends GenericFiller {
  constructor() {
    super()
    this.platform = 'lever'
    this.errors = []
    this.resumeParsingComplete = false
  }

  /**
   * Lever-specific selectors organized by category
   * These selectors target Lever's standard application form elements
   */
  static SELECTORS = {
    // Form containers
    form: [
      '.application-form',
      '#application-form',
      'form.posting-form',
      '[data-qa="application-form"]',
    ],

    // Main application fields
    main: {
      fullName: [
        'input[name="name"]',
        '#name',
        '[data-qa="name-input"]',
        'input[placeholder*="name"]',
        'input[autocomplete="name"]',
      ],
      email: [
        'input[name="email"]',
        '#email',
        '[data-qa="email-input"]',
        'input[type="email"]',
        'input[autocomplete="email"]',
      ],
      phone: [
        'input[name="phone"]',
        '#phone',
        '[data-qa="phone-input"]',
        'input[type="tel"]',
        'input[autocomplete="tel"]',
      ],
      currentCompany: [
        'input[name="org"]',
        '#org',
        '[data-qa="org-input"]',
        'input[name="organization"]',
        'input[placeholder*="company"]',
        'input[placeholder*="organization"]',
      ],
      currentTitle: [
        'input[name="title"]',
        '[data-qa="title-input"]',
        'input[placeholder*="title"]',
        'input[placeholder*="position"]',
      ],
    },

    // Resume section
    resume: {
      section: [
        '.application-resume',
        '[data-qa="resume-section"]',
        '.resume-upload-section',
      ],
      fileInput: [
        'input[type="file"][name*="resume"]',
        '.resume-upload input[type="file"]',
        '[data-qa="resume-upload"] input[type="file"]',
        'input[type="file"][accept*=".pdf"]',
      ],
      uploadButton: [
        'button[aria-label*="resume"]',
        '.resume-upload-btn',
        '[data-qa="resume-upload-btn"]',
        '.application-resume button',
      ],
      linkedInImport: [
        '[data-source="linkedin"]',
        '.resume-import-linkedin',
        'button[aria-label*="LinkedIn"]',
        '[data-qa="linkedin-import"]',
        '.source-linkedin',
      ],
      parseButton: [
        '.resume-parse-button',
        '[data-qa="parse-resume"]',
        'button[aria-label*="parse"]',
      ],
      textArea: [
        '.application-resume textarea',
        'textarea[name*="resume"]',
        '[data-qa="resume-text"]',
      ],
      parsingPopup: [
        '.resume-parsing-modal',
        '[data-qa="resume-parsing"]',
        '.parsing-overlay',
      ],
    },

    // Professional links
    links: {
      section: [
        '.application-urls',
        '[data-qa="urls-section"]',
        '.urls-section',
      ],
      container: [
        '.url-item',
        '[data-qa="url-item"]',
        '.application-url',
      ],
      input: [
        'input[type="url"]',
        'input[type="text"]',
      ],
      addButton: [
        '[data-qa="add-url"]',
        '.add-url-button',
        'button[aria-label*="Add"]',
        '.add-link-btn',
      ],
      linkedIn: [
        'input[name*="linkedin"]',
        'input[placeholder*="LinkedIn"]',
        'input[placeholder*="linkedin.com"]',
        '[data-qa="linkedin-input"]',
      ],
      website: [
        'input[name*="portfolio"]',
        'input[name*="website"]',
        'input[placeholder*="Portfolio"]',
        'input[placeholder*="Website"]',
        '[data-qa="portfolio-input"]',
      ],
      github: [
        'input[name*="github"]',
        'input[placeholder*="GitHub"]',
        'input[placeholder*="github.com"]',
        '[data-qa="github-input"]',
      ],
    },

    // Custom questions
    questions: {
      container: [
        '.application-question',
        '[data-qa="custom-question"]',
        '.additional-information .application-field',
        '.custom-question-item',
        '.application-additional',
      ],
      label: [
        'label',
        '.label',
        '.field-label',
        '[data-qa="question-label"]',
      ],
      required: [
        '.required',
        '[aria-required="true"]',
        '.required-indicator',
      ],
    },

    // Additional information section
    additional: {
      section: [
        '.additional-information',
        '[data-qa="additional-section"]',
        '.application-additional',
      ],
      coverLetter: [
        'textarea[name*="cover"]',
        '[data-qa="cover-letter"]',
        'textarea[placeholder*="cover letter"]',
      ],
      additionalInfo: [
        'textarea[name*="additional"]',
        '[data-qa="additional-info"]',
        'textarea[placeholder*="additional"]',
      ],
    },

    // Navigation and submission
    navigation: {
      submit: [
        'button[type="submit"]',
        '.application-submit',
        '[data-qa="submit-application"]',
        'input[type="submit"]',
      ],
      error: [
        '.error-message',
        '.field-error',
        '[data-qa="error"]',
        '.validation-error',
      ],
    },
  }

  /**
   * Fill Lever application form
   * @param {Object} profileData User profile data
   * @returns {Object} Result with filled fields
   */
  async fill(profileData) {
    this.filledFields = []
    this.errors = []

    try {
      const dataMap = this.mapProfileData(profileData)

      console.log('[ResuBoost] Starting Lever form fill')

      // Main application fields
      await this.fillMainFields(dataMap)

      // Resume upload or LinkedIn import
      await this.handleResume(profileData)

      // Wait for resume parsing if triggered
      if (this.resumeParsingComplete) {
        await this.waitForResumeParsing()
      }

      // Links section
      await this.fillLinks(dataMap)

      // Additional information (custom questions)
      await this.fillAdditionalInfo(dataMap, profileData)

      console.log(`[ResuBoost] Filled ${this.filledFields.length} fields on Lever`)

      return {
        success: true,
        filledFields: this.filledFields,
        errors: this.errors,
      }
    } catch (error) {
      console.error('[ResuBoost] Lever fill error:', error)
      this.errors.push({ type: 'general', message: error.message })
      return {
        success: false,
        filledFields: this.filledFields,
        errors: this.errors,
      }
    }
  }

  /**
   * Fill main application fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillMainFields(dataMap) {
    // Construct full name from first and last
    const fullName = `${dataMap.firstName} ${dataMap.lastName}`.trim()

    const fieldMappings = [
      {
        field: 'fullName',
        selectors: LeverFiller.SELECTORS.main.fullName,
        value: fullName,
      },
      {
        field: 'email',
        selectors: LeverFiller.SELECTORS.main.email,
        value: dataMap.email,
      },
      {
        field: 'phone',
        selectors: LeverFiller.SELECTORS.main.phone,
        value: dataMap.phone,
      },
      {
        field: 'currentCompany',
        selectors: LeverFiller.SELECTORS.main.currentCompany,
        value: dataMap.currentCompany,
      },
      {
        field: 'currentTitle',
        selectors: LeverFiller.SELECTORS.main.currentTitle,
        value: dataMap.currentTitle,
      },
    ]

    for (const { field, selectors, value } of fieldMappings) {
      if (!value) continue

      try {
        const input = this.findElement(selectors)
        if (input && !input.disabled && !input.readOnly) {
          if (input.value !== value) {
            await this.fillField(input, value)
            console.log(`[ResuBoost] Filled main field: ${field}`)
          }
        }
      } catch (error) {
        this.errors.push({ type: 'main', field, message: error.message })
        console.warn(`[ResuBoost] Could not fill ${field}:`, error)
      }
    }
  }

  /**
   * Handle resume upload or LinkedIn import
   * @param {Object} profileData Profile data with resume info
   */
  async handleResume(profileData) {
    try {
      const resumeSelectors = LeverFiller.SELECTORS.resume
      const resumeSection = this.findElement(resumeSelectors.section)

      if (!resumeSection) {
        console.log('[ResuBoost] No resume section found')
        return
      }

      // Option 1: Try LinkedIn import if available and user has LinkedIn URL
      if (profileData.linkedIn) {
        const linkedInImport = this.findElement(resumeSelectors.linkedInImport)
        if (linkedInImport) {
          console.log('[ResuBoost] LinkedIn import option available')
          // Note: Clicking this opens a popup for LinkedIn auth
          // We log it but don't auto-click to avoid interrupting user flow
          this.filledFields.push({ name: 'linkedin_import', type: 'option_available' })
        }
      }

      // Option 2: File upload
      const fileInput = this.findElement(resumeSelectors.fileInput)
      if (fileInput) {
        console.log('[ResuBoost] Resume file input found')

        if (profileData.resumeFile && profileData.resumeFileName) {
          try {
            await this.uploadFile(fileInput, profileData.resumeFile, profileData.resumeFileName)
            this.filledFields.push({ name: 'resume', type: 'file_upload' })
            this.resumeParsingComplete = true
            console.log('[ResuBoost] Resume file uploaded')
          } catch (uploadError) {
            console.warn('[ResuBoost] Could not auto-upload resume:', uploadError)
            this.filledFields.push({ name: 'resume', type: 'file_input_found' })
          }
        } else {
          this.filledFields.push({ name: 'resume', type: 'file_input_found' })
        }
      }

      // Option 3: Paste resume text if textarea is available
      const resumeText = this.findElement(resumeSelectors.textArea)
      if (resumeText && profileData.resumeText) {
        if (!resumeText.value) {
          await this.fillField(resumeText, profileData.resumeText)
          console.log('[ResuBoost] Resume text pasted')
        }
      }
    } catch (error) {
      this.errors.push({ type: 'resume', message: error.message })
      console.warn('[ResuBoost] Resume handling error:', error)
    }
  }

  /**
   * Wait for Lever's resume parsing popup to complete
   * This popup appears after uploading a resume and extracts data
   */
  async waitForResumeParsing() {
    try {
      const parsingPopup = this.findElement(LeverFiller.SELECTORS.resume.parsingPopup)

      if (!parsingPopup) {
        console.log('[ResuBoost] No parsing popup detected')
        return
      }

      console.log('[ResuBoost] Waiting for resume parsing to complete...')

      // Wait for parsing popup to disappear (max 10 seconds)
      let attempts = 0
      const maxAttempts = 20

      while (attempts < maxAttempts) {
        await this.delay(500)
        attempts++

        const popup = this.findElement(LeverFiller.SELECTORS.resume.parsingPopup)
        if (!popup || popup.style.display === 'none' || !popup.offsetParent) {
          console.log('[ResuBoost] Resume parsing complete')
          // Give a little extra time for fields to populate
          await this.delay(500)
          return
        }
      }

      console.log('[ResuBoost] Resume parsing timeout - continuing anyway')
    } catch (error) {
      console.warn('[ResuBoost] Error waiting for resume parsing:', error)
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
      const fileObj = file instanceof File ? file : new File([file], fileName, { type: file.type || 'application/pdf' })

      const dataTransfer = new DataTransfer()
      dataTransfer.items.add(fileObj)
      input.files = dataTransfer.files

      input.dispatchEvent(new Event('change', { bubbles: true }))
      input.dispatchEvent(new Event('input', { bubbles: true }))

      await this.delay(500)
    } catch (error) {
      throw new Error(`File upload failed: ${error.message}`)
    }
  }

  /**
   * Fill professional links section
   * @param {Object} dataMap Mapped profile data
   */
  async fillLinks(dataMap) {
    try {
      const linksSection = this.findElement(LeverFiller.SELECTORS.links.section)

      if (!linksSection) {
        // Try individual link inputs if no section found
        await this.fillIndividualLinks(dataMap)
        return
      }

      // Get all existing link inputs in the section
      const existingInputs = linksSection.querySelectorAll('input[type="url"], input[type="text"]')

      const linksToFill = [
        { value: dataMap.linkedIn, label: 'linkedin' },
        { value: dataMap.website, label: 'website' },
        { value: dataMap.github, label: 'github' },
      ].filter((link) => link.value)

      let filledCount = 0

      // Fill existing empty inputs
      for (const input of existingInputs) {
        if (filledCount >= linksToFill.length) break
        if (input.value) continue // Skip filled inputs

        const link = linksToFill[filledCount]
        await this.fillField(input, link.value)
        console.log(`[ResuBoost] Filled link: ${link.label}`)
        filledCount++
      }

      // Click "Add another link" button if we have more links to add
      while (filledCount < linksToFill.length) {
        const addButton = this.findElement(LeverFiller.SELECTORS.links.addButton)
        if (!addButton) break

        addButton.click()
        await this.delay(300) // Wait for new input to appear

        // Find the new input
        const newInputs = linksSection.querySelectorAll('input[type="url"], input[type="text"]')
        const lastInput = newInputs[newInputs.length - 1]

        if (lastInput && !lastInput.value) {
          const link = linksToFill[filledCount]
          await this.fillField(lastInput, link.value)
          console.log(`[ResuBoost] Added and filled link: ${link.label}`)
          filledCount++
        } else {
          break // Could not add more links
        }
      }
    } catch (error) {
      this.errors.push({ type: 'links', message: error.message })
      console.warn('[ResuBoost] Links fill error:', error)
    }
  }

  /**
   * Fill individual link inputs (when not in a links section)
   * @param {Object} dataMap Mapped profile data
   */
  async fillIndividualLinks(dataMap) {
    const linkFields = LeverFiller.SELECTORS.links

    const linkMappings = [
      { field: 'linkedIn', selectors: linkFields.linkedIn, value: dataMap.linkedIn },
      { field: 'website', selectors: linkFields.website, value: dataMap.website },
      { field: 'github', selectors: linkFields.github, value: dataMap.github },
    ]

    for (const { field, selectors, value } of linkMappings) {
      if (!value) continue

      try {
        const input = this.findElement(selectors)
        if (input && !input.disabled && !input.value) {
          await this.fillField(input, value)
          console.log(`[ResuBoost] Filled individual link: ${field}`)
        }
      } catch (error) {
        console.warn(`[ResuBoost] Could not fill ${field}:`, error)
      }
    }
  }

  /**
   * Fill additional information and custom questions
   * @param {Object} dataMap Mapped profile data
   * @param {Object} profileData Full profile data
   */
  async fillAdditionalInfo(dataMap, profileData) {
    try {
      // Fill cover letter if present
      await this.fillCoverLetter(profileData)

      // Fill additional info textarea
      await this.fillAdditionalTextField(profileData)

      // Fill custom question groups
      await this.fillCustomQuestions(dataMap, profileData)
    } catch (error) {
      this.errors.push({ type: 'additional', message: error.message })
      console.warn('[ResuBoost] Additional info error:', error)
    }
  }

  /**
   * Fill cover letter textarea
   * @param {Object} profileData Profile data with cover letter
   */
  async fillCoverLetter(profileData) {
    if (!profileData.coverLetter) return

    const coverLetterSelectors = LeverFiller.SELECTORS.additional.coverLetter
    const textarea = this.findElement(coverLetterSelectors)

    if (textarea && !textarea.value) {
      await this.fillField(textarea, profileData.coverLetter)
      console.log('[ResuBoost] Filled cover letter')
    }
  }

  /**
   * Fill additional information textarea
   * @param {Object} profileData Profile data with additional info
   */
  async fillAdditionalTextField(profileData) {
    if (!profileData.additionalInfo) return

    const additionalSelectors = LeverFiller.SELECTORS.additional.additionalInfo
    const textarea = this.findElement(additionalSelectors)

    if (textarea && !textarea.value) {
      await this.fillField(textarea, profileData.additionalInfo)
      console.log('[ResuBoost] Filled additional information')
    }
  }

  /**
   * Fill custom questions
   * @param {Object} dataMap Mapped profile data
   * @param {Object} profileData Full profile data
   */
  async fillCustomQuestions(dataMap, profileData) {
    const questionContainers = document.querySelectorAll(
      LeverFiller.SELECTORS.questions.container.join(', ')
    )

    for (const container of questionContainers) {
      // Skip if already processed
      if (container.dataset.resuboostFilled === 'true') continue

      const label = container.querySelector(
        LeverFiller.SELECTORS.questions.label.join(', ')
      )
      const labelText = (label?.textContent || '').toLowerCase().trim()

      if (!labelText) continue

      // Determine input type and fill accordingly
      const textInput = container.querySelector('input[type="text"], input[type="number"], input[type="url"]')
      const select = container.querySelector('select')
      const textarea = container.querySelector('textarea')
      const radios = container.querySelectorAll('input[type="radio"]')
      const checkboxes = container.querySelectorAll('input[type="checkbox"]')

      try {
        await this.fillQuestionByType(container, labelText, {
          textInput,
          select,
          textarea,
          radios,
          checkboxes,
        }, dataMap, profileData)
      } catch (error) {
        console.warn(`[ResuBoost] Could not fill question "${labelText}":`, error)
      }
    }
  }

  /**
   * Fill a question based on its type
   * @param {HTMLElement} container Question container
   * @param {string} labelText Label text
   * @param {Object} inputs Input elements object
   * @param {Object} dataMap Mapped data
   * @param {Object} profileData Full profile data
   */
  async fillQuestionByType(container, labelText, inputs, dataMap, profileData) {
    const { textInput, select, textarea, radios, checkboxes } = inputs

    // Years of experience
    if (this.matchesPattern(labelText, ['years', 'experience', 'how many years', 'how long'])) {
      if (textInput && dataMap.yearsExperience) {
        await this.fillField(textInput, dataMap.yearsExperience.toString())
        container.dataset.resuboostFilled = 'true'
      } else if (select && dataMap.yearsExperience) {
        await this.fillSelectByBestMatch(select, dataMap.yearsExperience.toString())
        container.dataset.resuboostFilled = 'true'
      }
    }
    // Salary expectations
    else if (this.matchesPattern(labelText, ['salary', 'compensation', 'pay', 'expected salary'])) {
      if (textInput && dataMap.salary) {
        await this.fillField(textInput, dataMap.salary.toString())
        container.dataset.resuboostFilled = 'true'
      }
    }
    // Location
    else if (this.matchesPattern(labelText, ['location', 'city', 'where are you', 'based in'])) {
      const location = this.formatLocation(dataMap)
      if (textInput && location) {
        await this.fillField(textInput, location)
        container.dataset.resuboostFilled = 'true'
      }
    }
    // Start date / Availability
    else if (this.matchesPattern(labelText, ['start', 'available', 'when', 'earliest'])) {
      if (textInput && profileData.availableDate) {
        await this.fillField(textInput, profileData.availableDate)
        container.dataset.resuboostFilled = 'true'
      }
    }
    // Work authorization
    else if (this.matchesPattern(labelText, ['authorized', 'eligible', 'legally', 'right to work'])) {
      if (radios.length > 0) {
        await this.selectRadioByValue(radios, profileData.workAuthorization !== false)
        container.dataset.resuboostFilled = 'true'
      } else if (select) {
        const value = profileData.workAuthorization !== false ? 'yes' : 'no'
        await this.fillSelectByBestMatch(select, value)
        container.dataset.resuboostFilled = 'true'
      }
    }
    // Sponsorship
    else if (this.matchesPattern(labelText, ['sponsorship', 'visa', 'sponsor'])) {
      if (radios.length > 0) {
        await this.selectRadioByValue(radios, profileData.requiresSponsorship === true)
        container.dataset.resuboostFilled = 'true'
      } else if (select) {
        const value = profileData.requiresSponsorship === true ? 'yes' : 'no'
        await this.fillSelectByBestMatch(select, value)
        container.dataset.resuboostFilled = 'true'
      }
    }
    // Remote work preference
    else if (this.matchesPattern(labelText, ['remote', 'work from home', 'hybrid', 'on-site'])) {
      if (radios.length > 0 && profileData.openToRemote !== undefined) {
        await this.selectRadioByValue(radios, profileData.openToRemote)
        container.dataset.resuboostFilled = 'true'
      }
    }
    // Relocation
    else if (this.matchesPattern(labelText, ['relocate', 'willing to move', 'relocation'])) {
      if (radios.length > 0 && profileData.willingToRelocate !== undefined) {
        await this.selectRadioByValue(radios, profileData.willingToRelocate)
        container.dataset.resuboostFilled = 'true'
      }
    }
    // How did you hear about us
    else if (this.matchesPattern(labelText, ['hear', 'source', 'find', 'learn about'])) {
      if (select) {
        await this.selectFirstValidOption(select)
        container.dataset.resuboostFilled = 'true'
      }
    }
    // Terms and conditions / Consent
    else if (checkboxes.length > 0 && this.matchesPattern(labelText, ['agree', 'terms', 'acknowledge', 'consent'])) {
      for (const checkbox of checkboxes) {
        if (!checkbox.checked) {
          checkbox.click()
          this.filledFields.push({ name: checkbox.name || 'consent', type: 'checkbox' })
        }
      }
      container.dataset.resuboostFilled = 'true'
    }
    // Cover letter or why interested
    else if (textarea && this.matchesPattern(labelText, ['cover letter', 'why', 'interested', 'tell us about'])) {
      if (profileData.coverLetter && !textarea.value) {
        await this.fillField(textarea, profileData.coverLetter)
        container.dataset.resuboostFilled = 'true'
      }
    }
    // Generic text questions - try answer templates
    else if (textarea) {
      const answer = this.findAnswerTemplate(labelText, profileData.answerTemplates)
      if (answer && !textarea.value) {
        await this.fillField(textarea, answer)
        container.dataset.resuboostFilled = 'true'
      }
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

      const isYes = radioValue === 'yes' ||
                    radioValue === 'true' ||
                    radioValue === '1' ||
                    label.includes('yes')

      const isNo = radioValue === 'no' ||
                   radioValue === 'false' ||
                   radioValue === '0' ||
                   label.includes('no')

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

    // Try exact match first
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

    // Try partial match
    for (const option of select.options) {
      const optionText = (option.text || '').toLowerCase()

      if (optionText.includes(valueLower) || valueLower.includes(optionText)) {
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        this.filledFields.push({ name: select.name || select.id, type: 'select' })
        return
      }
    }

    // Handle numeric ranges
    const numValue = parseInt(value, 10)
    if (!isNaN(numValue)) {
      for (const option of select.options) {
        const rangeMatch = option.text.match(/(\d+)\s*[-to]+\s*(\d+)/)
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
   * Select first valid option in dropdown (skip placeholder)
   * @param {HTMLSelectElement} select Select element
   */
  async selectFirstValidOption(select) {
    for (let i = 0; i < select.options.length; i++) {
      const option = select.options[i]
      const text = option.text.toLowerCase()

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
   * Format location string from data map
   * @param {Object} dataMap Data map with location fields
   * @returns {string} Formatted location
   */
  formatLocation(dataMap) {
    const parts = [dataMap.city, dataMap.state, dataMap.country].filter(Boolean)
    return parts.join(', ')
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
   * Find first matching element from selectors
   * @param {string[]} selectors CSS selectors
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
   * Check if text matches patterns
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
   * Extract job details from Lever job page
   * @returns {Object} Job details
   */
  extractJobDetails() {
    return {
      title: this.extractText([
        '.posting-headline h2',
        '.posting-title',
        '[data-qa="posting-name"]',
        'h1.posting-title',
      ]),
      company: this.extractText([
        '.posting-headline .company-name',
        '.main-header-logo img[alt]',
        '[data-qa="company-name"]',
        '.company-header .company-name',
      ]),
      location: this.extractText([
        '.posting-categories .location',
        '.posting-headline .location',
        '[data-qa="posting-location"]',
        '.posting-location',
      ]),
      description: this.extractText([
        '.posting-description',
        '[data-qa="posting-description"]',
        '.content',
        '.section-wrapper .section',
      ]),
      commitment: this.extractText([
        '.posting-categories .commitment',
        '[data-qa="posting-commitment"]',
        '.commitment',
      ]),
      team: this.extractText([
        '.posting-categories .team',
        '[data-qa="posting-team"]',
        '.department',
      ]),
      workplaceType: this.extractText([
        '.posting-categories .workplaceType',
        '[data-qa="posting-workplace-type"]',
        '.workplace-type',
      ]),
    }
  }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.LeverFiller = LeverFiller
}
