/**
 * Generic Form Filler
 * Base class for all platform-specific fillers
 * Provides common field detection and filling functionality
 */

class GenericFiller {
  constructor() {
    this.filledFields = []
    this.fieldMappings = {
      // Personal Information
      firstName: [
        'first_name', 'firstname', 'first-name', 'fname',
        'given_name', 'givenname', 'given-name',
        'applicant.firstName', 'candidate_first_name',
      ],
      lastName: [
        'last_name', 'lastname', 'last-name', 'lname',
        'family_name', 'familyname', 'family-name', 'surname',
        'applicant.lastName', 'candidate_last_name',
      ],
      email: [
        'email', 'e-mail', 'email_address', 'emailaddress',
        'applicant.email', 'candidate_email',
      ],
      phone: [
        'phone', 'phone_number', 'phonenumber', 'phone-number',
        'telephone', 'tel', 'mobile', 'cell',
        'applicant.phone', 'candidate_phone',
      ],

      // Address
      address: [
        'address', 'street_address', 'streetaddress', 'street',
        'address_line_1', 'address1', 'addressline1',
      ],
      city: [
        'city', 'town', 'locality',
      ],
      state: [
        'state', 'province', 'region', 'administrative_area',
      ],
      zipCode: [
        'zip', 'zipcode', 'zip_code', 'postal_code', 'postalcode', 'postcode',
      ],
      country: [
        'country', 'country_code', 'nation',
      ],

      // Professional
      linkedIn: [
        'linkedin', 'linkedin_url', 'linkedinurl', 'linkedin-url',
        'linkedin_profile', 'linkedinprofile',
      ],
      website: [
        'website', 'portfolio', 'portfolio_url', 'personal_website',
        'url', 'homepage',
      ],
      github: [
        'github', 'github_url', 'githuburl', 'github_profile',
      ],

      // Application specific
      currentCompany: [
        'current_company', 'currentcompany', 'current_employer',
        'company', 'employer',
      ],
      currentTitle: [
        'current_title', 'currenttitle', 'job_title', 'jobtitle',
        'title', 'position', 'current_position',
      ],
      yearsExperience: [
        'years_experience', 'yearsexperience', 'experience_years',
        'years_of_experience', 'total_experience',
      ],
      salary: [
        'salary', 'expected_salary', 'salary_expectation',
        'desired_salary', 'compensation',
      ],
    }
  }

  /**
   * Fill form with profile data
   * @param {Object} profileData User profile data from API
   * @returns {Object} Result with filled fields count
   */
  async fill(profileData) {
    this.filledFields = []

    // Map profile data to form fields
    const dataMap = this.mapProfileData(profileData)

    // Find and fill form inputs
    await this.fillInputFields(dataMap)

    // Handle file uploads (resume)
    // TODO: Implement resume file upload handling

    return {
      success: true,
      filledFields: this.filledFields,
    }
  }

  /**
   * Map profile data to a flat structure for form filling
   * @param {Object} profileData Raw profile data
   * @returns {Object} Mapped data
   */
  mapProfileData(profileData) {
    return {
      firstName: profileData.firstName || profileData.first_name || '',
      lastName: profileData.lastName || profileData.last_name || '',
      email: profileData.email || '',
      phone: profileData.phone || profileData.phoneNumber || '',
      address: profileData.address || profileData.streetAddress || '',
      city: profileData.city || '',
      state: profileData.state || profileData.province || '',
      zipCode: profileData.zipCode || profileData.postalCode || '',
      country: profileData.country || '',
      linkedIn: profileData.linkedIn || profileData.linkedin_url || '',
      website: profileData.website || profileData.portfolio || '',
      github: profileData.github || profileData.github_url || '',
      currentCompany: profileData.currentCompany || profileData.company || '',
      currentTitle: profileData.currentTitle || profileData.title || '',
      yearsExperience: profileData.yearsExperience || '',
      salary: profileData.expectedSalary || profileData.salary || '',
    }
  }

  /**
   * Fill input fields based on mapping
   * @param {Object} dataMap Mapped profile data
   */
  async fillInputFields(dataMap) {
    const inputs = document.querySelectorAll('input, textarea, select')

    for (const input of inputs) {
      const fieldType = this.identifyField(input)

      if (fieldType && dataMap[fieldType]) {
        await this.fillField(input, dataMap[fieldType])
      }
    }
  }

  /**
   * Identify what type of field an input is
   * @param {HTMLElement} input Input element
   * @returns {string|null} Field type or null
   */
  identifyField(input) {
    const name = (input.name || '').toLowerCase()
    const id = (input.id || '').toLowerCase()
    const placeholder = (input.placeholder || '').toLowerCase()
    const label = this.getLabelText(input).toLowerCase()
    const ariaLabel = (input.getAttribute('aria-label') || '').toLowerCase()
    const autocomplete = (input.getAttribute('autocomplete') || '').toLowerCase()

    for (const [fieldType, patterns] of Object.entries(this.fieldMappings)) {
      for (const pattern of patterns) {
        if (
          name.includes(pattern) ||
          id.includes(pattern) ||
          placeholder.includes(pattern) ||
          label.includes(pattern) ||
          ariaLabel.includes(pattern) ||
          autocomplete.includes(pattern)
        ) {
          return fieldType
        }
      }
    }

    // Try to match by autocomplete attribute directly
    const autocompleteMap = {
      'given-name': 'firstName',
      'family-name': 'lastName',
      'email': 'email',
      'tel': 'phone',
      'street-address': 'address',
      'address-level2': 'city',
      'address-level1': 'state',
      'postal-code': 'zipCode',
      'country-name': 'country',
    }

    if (autocompleteMap[autocomplete]) {
      return autocompleteMap[autocomplete]
    }

    return null
  }

  /**
   * Get label text for an input element
   * @param {HTMLElement} input Input element
   * @returns {string} Label text
   */
  getLabelText(input) {
    // Check for associated label via for attribute
    if (input.id) {
      const label = document.querySelector(`label[for="${input.id}"]`)
      if (label) {
        return label.textContent || ''
      }
    }

    // Check for wrapping label
    const parentLabel = input.closest('label')
    if (parentLabel) {
      return parentLabel.textContent || ''
    }

    // Check for aria-labelledby
    const labelledBy = input.getAttribute('aria-labelledby')
    if (labelledBy) {
      const labelElement = document.getElementById(labelledBy)
      if (labelElement) {
        return labelElement.textContent || ''
      }
    }

    return ''
  }

  /**
   * Fill a single field with value
   * @param {HTMLElement} input Input element
   * @param {string} value Value to fill
   */
  async fillField(input, value) {
    if (!value || input.disabled || input.readOnly) {
      return
    }

    // Skip if already has value and matches
    if (input.value === value) {
      return
    }

    // Focus the input
    input.focus()

    if (input.tagName === 'SELECT') {
      await this.fillSelect(input, value)
    } else if (input.type === 'checkbox' || input.type === 'radio') {
      // TODO: Handle checkbox/radio inputs
      return
    } else {
      await this.fillTextInput(input, value)
    }

    // Track filled field
    this.filledFields.push({
      name: input.name || input.id,
      type: input.type || input.tagName.toLowerCase(),
    })
  }

  /**
   * Fill a text input with simulated typing
   * @param {HTMLElement} input Input element
   * @param {string} value Value to type
   */
  async fillTextInput(input, value) {
    // Clear existing value
    input.value = ''

    // Set the value
    input.value = value

    // Dispatch events to trigger validation and React state updates
    input.dispatchEvent(new Event('input', { bubbles: true }))
    input.dispatchEvent(new Event('change', { bubbles: true }))
    input.dispatchEvent(new Event('blur', { bubbles: true }))

    // For React inputs, we may need to set the value via native setter
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      'value'
    )?.set

    if (nativeInputValueSetter) {
      nativeInputValueSetter.call(input, value)
      input.dispatchEvent(new Event('input', { bubbles: true }))
    }
  }

  /**
   * Fill a select dropdown
   * @param {HTMLSelectElement} select Select element
   * @param {string} value Value to select
   */
  async fillSelect(select, value) {
    const valueLower = value.toLowerCase()

    // Try to find matching option
    for (const option of select.options) {
      const optionText = option.text.toLowerCase()
      const optionValue = option.value.toLowerCase()

      if (
        optionValue === valueLower ||
        optionText === valueLower ||
        optionText.includes(valueLower) ||
        valueLower.includes(optionText)
      ) {
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        return
      }
    }
  }

  /**
   * Extract job details from the page
   * @returns {Object} Job details
   */
  extractJobDetails() {
    return {
      title: this.extractText(['h1', '.job-title', '[data-job-title]']),
      company: this.extractText(['.company-name', '[data-company]', '.employer']),
      location: this.extractText(['.location', '.job-location', '[data-location]']),
      description: this.extractText(['.job-description', '.description', '[data-description]']),
      salary: this.extractText(['.salary', '.compensation', '[data-salary]']),
      type: this.extractText(['.job-type', '.employment-type', '[data-job-type]']),
    }
  }

  /**
   * Extract text from first matching selector
   * @param {string[]} selectors CSS selectors to try
   * @returns {string} Extracted text
   */
  extractText(selectors) {
    for (const selector of selectors) {
      try {
        const element = document.querySelector(selector)
        if (element) {
          return element.textContent?.trim() || ''
        }
      } catch (e) {
        continue
      }
    }
    return ''
  }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.GenericFiller = GenericFiller
}
