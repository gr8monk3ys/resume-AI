/**
 * Platform Detector
 * Detects which ATS (Applicant Tracking System) platform the current page belongs to
 */

class PlatformDetector {
  constructor() {
    this.platforms = [
      {
        name: 'linkedin',
        patterns: [
          /linkedin\.com\/jobs/i,
          /linkedin\.com\/talent/i,
        ],
        selectors: [
          '.jobs-apply-button',
          '.jobs-easy-apply-button',
          '[data-job-id]',
        ],
      },
      {
        name: 'greenhouse',
        patterns: [
          /boards\.greenhouse\.io/i,
          /jobs\.greenhouse\.io/i,
        ],
        selectors: [
          '#application',
          '.application-form',
          '[data-controller="application"]',
        ],
      },
      {
        name: 'lever',
        patterns: [
          /jobs\.lever\.co/i,
        ],
        selectors: [
          '.application-form',
          '[data-qa="application-form"]',
          '.posting-apply',
        ],
      },
      {
        name: 'workday',
        patterns: [
          /myworkdayjobs\.com/i,
          /\.workday\.com/i,
        ],
        selectors: [
          '[data-automation-id="jobPostingPage"]',
          '[data-automation-id="applyButton"]',
          '.wd-icon-briefcase',
        ],
      },
      {
        name: 'icims',
        patterns: [
          /icims\.com/i,
        ],
        selectors: [
          '.iCIMS_JobContent',
          '#iCIMS_Header',
          '.iCIMS_MainWrapper',
        ],
      },
      {
        name: 'smartrecruiters',
        patterns: [
          /smartrecruiters\.com/i,
        ],
        selectors: [
          '[data-test="header-apply-button"]',
          '.job-details',
          '.smrtr-app',
        ],
      },
      {
        name: 'ashby',
        patterns: [
          /ashbyhq\.com/i,
        ],
        selectors: [
          '[data-testid="job-application-form"]',
          '.ashby-application-form',
        ],
      },
      {
        name: 'bamboohr',
        patterns: [
          /bamboohr\.com\/careers/i,
          /bamboohr\.com\/jobs/i,
        ],
        selectors: [
          '.BambooHR-ATS-board',
          '[data-bamboohr-ats]',
        ],
      },
      {
        name: 'breezy',
        patterns: [
          /breezy\.hr/i,
        ],
        selectors: [
          '.breezy-application',
          '[data-breezy-form]',
        ],
      },
      {
        name: 'indeed',
        patterns: [
          /indeed\.com/i,
        ],
        selectors: [
          '#apply-button',
          '.jobsearch-IndeedApplyButton',
          '#indeedApplyButton',
        ],
      },
    ]
  }

  /**
   * Detect the current platform based on URL and DOM elements
   * @returns {string|null} Platform name or null if not detected
   */
  detect() {
    const url = window.location.href

    for (const platform of this.platforms) {
      // Check URL patterns
      const urlMatch = platform.patterns.some((pattern) => pattern.test(url))

      if (urlMatch) {
        // Verify with DOM selectors if available
        if (this.verifyWithSelectors(platform.selectors)) {
          return platform.name
        }
        // If URL matches but no selectors found, still return the platform
        // (page might be loading or using different layout)
        return platform.name
      }
    }

    // Check selectors only (for embedded forms)
    for (const platform of this.platforms) {
      if (this.verifyWithSelectors(platform.selectors)) {
        return platform.name
      }
    }

    return null
  }

  /**
   * Verify platform by checking for specific DOM selectors
   * @param {string[]} selectors CSS selectors to check
   * @returns {boolean} True if any selector matches
   */
  verifyWithSelectors(selectors) {
    return selectors.some((selector) => {
      try {
        return document.querySelector(selector) !== null
      } catch (e) {
        console.warn(`[ResuBoost] Invalid selector: ${selector}`)
        return false
      }
    })
  }

  /**
   * Check if the current page has an application form
   * @returns {boolean} True if application form is detected
   */
  hasApplicationForm() {
    const formIndicators = [
      // Generic form elements
      'form[action*="apply"]',
      'form[action*="application"]',
      'form[id*="apply"]',
      'form[id*="application"]',
      'form[class*="apply"]',
      'form[class*="application"]',

      // Common input fields for job applications
      'input[name*="resume"]',
      'input[name*="cv"]',
      'input[type="file"][accept*="pdf"]',
      'input[name*="first_name"]',
      'input[name*="firstName"]',
      'input[name*="last_name"]',
      'input[name*="lastName"]',

      // Apply buttons
      'button[type="submit"][class*="apply"]',
      'button[id*="apply"]',
      'a[href*="apply"]',
    ]

    return formIndicators.some((selector) => {
      try {
        return document.querySelector(selector) !== null
      } catch (e) {
        return false
      }
    })
  }

  /**
   * Get detailed information about the detected platform
   * @returns {Object} Platform information including features and selectors
   */
  getDetails() {
    const platform = this.detect()

    if (!platform) {
      return {
        platform: null,
        supported: false,
        hasForm: this.hasApplicationForm(),
      }
    }

    const platformConfig = this.platforms.find((p) => p.name === platform)

    return {
      platform,
      supported: true,
      hasForm: this.hasApplicationForm(),
      selectors: platformConfig?.selectors || [],
    }
  }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.PlatformDetector = PlatformDetector
}
