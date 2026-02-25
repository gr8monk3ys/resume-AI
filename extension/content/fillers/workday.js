/**
 * Workday Form Filler
 * Handles Workday ATS job application forms
 *
 * Workday is one of the most complex ATS systems with:
 * - Dynamic form loading (React-based SPA)
 * - Multi-page application flow
 * - Custom components for dropdowns and inputs
 * - Sections for personal info, experience, education, documents
 * - Significant variation between company implementations
 *
 * Note: Workday forms are complex and vary significantly between companies.
 * This filler provides a best-effort approach to fill common fields.
 */

class WorkdayFiller extends GenericFiller {
  constructor() {
    super()
    this.platform = 'workday'
    this.errors = []
    this.currentSection = 'unknown'
  }

  /**
   * Workday-specific selectors organized by category
   * Uses data-automation-id attributes which are more stable
   */
  static SELECTORS = {
    // Loading indicators
    loading: {
      spinner: [
        '[data-automation-id="loading"]',
        '.wd-loading',
        '.loading-overlay',
        '[data-automation-id="spinnerContainer"]',
        '.wd-spinner',
      ],
      skeleton: [
        '.wd-skeleton',
        '[data-automation-id="skeleton"]',
      ],
    },

    // Page/Section headers
    headers: {
      page: [
        '[data-automation-id="pageHeaderTitle"]',
        '.wd-section-title',
        'h2[data-automation-id]',
        '.header-title',
        '[data-automation-id="sectionTitle"]',
      ],
      section: [
        '[data-automation-id="sectionHeader"]',
        '.wd-FormSection-header',
        'h3[data-automation-id]',
      ],
    },

    // Personal information
    personal: {
      firstName: [
        '[data-automation-id="legalNameSection_firstName"]',
        '[data-automation-id="firstName"]',
        '[data-automation-id="name_first"]',
        'input[id*="firstName"]',
      ],
      lastName: [
        '[data-automation-id="legalNameSection_lastName"]',
        '[data-automation-id="lastName"]',
        '[data-automation-id="name_last"]',
        'input[id*="lastName"]',
      ],
      preferredName: [
        '[data-automation-id="preferredName"]',
        '[data-automation-id="legalNameSection_preferredName"]',
      ],
      country: [
        '[data-automation-id="countryDropdown"]',
        '[data-automation-id="country"]',
        'button[aria-label*="Country"]',
      ],
    },

    // Contact information
    contact: {
      email: [
        '[data-automation-id="email"]',
        '[data-automation-id="emailAddress"]',
        'input[type="email"]',
        'input[id*="email"]',
      ],
      phone: [
        '[data-automation-id="phone-number"]',
        '[data-automation-id="phoneNumber"]',
        '[data-automation-id="phone"]',
        'input[type="tel"]',
        'input[id*="phone"]',
      ],
      phoneType: [
        '[data-automation-id="phoneDeviceType"]',
        '[data-automation-id="phone-device-type"]',
        'button[aria-label*="Phone Device"]',
      ],
      phoneCountryCode: [
        '[data-automation-id="countryPhoneCode"]',
        '[data-automation-id="phone-country-code"]',
      ],
    },

    // Address
    address: {
      line1: [
        '[data-automation-id="addressSection_addressLine1"]',
        '[data-automation-id="address"]',
        '[data-automation-id="addressLine1"]',
        'input[id*="addressLine1"]',
      ],
      line2: [
        '[data-automation-id="addressSection_addressLine2"]',
        '[data-automation-id="addressLine2"]',
      ],
      city: [
        '[data-automation-id="addressSection_city"]',
        '[data-automation-id="city"]',
        'input[id*="city"]',
      ],
      state: [
        '[data-automation-id="addressSection_region"]',
        '[data-automation-id="state"]',
        '[data-automation-id="province"]',
        'button[aria-label*="State"]',
        'button[aria-label*="Region"]',
      ],
      zipCode: [
        '[data-automation-id="addressSection_postalCode"]',
        '[data-automation-id="postalCode"]',
        '[data-automation-id="zip"]',
        'input[id*="postalCode"]',
      ],
      country: [
        '[data-automation-id="addressSection_countryRegion"]',
        '[data-automation-id="countryRegion"]',
        'button[aria-label*="Country"]',
      ],
    },

    // Resume/Documents
    documents: {
      resumeUpload: [
        '[data-automation-id="file-upload-input-ref"]',
        'input[type="file"]',
        '[data-automation-id="resumeUpload"]',
        '[data-automation-id="resume-upload-input"]',
      ],
      resumeDropzone: [
        '[data-automation-id="file-upload-drop-zone"]',
        '.wd-file-upload-dropzone',
      ],
      linkedInImport: [
        '[data-automation-id="linkedInImport"]',
        '[data-automation-id="parseResumeButton"]',
        'button[aria-label*="LinkedIn"]',
      ],
      coverLetter: [
        '[data-automation-id="coverLetter"]',
        'textarea[id*="coverLetter"]',
        '[data-automation-id="cover-letter"]',
      ],
    },

    // Work Experience
    experience: {
      section: [
        '[data-automation-id="workExperienceSection"]',
        '[data-automation-id="experience-section"]',
      ],
      addButton: [
        '[data-automation-id="Add Work Experience"]',
        '[data-automation-id="addWorkExperience"]',
        'button[aria-label*="Add Work Experience"]',
        'button[aria-label*="Add Position"]',
      ],
      jobTitle: [
        '[data-automation-id="jobTitle"]',
        '[data-automation-id="title"]',
        'input[id*="jobTitle"]',
      ],
      company: [
        '[data-automation-id="company"]',
        '[data-automation-id="companyName"]',
        'input[id*="company"]',
      ],
      location: [
        '[data-automation-id="location"]',
        '[data-automation-id="workLocation"]',
      ],
      startMonth: [
        '[data-automation-id="startDateMonth"]',
        '[data-automation-id="from-month"]',
        'button[aria-label*="Start Month"]',
      ],
      startYear: [
        '[data-automation-id="startDateYear"]',
        '[data-automation-id="from-year"]',
        'input[id*="startYear"]',
      ],
      endMonth: [
        '[data-automation-id="endDateMonth"]',
        '[data-automation-id="to-month"]',
        'button[aria-label*="End Month"]',
      ],
      endYear: [
        '[data-automation-id="endDateYear"]',
        '[data-automation-id="to-year"]',
        'input[id*="endYear"]',
      ],
      currentJob: [
        '[data-automation-id="currentlyWorkHere"]',
        'input[type="checkbox"][id*="current"]',
        '[data-automation-id="isCurrent"]',
      ],
      description: [
        '[data-automation-id="description"]',
        'textarea[id*="description"]',
        '[data-automation-id="roleDescription"]',
      ],
    },

    // Education
    education: {
      section: [
        '[data-automation-id="educationSection"]',
        '[data-automation-id="education-section"]',
      ],
      addButton: [
        '[data-automation-id="Add Education"]',
        '[data-automation-id="addEducation"]',
        'button[aria-label*="Add Education"]',
      ],
      school: [
        '[data-automation-id="school"]',
        '[data-automation-id="schoolName"]',
        'input[id*="school"]',
      ],
      degree: [
        '[data-automation-id="degree"]',
        '[data-automation-id="degreeType"]',
        'button[aria-label*="Degree"]',
      ],
      fieldOfStudy: [
        '[data-automation-id="fieldOfStudy"]',
        '[data-automation-id="major"]',
        'input[id*="fieldOfStudy"]',
      ],
      gpa: [
        '[data-automation-id="gpa"]',
        'input[id*="gpa"]',
      ],
      startYear: [
        '[data-automation-id="educationStartYear"]',
        '[data-automation-id="startYear"]',
        'input[id*="eduStartYear"]',
      ],
      endYear: [
        '[data-automation-id="educationEndYear"]',
        '[data-automation-id="endYear"]',
        '[data-automation-id="graduationYear"]',
        'input[id*="eduEndYear"]',
      ],
    },

    // Custom Questions
    questions: {
      container: [
        '[data-automation-id="questionItem"]',
        '.wd-FormInputComponent',
        '[data-automation-id^="formField"]',
        '[data-automation-id="questionContainer"]',
      ],
      label: [
        'label',
        '[data-automation-id="formLabel"]',
        '.wd-label',
        '[data-automation-id="questionText"]',
      ],
      required: [
        '[data-automation-id="required"]',
        '.wd-required',
        '[aria-required="true"]',
      ],
    },

    // Dropdown components (Workday custom)
    dropdown: {
      trigger: [
        '[data-automation-id*="dropdown"]',
        'button[aria-haspopup="listbox"]',
        '.wd-dropdown',
        '[role="combobox"]',
      ],
      options: [
        '[data-automation-id*="promptOption"]',
        '[role="option"]',
        '.wd-ListItem',
        '[data-automation-id="option"]',
      ],
      search: [
        '[data-automation-id="searchBox"]',
        'input[role="combobox"]',
        '.wd-search-input',
      ],
    },

    // Navigation
    navigation: {
      next: [
        '[data-automation-id="bottom-navigation-next-button"]',
        '[data-automation-id="nextButton"]',
        'button[aria-label*="Next"]',
        'button[aria-label*="Continue"]',
      ],
      back: [
        '[data-automation-id="bottom-navigation-previous-button"]',
        '[data-automation-id="previousButton"]',
        'button[aria-label*="Back"]',
        'button[aria-label*="Previous"]',
      ],
      submit: [
        '[data-automation-id="bottom-navigation-submit-button"]',
        '[data-automation-id="submitButton"]',
        'button[aria-label*="Submit"]',
      ],
      save: [
        '[data-automation-id="saveButton"]',
        'button[aria-label*="Save"]',
      ],
    },

    // Progress
    progress: {
      bar: [
        '[data-automation-id="progressBar"]',
        '[role="progressbar"]',
        '.wd-progress',
      ],
      step: [
        '[data-automation-id="stepIndicator"]',
        '.wd-step',
      ],
    },
  }

  /**
   * Section indicators for detecting current page
   */
  static SECTION_INDICATORS = {
    personal: ['personal information', 'about you', 'my information', 'personal details'],
    contact: ['contact information', 'contact details', 'how can we reach you', 'contact info'],
    experience: ['work experience', 'employment history', 'professional experience', 'work history'],
    education: ['education', 'academic', 'degree', 'educational background'],
    resume: ['resume', 'cv', 'upload', 'documents', 'attach resume'],
    questions: ['additional questions', 'screening questions', 'questionnaire', 'application questions'],
    review: ['review', 'summary', 'confirm', 'preview'],
  }

  /**
   * Fill Workday application form
   * @param {Object} profileData User profile data
   * @returns {Object} Result with filled fields
   */
  async fill(profileData) {
    this.filledFields = []
    this.errors = []

    try {
      const dataMap = this.mapProfileData(profileData)

      console.log('[ResuBoost] Starting Workday form fill')

      // Wait for Workday's dynamic content to load
      await this.waitForWorkdayLoad()

      // Detect which section/page we're on
      this.currentSection = this.detectCurrentSection()
      console.log(`[ResuBoost] Detected section: ${this.currentSection}`)

      // Fill based on current section
      switch (this.currentSection) {
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
        case 'review':
          console.log('[ResuBoost] On review page - no fields to fill')
          break
        default:
          // Try to fill all visible fields
          console.log('[ResuBoost] Unknown section - attempting to fill all visible fields')
          await this.fillAllVisibleFields(dataMap, profileData)
      }

      console.log(`[ResuBoost] Filled ${this.filledFields.length} fields on Workday`)

      return {
        success: true,
        filledFields: this.filledFields,
        errors: this.errors,
        currentSection: this.currentSection,
      }
    } catch (error) {
      console.error('[ResuBoost] Workday fill error:', error)
      this.errors.push({ type: 'general', message: error.message })
      return {
        success: false,
        filledFields: this.filledFields,
        errors: this.errors,
      }
    }
  }

  /**
   * Wait for Workday's dynamic content to load
   * Workday is a React SPA that loads content dynamically
   */
  async waitForWorkdayLoad() {
    return new Promise((resolve) => {
      let attempts = 0
      const maxAttempts = 30 // 15 seconds max

      const checkLoading = () => {
        const loadingIndicators = document.querySelectorAll(
          WorkdayFiller.SELECTORS.loading.spinner.join(', ')
        )

        // Check if any loading indicators are visible
        let isLoading = false
        for (const indicator of loadingIndicators) {
          if (indicator.offsetParent !== null && indicator.style.display !== 'none') {
            isLoading = true
            break
          }
        }

        if (!isLoading) {
          // Also wait a bit for React to finish rendering
          setTimeout(resolve, 300)
        } else if (attempts < maxAttempts) {
          attempts++
          setTimeout(checkLoading, 500)
        } else {
          console.warn('[ResuBoost] Workday load timeout - proceeding anyway')
          resolve()
        }
      }

      // Initial delay to let page start loading
      setTimeout(checkLoading, 500)
    })
  }

  /**
   * Wait for a specific element to appear
   * @param {string[]} selectors Selectors to wait for
   * @param {number} timeout Maximum wait time in ms
   * @returns {HTMLElement|null} Found element or null
   */
  async waitForElement(selectors, timeout = 5000) {
    const startTime = Date.now()
    const selectorString = selectors.join(', ')

    while (Date.now() - startTime < timeout) {
      const element = document.querySelector(selectorString)
      if (element) return element
      await this.delay(200)
    }

    return null
  }

  /**
   * Detect current section of the application
   * @returns {string} Section name
   */
  detectCurrentSection() {
    // Check page header or section title
    const headers = document.querySelectorAll(
      WorkdayFiller.SELECTORS.headers.page.join(', ')
    )

    for (const header of headers) {
      const headerText = (header.textContent || '').toLowerCase().trim()

      for (const [section, indicators] of Object.entries(WorkdayFiller.SECTION_INDICATORS)) {
        if (indicators.some((indicator) => headerText.includes(indicator))) {
          return section
        }
      }
    }

    // Also check URL for clues
    const url = window.location.href.toLowerCase()
    if (url.includes('personal')) return 'personal'
    if (url.includes('contact')) return 'contact'
    if (url.includes('experience') || url.includes('work-history')) return 'experience'
    if (url.includes('education')) return 'education'
    if (url.includes('resume') || url.includes('document')) return 'resume'
    if (url.includes('question')) return 'questions'
    if (url.includes('review') || url.includes('summary')) return 'review'

    return 'unknown'
  }

  /**
   * Fill personal information fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillPersonalInfo(dataMap) {
    const fields = WorkdayFiller.SELECTORS.personal

    const fieldMappings = [
      { field: 'firstName', selectors: fields.firstName, value: dataMap.firstName },
      { field: 'lastName', selectors: fields.lastName, value: dataMap.lastName },
    ]

    for (const { field, selectors, value } of fieldMappings) {
      if (!value) continue

      try {
        const input = await this.waitForElement(selectors, 2000)
        if (input) {
          await this.fillWorkdayField(input, value)
          console.log(`[ResuBoost] Filled personal field: ${field}`)
        }
      } catch (error) {
        this.errors.push({ type: 'personal', field, message: error.message })
        console.warn(`[ResuBoost] Could not fill ${field}:`, error)
      }
    }

    // Handle country dropdown
    if (dataMap.country) {
      try {
        const countryDropdown = this.findElement(fields.country)
        if (countryDropdown) {
          await this.fillWorkdayDropdown(countryDropdown, dataMap.country)
        }
      } catch (error) {
        console.warn('[ResuBoost] Could not fill country:', error)
      }
    }
  }

  /**
   * Fill contact information fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillContactInfo(dataMap) {
    const fields = WorkdayFiller.SELECTORS.contact
    const addressFields = WorkdayFiller.SELECTORS.address

    // Email and phone
    const contactMappings = [
      { field: 'email', selectors: fields.email, value: dataMap.email },
      { field: 'phone', selectors: fields.phone, value: dataMap.phone },
    ]

    for (const { field, selectors, value } of contactMappings) {
      if (!value) continue

      try {
        const input = await this.waitForElement(selectors, 2000)
        if (input) {
          await this.fillWorkdayField(input, value)
          console.log(`[ResuBoost] Filled contact field: ${field}`)
        }
      } catch (error) {
        this.errors.push({ type: 'contact', field, message: error.message })
        console.warn(`[ResuBoost] Could not fill ${field}:`, error)
      }
    }

    // Address fields
    const addressMappings = [
      { field: 'address', selectors: addressFields.line1, value: dataMap.address },
      { field: 'city', selectors: addressFields.city, value: dataMap.city },
      { field: 'zipCode', selectors: addressFields.zipCode, value: dataMap.zipCode },
    ]

    for (const { field, selectors, value } of addressMappings) {
      if (!value) continue

      try {
        const input = this.findElement(selectors)
        if (input) {
          await this.fillWorkdayField(input, value)
          console.log(`[ResuBoost] Filled address field: ${field}`)
        }
      } catch (error) {
        console.warn(`[ResuBoost] Could not fill ${field}:`, error)
      }
    }

    // State dropdown
    if (dataMap.state) {
      try {
        const stateDropdown = this.findElement(addressFields.state)
        if (stateDropdown) {
          await this.fillWorkdayDropdown(stateDropdown, dataMap.state)
        }
      } catch (error) {
        console.warn('[ResuBoost] Could not fill state:', error)
      }
    }
  }

  /**
   * Fill work experience section
   * @param {Object} profileData Profile data with experience
   */
  async fillExperience(profileData) {
    if (!profileData.experience || profileData.experience.length === 0) {
      console.log('[ResuBoost] No experience data to fill')
      return
    }

    const expSelectors = WorkdayFiller.SELECTORS.experience

    try {
      // Check if we need to add a new experience entry
      const existingExperience = document.querySelectorAll('[data-automation-id="workExperienceCard"]')

      if (existingExperience.length === 0) {
        // Try to click "Add Work Experience" button
        const addButton = this.findElement(expSelectors.addButton)
        if (addButton) {
          addButton.click()
          await this.delay(500) // Wait for form to appear
        }
      }

      // Fill most recent experience
      const exp = profileData.experience[0]

      // Job title
      if (exp.title) {
        const titleInput = await this.waitForElement(expSelectors.jobTitle, 2000)
        if (titleInput) {
          await this.fillWorkdayField(titleInput, exp.title)
        }
      }

      // Company
      if (exp.company) {
        const companyInput = this.findElement(expSelectors.company)
        if (companyInput) {
          await this.fillWorkdayField(companyInput, exp.company)
        }
      }

      // Location
      if (exp.location) {
        const locationInput = this.findElement(expSelectors.location)
        if (locationInput) {
          await this.fillWorkdayField(locationInput, exp.location)
        }
      }

      // Description
      if (exp.description) {
        const descInput = this.findElement(expSelectors.description)
        if (descInput) {
          await this.fillWorkdayField(descInput, exp.description)
        }
      }

      // Current job checkbox
      if (exp.current) {
        const currentCheckbox = this.findElement(expSelectors.currentJob)
        if (currentCheckbox && !currentCheckbox.checked) {
          currentCheckbox.click()
          this.filledFields.push({ name: 'currentJob', type: 'checkbox' })
        }
      }

      console.log('[ResuBoost] Filled work experience')
    } catch (error) {
      this.errors.push({ type: 'experience', message: error.message })
      console.warn('[ResuBoost] Experience fill error:', error)
    }
  }

  /**
   * Fill education section
   * @param {Object} profileData Profile data with education
   */
  async fillEducation(profileData) {
    if (!profileData.education || profileData.education.length === 0) {
      console.log('[ResuBoost] No education data to fill')
      return
    }

    const eduSelectors = WorkdayFiller.SELECTORS.education

    try {
      // Check if we need to add a new education entry
      const existingEducation = document.querySelectorAll('[data-automation-id="educationCard"]')

      if (existingEducation.length === 0) {
        const addButton = this.findElement(eduSelectors.addButton)
        if (addButton) {
          addButton.click()
          await this.delay(500)
        }
      }

      // Fill most recent education
      const edu = profileData.education[0]

      // School
      if (edu.school) {
        const schoolInput = await this.waitForElement(eduSelectors.school, 2000)
        if (schoolInput) {
          await this.fillWorkdayField(schoolInput, edu.school)
        }
      }

      // Degree (often a dropdown)
      if (edu.degree) {
        const degreeElement = this.findElement(eduSelectors.degree)
        if (degreeElement) {
          if (degreeElement.tagName === 'BUTTON' || degreeElement.getAttribute('role') === 'combobox') {
            await this.fillWorkdayDropdown(degreeElement, edu.degree)
          } else {
            await this.fillWorkdayField(degreeElement, edu.degree)
          }
        }
      }

      // Field of study
      if (edu.field || edu.major) {
        const fieldInput = this.findElement(eduSelectors.fieldOfStudy)
        if (fieldInput) {
          await this.fillWorkdayField(fieldInput, edu.field || edu.major)
        }
      }

      // GPA
      if (edu.gpa) {
        const gpaInput = this.findElement(eduSelectors.gpa)
        if (gpaInput) {
          await this.fillWorkdayField(gpaInput, edu.gpa.toString())
        }
      }

      console.log('[ResuBoost] Filled education')
    } catch (error) {
      this.errors.push({ type: 'education', message: error.message })
      console.warn('[ResuBoost] Education fill error:', error)
    }
  }

  /**
   * Handle resume upload
   * @param {Object} profileData Profile data with resume
   */
  async handleResume(profileData) {
    try {
      const docSelectors = WorkdayFiller.SELECTORS.documents

      // File input
      const uploadInput = this.findElement(docSelectors.resumeUpload)
      if (uploadInput) {
        console.log('[ResuBoost] Resume upload found')

        if (profileData.resumeFile && profileData.resumeFileName) {
          try {
            await this.uploadFile(uploadInput, profileData.resumeFile, profileData.resumeFileName)
            this.filledFields.push({ name: 'resume', type: 'file_upload' })
            console.log('[ResuBoost] Resume uploaded')
          } catch (uploadError) {
            console.warn('[ResuBoost] Could not auto-upload resume:', uploadError)
            this.filledFields.push({ name: 'resume', type: 'file_input_found' })
          }
        } else {
          this.filledFields.push({ name: 'resume', type: 'file_input_found' })
        }
      }

      // LinkedIn import option
      const linkedInImport = this.findElement(docSelectors.linkedInImport)
      if (linkedInImport) {
        console.log('[ResuBoost] LinkedIn import option available')
      }

      // Cover letter
      if (profileData.coverLetter) {
        const coverLetterInput = this.findElement(docSelectors.coverLetter)
        if (coverLetterInput && !coverLetterInput.value) {
          await this.fillWorkdayField(coverLetterInput, profileData.coverLetter)
          console.log('[ResuBoost] Cover letter filled')
        }
      }
    } catch (error) {
      this.errors.push({ type: 'resume', message: error.message })
      console.warn('[ResuBoost] Resume handling error:', error)
    }
  }

  /**
   * Upload file to input
   * @param {HTMLInputElement} input File input
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
   * Fill custom screening questions
   * @param {Object} dataMap Mapped profile data
   * @param {Object} profileData Full profile data
   */
  async fillCustomQuestions(dataMap, profileData) {
    try {
      const questionContainers = document.querySelectorAll(
        WorkdayFiller.SELECTORS.questions.container.join(', ')
      )

      for (const container of questionContainers) {
        if (container.dataset.resuboostFilled === 'true') continue

        await this.fillQuestionContainer(container, dataMap, profileData)
      }
    } catch (error) {
      this.errors.push({ type: 'questions', message: error.message })
      console.warn('[ResuBoost] Questions fill error:', error)
    }
  }

  /**
   * Fill a single question container
   * @param {HTMLElement} container Question container
   * @param {Object} dataMap Mapped data
   * @param {Object} profileData Full profile data
   */
  async fillQuestionContainer(container, dataMap, profileData) {
    const labelElement = container.querySelector(
      WorkdayFiller.SELECTORS.questions.label.join(', ')
    )
    const labelText = (labelElement?.textContent || '').toLowerCase().trim()

    if (!labelText) return

    // Find input elements
    const input = container.querySelector('input[type="text"], input[type="number"], input[type="url"]')
    const textarea = container.querySelector('textarea')
    const select = container.querySelector('select, [role="combobox"]')
    const radios = container.querySelectorAll('input[type="radio"]')
    const checkboxes = container.querySelectorAll('input[type="checkbox"]')

    try {
      // Years of experience
      if (this.matchesPattern(labelText, ['years', 'experience'])) {
        if (input && dataMap.yearsExperience) {
          await this.fillWorkdayField(input, dataMap.yearsExperience.toString())
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Salary
      else if (this.matchesPattern(labelText, ['salary', 'compensation', 'pay'])) {
        if (input && dataMap.salary) {
          await this.fillWorkdayField(input, dataMap.salary.toString())
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Work authorization
      else if (this.matchesPattern(labelText, ['authorized', 'eligible', 'legally', 'right to work'])) {
        if (radios.length > 0) {
          await this.fillYesNoField(container, profileData.workAuthorization !== false)
          container.dataset.resuboostFilled = 'true'
        } else if (select) {
          await this.fillWorkdayDropdown(select, profileData.workAuthorization !== false ? 'Yes' : 'No')
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Sponsorship
      else if (this.matchesPattern(labelText, ['sponsorship', 'visa'])) {
        if (radios.length > 0) {
          await this.fillYesNoField(container, profileData.requiresSponsorship === true)
          container.dataset.resuboostFilled = 'true'
        } else if (select) {
          await this.fillWorkdayDropdown(select, profileData.requiresSponsorship === true ? 'Yes' : 'No')
          container.dataset.resuboostFilled = 'true'
        }
      }
      // LinkedIn
      else if (this.matchesPattern(labelText, ['linkedin'])) {
        if (input && dataMap.linkedIn) {
          await this.fillWorkdayField(input, dataMap.linkedIn)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Remote work
      else if (this.matchesPattern(labelText, ['remote', 'work from home', 'hybrid'])) {
        if (radios.length > 0 && profileData.openToRemote !== undefined) {
          await this.fillYesNoField(container, profileData.openToRemote)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Relocation
      else if (this.matchesPattern(labelText, ['relocate', 'relocation', 'willing to move'])) {
        if (radios.length > 0 && profileData.willingToRelocate !== undefined) {
          await this.fillYesNoField(container, profileData.willingToRelocate)
          container.dataset.resuboostFilled = 'true'
        }
      }
      // Consent/Agreement checkboxes
      else if (checkboxes.length > 0 && this.matchesPattern(labelText, ['agree', 'consent', 'acknowledge', 'terms'])) {
        for (const checkbox of checkboxes) {
          if (!checkbox.checked) {
            checkbox.click()
            this.filledFields.push({ name: checkbox.name || 'consent', type: 'checkbox' })
          }
        }
        container.dataset.resuboostFilled = 'true'
      }
      // Answer templates for text questions
      else if (textarea && !textarea.value) {
        const answer = this.findAnswerTemplate(labelText, profileData.answerTemplates)
        if (answer) {
          await this.fillWorkdayField(textarea, answer)
          container.dataset.resuboostFilled = 'true'
        }
      }
    } catch (error) {
      console.warn(`[ResuBoost] Could not fill question "${labelText}":`, error)
    }
  }

  /**
   * Fill all visible fields (fallback for unknown sections)
   * @param {Object} dataMap Mapped profile data
   * @param {Object} profileData Full profile data
   */
  async fillAllVisibleFields(dataMap, profileData) {
    // Try all field types
    await this.fillPersonalInfo(dataMap)
    await this.fillContactInfo(dataMap)
    await this.fillCustomQuestions(dataMap, profileData)
  }

  /**
   * Find Workday input by automation ID or selector
   * @param {string[]} selectors Selectors to try
   * @returns {HTMLElement|null} Input element
   */
  findElement(selectors) {
    if (!Array.isArray(selectors)) {
      return document.querySelector(selectors)
    }

    for (const selector of selectors) {
      try {
        // Try exact automation-id match first
        let element = document.querySelector(`[data-automation-id="${selector.replace('[data-automation-id="', '').replace('"]', '')}"]`)
        if (element) return element

        // Try as CSS selector
        element = document.querySelector(selector)
        if (element) return element
      } catch (e) {
        continue
      }
    }

    return null
  }

  /**
   * Fill a Workday field with proper event handling
   * Workday uses React and needs specific event dispatching
   * @param {HTMLElement} input Input element
   * @param {string} value Value to fill
   */
  async fillWorkdayField(input, value) {
    if (!input || !value) return

    try {
      // Check if it's a Workday dropdown component
      const isDropdown = input.getAttribute('role') === 'combobox' ||
                         input.closest('[data-automation-id*="dropdown"]') !== null ||
                         input.tagName === 'BUTTON'

      if (isDropdown) {
        await this.fillWorkdayDropdown(input, value)
        return
      }

      // Focus the input
      input.focus()
      await this.delay(50)

      // Clear existing value
      input.value = ''

      // Set new value using native setter for React compatibility
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        'value'
      )?.set || Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        'value'
      )?.set

      if (nativeInputValueSetter) {
        nativeInputValueSetter.call(input, value)
      } else {
        input.value = value
      }

      // Dispatch events in order Workday expects
      input.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }))
      input.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }))

      // Workday often uses blur to validate
      await this.delay(50)
      input.dispatchEvent(new Event('blur', { bubbles: true }))

      this.filledFields.push({
        name: input.name || input.getAttribute('data-automation-id') || 'text',
        type: input.tagName === 'TEXTAREA' ? 'textarea' : 'text',
      })
    } catch (error) {
      console.warn('[ResuBoost] Error filling Workday field:', error)
    }
  }

  /**
   * Fill Workday dropdown/select component
   * Workday dropdowns are custom React components
   * @param {HTMLElement} element Dropdown trigger element
   * @param {string} value Value to select
   */
  async fillWorkdayDropdown(element, value) {
    try {
      // Click to open dropdown
      element.click()
      await this.delay(300)

      const valueLower = value.toLowerCase()

      // Look for search input
      const searchInput = document.querySelector(
        WorkdayFiller.SELECTORS.dropdown.search.join(', ')
      )

      if (searchInput) {
        // Type in search box
        searchInput.focus()
        searchInput.value = value
        searchInput.dispatchEvent(new Event('input', { bubbles: true }))
        await this.delay(300)
      }

      // Find options
      const options = document.querySelectorAll(
        WorkdayFiller.SELECTORS.dropdown.options.join(', ')
      )

      for (const option of options) {
        const optionText = (option.textContent || '').toLowerCase().trim()

        if (optionText === valueLower ||
            optionText.includes(valueLower) ||
            valueLower.includes(optionText)) {
          option.click()
          await this.delay(100)
          this.filledFields.push({
            name: element.getAttribute('data-automation-id') || 'dropdown',
            type: 'select',
          })
          return
        }
      }

      // If no match found, close dropdown
      document.body.click()
      console.warn(`[ResuBoost] No matching option found for: ${value}`)
    } catch (error) {
      console.warn('[ResuBoost] Error filling Workday dropdown:', error)
      document.body.click() // Ensure dropdown is closed
    }
  }

  /**
   * Fill Yes/No question field
   * @param {HTMLElement} container Question container
   * @param {boolean} value True for Yes, False for No
   */
  async fillYesNoField(container, value) {
    const radios = container.querySelectorAll('input[type="radio"]')

    for (const radio of radios) {
      const label = this.getLabelText(radio).toLowerCase()
      const radioValue = radio.value.toLowerCase()

      const isYes = radioValue === 'yes' ||
                    radioValue === '1' ||
                    radioValue === 'true' ||
                    label.includes('yes')

      const isNo = radioValue === 'no' ||
                   radioValue === '0' ||
                   radioValue === 'false' ||
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

    // Also try dropdown if radios didn't work
    const select = container.querySelector('select, [role="combobox"]')
    if (select) {
      await this.fillWorkdayDropdown(select, value ? 'Yes' : 'No')
    }
  }

  /**
   * Find answer template for question
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
   * Click next button to proceed to next page
   * @returns {boolean} True if clicked successfully
   */
  async clickNextButton() {
    try {
      const nextButton = this.findElement(WorkdayFiller.SELECTORS.navigation.next)
      if (nextButton && !nextButton.disabled) {
        nextButton.click()
        await this.waitForWorkdayLoad()
        return true
      }
    } catch (error) {
      console.warn('[ResuBoost] Could not click next:', error)
    }
    return false
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
        'h1[data-automation-id]',
      ]),
      company: this.extractText([
        '[data-automation-id="companyName"]',
        '.css-1q2dra3 .company',
        '[data-automation-id="organization"]',
      ]),
      location: this.extractText([
        '[data-automation-id="locations"]',
        '[data-automation-id="jobPostingLocation"]',
        '.locations',
        '[data-automation-id="location"]',
      ]),
      description: this.extractText([
        '[data-automation-id="jobPostingDescription"]',
        '.job-description',
        '[data-automation-id="description"]',
      ]),
      jobId: this.extractText([
        '[data-automation-id="jobReqId"]',
        '[data-automation-id="jobPostingJobReqId"]',
        '[data-automation-id="requisitionId"]',
      ]),
      postedDate: this.extractText([
        '[data-automation-id="postedOn"]',
        '[data-automation-id="jobPostingDate"]',
      ]),
      department: this.extractText([
        '[data-automation-id="department"]',
        '[data-automation-id="jobFamily"]',
      ]),
      employmentType: this.extractText([
        '[data-automation-id="employmentType"]',
        '[data-automation-id="time-type"]',
      ]),
    }
  }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.WorkdayFiller = WorkdayFiller
}
