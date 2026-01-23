/**
 * Generic Form Filler
 * Base class for all form fillers with comprehensive field detection
 *
 * This filler works on any job application form by:
 * - Detecting fields via autocomplete attributes (HTML5 standard)
 * - Matching field labels and placeholders
 * - Using name/id patterns common in forms
 * - Supporting all input types: text, email, tel, select, radio, checkbox, textarea
 *
 * Other platform-specific fillers extend this class to inherit
 * the generic detection patterns while adding platform-specific selectors.
 */

class GenericFiller {
  constructor() {
    this.platform = 'generic'
    this.filledFields = []
    this.errors = []
  }

  /**
   * Field pattern definitions for detecting input fields
   * Organized by field type with multiple detection methods
   */
  static FIELD_PATTERNS = {
    // Personal information patterns
    firstName: {
      autocomplete: ['given-name', 'first-name', 'fname'],
      name: ['firstname', 'first_name', 'first-name', 'fname', 'given_name', 'givenname'],
      id: ['firstname', 'first_name', 'first-name', 'fname', 'given-name'],
      label: ['first name', 'first', 'given name', 'forename'],
      placeholder: ['first name', 'first', 'given name'],
    },
    lastName: {
      autocomplete: ['family-name', 'last-name', 'lname'],
      name: ['lastname', 'last_name', 'last-name', 'lname', 'family_name', 'familyname', 'surname'],
      id: ['lastname', 'last_name', 'last-name', 'lname', 'family-name'],
      label: ['last name', 'last', 'family name', 'surname'],
      placeholder: ['last name', 'last', 'family name', 'surname'],
    },
    fullName: {
      autocomplete: ['name', 'full-name'],
      name: ['name', 'fullname', 'full_name', 'full-name', 'applicant_name'],
      id: ['name', 'fullname', 'full_name', 'full-name'],
      label: ['full name', 'your name', 'name'],
      placeholder: ['full name', 'your name', 'name'],
    },

    // Contact information patterns
    email: {
      autocomplete: ['email'],
      type: ['email'],
      name: ['email', 'e-mail', 'email_address', 'emailaddress', 'useremail'],
      id: ['email', 'e-mail', 'emailaddress'],
      label: ['email', 'e-mail', 'email address'],
      placeholder: ['email', 'e-mail', 'your email'],
    },
    phone: {
      autocomplete: ['tel', 'tel-national', 'tel-local', 'mobile'],
      type: ['tel'],
      name: ['phone', 'telephone', 'mobile', 'phone_number', 'phonenumber', 'tel', 'cellphone', 'cell'],
      id: ['phone', 'telephone', 'mobile', 'phonenumber', 'tel'],
      label: ['phone', 'telephone', 'mobile', 'phone number', 'cell phone', 'contact number'],
      placeholder: ['phone', 'telephone', 'mobile', 'phone number', '(xxx) xxx-xxxx'],
    },

    // Address patterns
    address: {
      autocomplete: ['street-address', 'address-line1'],
      name: ['address', 'street', 'address1', 'address_line1', 'streetaddress'],
      id: ['address', 'street', 'address1', 'addressline1'],
      label: ['address', 'street address', 'address line 1'],
      placeholder: ['address', 'street address', 'enter your address'],
    },
    city: {
      autocomplete: ['address-level2'],
      name: ['city', 'town', 'locality'],
      id: ['city', 'town', 'locality'],
      label: ['city', 'town'],
      placeholder: ['city', 'town'],
    },
    state: {
      autocomplete: ['address-level1'],
      name: ['state', 'province', 'region', 'state_province'],
      id: ['state', 'province', 'region'],
      label: ['state', 'province', 'region', 'state/province'],
      placeholder: ['state', 'province', 'region', 'select state'],
    },
    zipCode: {
      autocomplete: ['postal-code', 'zip'],
      name: ['zip', 'zipcode', 'zip_code', 'postal', 'postalcode', 'postal_code'],
      id: ['zip', 'zipcode', 'postalcode', 'postal'],
      label: ['zip', 'zip code', 'postal code', 'post code'],
      placeholder: ['zip', 'zip code', 'postal code', '12345'],
    },
    country: {
      autocomplete: ['country-name', 'country'],
      name: ['country', 'nation', 'country_code'],
      id: ['country', 'nation'],
      label: ['country', 'nation'],
      placeholder: ['country', 'select country'],
    },

    // Professional links patterns
    linkedIn: {
      autocomplete: ['url'],
      name: ['linkedin', 'linkedin_url', 'linkedinurl', 'linkedin_profile'],
      id: ['linkedin', 'linkedinurl'],
      label: ['linkedin', 'linkedin profile', 'linkedin url'],
      placeholder: ['linkedin', 'linkedin.com/in/', 'linkedin profile url'],
    },
    website: {
      autocomplete: ['url'],
      name: ['website', 'portfolio', 'personal_site', 'personalsite', 'url', 'personalwebsite'],
      id: ['website', 'portfolio', 'personalsite'],
      label: ['website', 'portfolio', 'personal website', 'personal site'],
      placeholder: ['website', 'portfolio', 'https://'],
    },
    github: {
      autocomplete: ['url'],
      name: ['github', 'github_url', 'githuburl', 'github_profile'],
      id: ['github', 'githuburl'],
      label: ['github', 'github profile', 'github url'],
      placeholder: ['github', 'github.com/', 'github profile'],
    },
    twitter: {
      autocomplete: ['url'],
      name: ['twitter', 'twitter_url', 'twitterurl', 'twitter_handle'],
      id: ['twitter', 'twitterurl'],
      label: ['twitter', 'twitter profile', 'twitter handle'],
      placeholder: ['twitter', 'twitter.com/', '@username'],
    },

    // Professional information patterns
    currentCompany: {
      name: ['company', 'current_company', 'currentcompany', 'employer', 'organization', 'org'],
      id: ['company', 'currentcompany', 'employer', 'organization'],
      label: ['company', 'current company', 'employer', 'organization'],
      placeholder: ['company', 'current company', 'employer name'],
    },
    currentTitle: {
      name: ['title', 'job_title', 'jobtitle', 'current_title', 'position', 'role'],
      id: ['title', 'jobtitle', 'currenttitle', 'position'],
      label: ['title', 'job title', 'current title', 'position', 'role'],
      placeholder: ['title', 'job title', 'your title', 'current position'],
    },
    yearsExperience: {
      name: ['experience', 'years', 'years_experience', 'yearsexperience', 'work_experience'],
      id: ['experience', 'yearsexperience', 'years'],
      label: ['years', 'experience', 'years of experience', 'work experience'],
      placeholder: ['years', 'years of experience', 'e.g. 5'],
    },
    salary: {
      name: ['salary', 'desired_salary', 'salary_expectation', 'compensation', 'pay'],
      id: ['salary', 'desiredsalary', 'compensation'],
      label: ['salary', 'desired salary', 'expected salary', 'compensation', 'salary expectation'],
      placeholder: ['salary', 'expected salary', '$', 'e.g. 100000'],
    },
  }

  /**
   * Common Yes/No question patterns for work authorization, sponsorship, etc.
   */
  static YES_NO_PATTERNS = {
    workAuthorization: [
      'authorized to work',
      'legally authorized',
      'eligible to work',
      'work authorization',
      'legally eligible',
      'right to work',
      'work in the',
      'permitted to work',
    ],
    requiresSponsorship: [
      'sponsorship',
      'visa sponsorship',
      'require sponsorship',
      'need sponsorship',
      'immigration sponsorship',
    ],
    willingToRelocate: [
      'relocate',
      'willing to move',
      'relocation',
      'willing to relocate',
      'open to relocation',
    ],
    openToRemote: [
      'remote',
      'work from home',
      'wfh',
      'hybrid',
      'work remotely',
      'remote work',
    ],
    backgroundCheck: [
      'background check',
      'background investigation',
      'consent to background',
    ],
    ageVerification: [
      '18 years',
      'over 18',
      'at least 18',
      'of legal age',
      'legally of age',
    ],
  }

  /**
   * Fill form with profile data
   * @param {Object} profileData User profile data
   * @returns {Object} Result with filled fields and errors
   */
  async fill(profileData) {
    this.filledFields = []
    this.errors = []

    try {
      const dataMap = this.mapProfileData(profileData)

      console.log('[ResuBoost] Starting generic form fill')

      // Phase 1: Fill text inputs and textareas
      await this.fillTextFields(dataMap)

      // Phase 2: Fill email and phone inputs
      await this.fillContactFields(dataMap)

      // Phase 3: Fill select dropdowns
      await this.fillSelectFields(dataMap)

      // Phase 4: Fill radio buttons (Yes/No questions)
      await this.fillRadioFields(profileData)

      // Phase 5: Fill checkboxes (consents, terms)
      await this.fillCheckboxFields()

      // Phase 6: Try to detect file upload for resume
      this.detectFileUpload()

      console.log(`[ResuBoost] Filled ${this.filledFields.length} fields`)

      return {
        success: true,
        filledFields: this.filledFields,
        errors: this.errors,
      }
    } catch (error) {
      console.error('[ResuBoost] Generic fill error:', error)
      this.errors.push({ type: 'general', message: error.message })
      return {
        success: false,
        filledFields: this.filledFields,
        errors: this.errors,
      }
    }
  }

  /**
   * Map profile data to standardized field names
   * @param {Object} profileData Raw profile data
   * @returns {Object} Mapped data
   */
  mapProfileData(profileData) {
    if (!profileData) return {}

    return {
      // Personal info
      firstName: profileData.firstName || profileData.first_name || '',
      lastName: profileData.lastName || profileData.last_name || '',
      fullName: profileData.fullName || `${profileData.firstName || ''} ${profileData.lastName || ''}`.trim(),

      // Contact
      email: profileData.email || '',
      phone: profileData.phone || profileData.phoneNumber || profileData.phone_number || '',

      // Address
      address: profileData.address || profileData.street || profileData.addressLine1 || '',
      city: profileData.city || '',
      state: profileData.state || profileData.province || '',
      zipCode: profileData.zipCode || profileData.zip || profileData.postalCode || '',
      country: profileData.country || 'United States',

      // Professional links
      linkedIn: profileData.linkedIn || profileData.linkedin || profileData.linkedinUrl || '',
      website: profileData.website || profileData.portfolio || '',
      github: profileData.github || profileData.githubUrl || '',
      twitter: profileData.twitter || '',

      // Professional info
      currentCompany: profileData.currentCompany || profileData.company || profileData.employer || '',
      currentTitle: profileData.currentTitle || profileData.title || profileData.position || '',
      yearsExperience: profileData.yearsExperience || profileData.experience || '',
      salary: profileData.salary || profileData.desiredSalary || '',

      // Extra
      coverLetter: profileData.coverLetter || '',
    }
  }

  /**
   * Fill text input fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillTextFields(dataMap) {
    const textInputs = document.querySelectorAll(
      'input[type="text"], input:not([type]), textarea'
    )

    for (const input of textInputs) {
      // Skip if already filled or readonly
      if (input.value || input.disabled || input.readOnly) continue

      // Skip hidden inputs
      if (input.type === 'hidden' || !input.offsetParent) continue

      try {
        const fieldType = this.detectFieldType(input)

        if (fieldType && dataMap[fieldType]) {
          await this.fillField(input, dataMap[fieldType])
          console.log(`[ResuBoost] Filled text field: ${fieldType}`)
        }
      } catch (error) {
        console.warn('[ResuBoost] Error filling text field:', error)
      }
    }
  }

  /**
   * Fill email and phone specific inputs
   * @param {Object} dataMap Mapped profile data
   */
  async fillContactFields(dataMap) {
    // Email inputs
    const emailInputs = document.querySelectorAll('input[type="email"]')
    for (const input of emailInputs) {
      if (!input.value && !input.disabled && dataMap.email) {
        await this.fillField(input, dataMap.email)
        console.log('[ResuBoost] Filled email field')
      }
    }

    // Phone inputs
    const phoneInputs = document.querySelectorAll('input[type="tel"]')
    for (const input of phoneInputs) {
      if (!input.value && !input.disabled && dataMap.phone) {
        await this.fillField(input, dataMap.phone)
        console.log('[ResuBoost] Filled phone field')
      }
    }

    // URL inputs (for links)
    const urlInputs = document.querySelectorAll('input[type="url"]')
    for (const input of urlInputs) {
      if (input.value || input.disabled) continue

      const fieldType = this.detectFieldType(input)
      if (fieldType && dataMap[fieldType]) {
        await this.fillField(input, dataMap[fieldType])
        console.log(`[ResuBoost] Filled URL field: ${fieldType}`)
      }
    }
  }

  /**
   * Fill select dropdown fields
   * @param {Object} dataMap Mapped profile data
   */
  async fillSelectFields(dataMap) {
    const selectElements = document.querySelectorAll('select')

    for (const select of selectElements) {
      // Skip if already selected (not on first option) or disabled
      if (select.selectedIndex > 0 || select.disabled) continue

      try {
        const fieldType = this.detectFieldType(select)

        if (fieldType && dataMap[fieldType]) {
          await this.fillSelect(select, dataMap[fieldType])
          console.log(`[ResuBoost] Filled select: ${fieldType}`)
        }
      } catch (error) {
        console.warn('[ResuBoost] Error filling select:', error)
      }
    }
  }

  /**
   * Fill radio button fields (typically Yes/No questions)
   * @param {Object} profileData Full profile data
   */
  async fillRadioFields(profileData) {
    // Find all radio groups by name
    const radioNames = new Set()
    document.querySelectorAll('input[type="radio"]').forEach((radio) => {
      if (radio.name) radioNames.add(radio.name)
    })

    for (const name of radioNames) {
      const radios = document.querySelectorAll(`input[type="radio"][name="${name}"]`)
      if (radios.length === 0) continue

      // Skip if already answered
      const hasChecked = Array.from(radios).some((r) => r.checked)
      if (hasChecked) continue

      try {
        // Get container or label text to understand the question
        const container = radios[0].closest('fieldset, .field, .question, div')
        const containerText = (container?.textContent || '').toLowerCase()

        // Match against Yes/No patterns
        for (const [patternKey, patterns] of Object.entries(GenericFiller.YES_NO_PATTERNS)) {
          if (patterns.some((p) => containerText.includes(p))) {
            let shouldBeYes = false

            switch (patternKey) {
              case 'workAuthorization':
                shouldBeYes = profileData.workAuthorization !== false
                break
              case 'requiresSponsorship':
                shouldBeYes = profileData.requiresSponsorship === true
                break
              case 'willingToRelocate':
                shouldBeYes = profileData.willingToRelocate === true
                break
              case 'openToRemote':
                shouldBeYes = profileData.openToRemote === true
                break
              case 'backgroundCheck':
                shouldBeYes = true // Typically should consent to background check
                break
              case 'ageVerification':
                shouldBeYes = true // Should confirm 18+
                break
            }

            await this.selectRadioByValue(radios, shouldBeYes)
            console.log(`[ResuBoost] Filled radio group: ${patternKey} = ${shouldBeYes}`)
            break
          }
        }
      } catch (error) {
        console.warn('[ResuBoost] Error filling radio group:', error)
      }
    }
  }

  /**
   * Select radio button based on Yes/No value
   * @param {NodeList} radios Radio buttons
   * @param {boolean} selectYes True to select Yes option
   */
  async selectRadioByValue(radios, selectYes) {
    for (const radio of radios) {
      const labelText = this.getLabelText(radio).toLowerCase()
      const value = (radio.value || '').toLowerCase()

      const isYes = value === 'yes' ||
                    value === 'true' ||
                    value === '1' ||
                    labelText.includes('yes')

      const isNo = value === 'no' ||
                   value === 'false' ||
                   value === '0' ||
                   labelText.includes('no')

      if ((selectYes && isYes) || (!selectYes && isNo)) {
        radio.click()
        await this.delay(50)
        this.filledFields.push({ name: radio.name || 'radio', type: 'radio' })
        return
      }
    }
  }

  /**
   * Fill checkbox fields (consent, terms, agreements)
   */
  async fillCheckboxFields() {
    const checkboxes = document.querySelectorAll('input[type="checkbox"]')

    for (const checkbox of checkboxes) {
      if (checkbox.checked || checkbox.disabled) continue

      const container = checkbox.closest('label, .field, div')
      const text = (container?.textContent || '').toLowerCase()

      // Auto-check consent/agreement checkboxes
      const shouldCheck =
        text.includes('agree') ||
        text.includes('consent') ||
        text.includes('acknowledge') ||
        text.includes('terms') ||
        text.includes('privacy') ||
        text.includes('accept')

      if (shouldCheck) {
        checkbox.click()
        this.filledFields.push({
          name: checkbox.name || 'checkbox',
          type: 'checkbox',
        })
        console.log('[ResuBoost] Checked consent checkbox')
      }
    }
  }

  /**
   * Detect file upload inputs for resume
   */
  detectFileUpload() {
    const fileInputs = document.querySelectorAll('input[type="file"]')

    for (const input of fileInputs) {
      const name = (input.name || '').toLowerCase()
      const id = (input.id || '').toLowerCase()
      const accept = (input.accept || '').toLowerCase()
      const label = this.getLabelText(input).toLowerCase()

      const isResume =
        name.includes('resume') ||
        name.includes('cv') ||
        id.includes('resume') ||
        id.includes('cv') ||
        label.includes('resume') ||
        label.includes('cv') ||
        accept.includes('.pdf') ||
        accept.includes('.doc')

      if (isResume) {
        this.filledFields.push({ name: 'resume', type: 'file_input_found' })
        console.log('[ResuBoost] Resume upload field found')
        return
      }
    }
  }

  /**
   * Detect field type based on various attributes
   * @param {HTMLElement} element Input element
   * @returns {string|null} Field type or null
   */
  detectFieldType(element) {
    const autocomplete = (element.autocomplete || '').toLowerCase()
    const name = (element.name || '').toLowerCase()
    const id = (element.id || '').toLowerCase()
    const placeholder = (element.placeholder || '').toLowerCase()
    const label = this.getLabelText(element).toLowerCase()
    const type = (element.type || '').toLowerCase()

    for (const [fieldType, patterns] of Object.entries(GenericFiller.FIELD_PATTERNS)) {
      // Check autocomplete attribute first (most reliable)
      if (patterns.autocomplete && patterns.autocomplete.some((p) => autocomplete.includes(p))) {
        return fieldType
      }

      // Check input type (for email, tel)
      if (patterns.type && patterns.type.some((p) => type === p)) {
        return fieldType
      }

      // Check name attribute
      if (patterns.name && patterns.name.some((p) => name.includes(p))) {
        return fieldType
      }

      // Check id attribute
      if (patterns.id && patterns.id.some((p) => id.includes(p))) {
        return fieldType
      }

      // Check label text
      if (patterns.label && patterns.label.some((p) => label.includes(p))) {
        return fieldType
      }

      // Check placeholder
      if (patterns.placeholder && patterns.placeholder.some((p) => placeholder.includes(p))) {
        return fieldType
      }
    }

    return null
  }

  /**
   * Get label text for an input element
   * @param {HTMLElement} input Input element
   * @returns {string} Label text
   */
  getLabelText(input) {
    // Try explicit label via for attribute
    if (input.id) {
      const label = document.querySelector(`label[for="${input.id}"]`)
      if (label) return label.textContent || ''
    }

    // Try aria-label
    const ariaLabel = input.getAttribute('aria-label')
    if (ariaLabel) return ariaLabel

    // Try aria-labelledby
    const labelledBy = input.getAttribute('aria-labelledby')
    if (labelledBy) {
      const labelElement = document.getElementById(labelledBy)
      if (labelElement) return labelElement.textContent || ''
    }

    // Try parent label
    const parentLabel = input.closest('label')
    if (parentLabel) return parentLabel.textContent || ''

    // Try previous sibling label
    const prevSibling = input.previousElementSibling
    if (prevSibling?.tagName === 'LABEL') {
      return prevSibling.textContent || ''
    }

    // Try container with label class
    const container = input.closest('.field, .form-group, .form-field')
    if (container) {
      const labelElement = container.querySelector('label, .label, .field-label')
      if (labelElement) return labelElement.textContent || ''
    }

    return ''
  }

  /**
   * Fill an input field with proper event handling
   * @param {HTMLElement} input Input element
   * @param {string} value Value to fill
   */
  async fillField(input, value) {
    if (!input || !value) return

    // Focus the input
    input.focus()
    await this.delay(50)

    // Clear existing value
    input.value = ''

    // Set new value
    // Use native setter for React compatibility
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      'value'
    )?.set

    const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype,
      'value'
    )?.set

    const setter = input.tagName === 'TEXTAREA' ? nativeTextAreaValueSetter : nativeInputValueSetter

    if (setter) {
      setter.call(input, value)
    } else {
      input.value = value
    }

    // Dispatch events
    input.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }))
    input.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }))

    // Blur to trigger validation
    await this.delay(50)
    input.dispatchEvent(new Event('blur', { bubbles: true }))

    this.filledFields.push({
      name: input.name || input.id || 'text',
      type: input.tagName === 'TEXTAREA' ? 'textarea' : 'text',
    })
  }

  /**
   * Fill a select dropdown
   * @param {HTMLSelectElement} select Select element
   * @param {string} value Value to select
   */
  async fillSelect(select, value) {
    if (!select || !value) return

    const valueLower = value.toLowerCase()

    // Try exact match first
    for (const option of select.options) {
      const optionText = (option.text || '').toLowerCase()
      const optionValue = (option.value || '').toLowerCase()

      if (optionValue === valueLower || optionText === valueLower) {
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        this.filledFields.push({
          name: select.name || select.id || 'select',
          type: 'select',
        })
        return
      }
    }

    // Try partial match
    for (const option of select.options) {
      const optionText = (option.text || '').toLowerCase()

      if (optionText.includes(valueLower) || valueLower.includes(optionText)) {
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        this.filledFields.push({
          name: select.name || select.id || 'select',
          type: 'select',
        })
        return
      }
    }

    // For numeric values, try range matching
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
            this.filledFields.push({
              name: select.name || select.id || 'select',
              type: 'select',
            })
            return
          }
        }
      }
    }
  }

  /**
   * Extract text content from first matching selector
   * @param {string[]} selectors Selectors to try
   * @returns {string} Text content or empty string
   */
  extractText(selectors) {
    for (const selector of selectors) {
      try {
        const element = document.querySelector(selector)
        if (element) {
          // For img elements, return alt text
          if (element.tagName === 'IMG') {
            return element.alt || ''
          }
          return (element.textContent || '').trim()
        }
      } catch (e) {
        continue
      }
    }
    return ''
  }

  /**
   * Check if text matches any of the patterns
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
   * Extract job details from page (generic implementation)
   * @returns {Object} Job details
   */
  extractJobDetails() {
    return {
      title: this.extractText([
        'h1',
        '.job-title',
        '.posting-title',
        '[class*="job-title"]',
        '[class*="jobtitle"]',
      ]),
      company: this.extractText([
        '.company-name',
        '[class*="company"]',
        '[class*="employer"]',
        '[class*="organization"]',
      ]),
      location: this.extractText([
        '.job-location',
        '.location',
        '[class*="location"]',
      ]),
      description: this.extractText([
        '.job-description',
        '.description',
        '[class*="description"]',
        '#job-details',
      ]),
    }
  }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.GenericFiller = GenericFiller
}
