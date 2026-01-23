/**
 * ResuBoost AI Extension Content Script
 * Main entry point for content script functionality
 * Handles form detection, autofill button injection, progress tracking, and message handling
 */

;(function () {
  'use strict'

  // Prevent multiple injections
  if (window.__resuboostInjected) {
    return
  }
  window.__resuboostInjected = true

  const AUTOFILL_BUTTON_ID = 'resuboost-autofill-btn'
  const PROGRESS_CONTAINER_ID = 'resuboost-progress'
  const NOTIFICATION_ID = 'resuboost-notification'

  /**
   * Notification types for visual feedback
   */
  const NOTIFICATION_TYPES = {
    success: {
      bgColor: '#22c55e',
      icon: '<path d="M20 6L9 17l-5-5"></path>',
    },
    error: {
      bgColor: '#ef4444',
      icon: '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>',
    },
    info: {
      bgColor: '#3b82f6',
      icon: '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>',
    },
    warning: {
      bgColor: '#f59e0b',
      icon: '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>',
    },
  }

  /**
   * Content Script Controller
   * Manages form filling, UI, and communication with background script
   */
  class ContentController {
    constructor() {
      this.detector = new PlatformDetector()
      this.currentPlatform = null
      this.filler = null
      this.isMultiStep = false
      this.currentStep = 0
      this.totalSteps = 0
    }

    /**
     * Initialize the content script
     */
    init() {
      this.injectStyles()
      this.detectPlatform()
      this.setupMessageListener()
      this.injectAutofillButton()
      this.observePageChanges()

      console.log('[ResuBoost] Content script initialized')
    }

    /**
     * Inject required CSS styles
     */
    injectStyles() {
      if (document.getElementById('resuboost-styles')) return

      const style = document.createElement('style')
      style.id = 'resuboost-styles'
      style.textContent = `
        @keyframes resuboost-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        @keyframes resuboost-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        @keyframes resuboost-slide-in {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }

        @keyframes resuboost-slide-out {
          from {
            transform: translateX(0);
            opacity: 1;
          }
          to {
            transform: translateX(100%);
            opacity: 0;
          }
        }

        @keyframes resuboost-field-highlight {
          0% { box-shadow: 0 0 0 2px #3b82f6; }
          100% { box-shadow: 0 0 0 4px #93c5fd; }
        }

        .resuboost-filled-field {
          animation: resuboost-field-highlight 0.3s ease-out;
          outline: 2px solid #22c55e !important;
          outline-offset: 2px;
        }

        #${AUTOFILL_BUTTON_ID} {
          transition: all 0.2s ease;
        }

        #${AUTOFILL_BUTTON_ID}:hover {
          transform: translateY(-2px);
        }

        #${AUTOFILL_BUTTON_ID}:active {
          transform: translateY(0);
        }

        #${AUTOFILL_BUTTON_ID}:disabled {
          cursor: not-allowed;
          opacity: 0.8;
        }

        #${PROGRESS_CONTAINER_ID} {
          animation: resuboost-slide-in 0.3s ease-out;
        }

        #${NOTIFICATION_ID} {
          animation: resuboost-slide-in 0.3s ease-out;
        }

        #${NOTIFICATION_ID}.hiding {
          animation: resuboost-slide-out 0.3s ease-out forwards;
        }
      `
      document.head.appendChild(style)
    }

    /**
     * Detect the current job application platform
     */
    detectPlatform() {
      this.currentPlatform = this.detector.detect()

      if (this.currentPlatform) {
        console.log(`[ResuBoost] Detected platform: ${this.currentPlatform}`)
        this.filler = this.getFiller(this.currentPlatform)

        // Detect if this is a multi-step form
        this.isMultiStep = this.detectMultiStepForm()
      } else {
        console.log('[ResuBoost] No supported platform detected, using generic filler')
        this.filler = typeof GenericFiller !== 'undefined' ? new GenericFiller() : null
      }
    }

    /**
     * Get the appropriate filler for the platform
     * @param {string} platform Platform name
     * @returns {Object} Filler instance
     */
    getFiller(platform) {
      const fillers = {
        linkedin: typeof LinkedInFiller !== 'undefined' ? new LinkedInFiller() : null,
        greenhouse: typeof GreenhouseFiller !== 'undefined' ? new GreenhouseFiller() : null,
        lever: typeof LeverFiller !== 'undefined' ? new LeverFiller() : null,
        workday: typeof WorkdayFiller !== 'undefined' ? new WorkdayFiller() : null,
      }

      return fillers[platform] || (typeof GenericFiller !== 'undefined' ? new GenericFiller() : null)
    }

    /**
     * Detect if the form is a multi-step application
     * @returns {boolean} True if multi-step
     */
    detectMultiStepForm() {
      // Check for common multi-step indicators
      const multiStepIndicators = [
        '.step-indicator',
        '.progress-bar',
        '[role="progressbar"]',
        '.pagination',
        '[data-step]',
        '.wizard',
        '.stepper',
        '.jobs-easy-apply-progress', // LinkedIn
        '[data-automation-id="progressBar"]', // Workday
      ]

      return multiStepIndicators.some((selector) => {
        try {
          return document.querySelector(selector) !== null
        } catch (e) {
          return false
        }
      })
    }

    /**
     * Set up message listener for communication with popup/background
     */
    setupMessageListener() {
      chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        this.handleMessage(message)
          .then(sendResponse)
          .catch((error) => {
            console.error('[ResuBoost] Message handler error:', error)
            sendResponse({ error: error.message })
          })
        return true // Keep channel open for async response
      })
    }

    /**
     * Handle incoming messages
     * @param {Object} message Message object
     * @returns {Object} Response
     */
    async handleMessage(message) {
      switch (message.type) {
        case 'DETECT_PAGE':
          return {
            supported: !!this.currentPlatform || !!this.filler,
            platform: this.currentPlatform || 'generic',
            hasForm: this.detector.hasApplicationForm(),
            isMultiStep: this.isMultiStep,
          }

        case 'AUTOFILL':
          return await this.performAutofill(message.data)

        case 'GET_JOB_DETAILS':
          return this.extractJobDetails()

        case 'FILL_NEXT_STEP':
          return await this.fillNextStep(message.data)

        default:
          return { error: 'Unknown message type' }
      }
    }

    /**
     * Perform autofill operation with visual feedback
     * @param {Object} profileData User profile data
     * @returns {Object} Result object
     */
    async performAutofill(profileData) {
      if (!this.filler) {
        throw new Error('No filler available for this page')
      }

      try {
        // Show progress indicator for multi-step forms
        if (this.isMultiStep) {
          this.showProgressIndicator()
        }

        const result = await this.filler.fill(profileData)

        // Highlight filled fields
        this.highlightFilledFields(result.filledFields || [])

        // Update progress
        if (this.isMultiStep && result.currentStep) {
          this.updateProgress(result.currentStep, result.totalSteps)
        }

        // Show success notification
        const fieldCount = result.filledFields?.length || 0
        this.showNotification(
          `Filled ${fieldCount} field${fieldCount !== 1 ? 's' : ''} successfully!`,
          'success'
        )

        // Log any errors that occurred during filling
        if (result.errors && result.errors.length > 0) {
          console.warn('[ResuBoost] Some fields had errors:', result.errors)
          if (result.errors.length > 0) {
            this.showNotification(
              `Filled ${fieldCount} fields, but ${result.errors.length} field(s) could not be filled`,
              'warning',
              5000
            )
          }
        }

        return {
          success: true,
          filledFields: result.filledFields,
          errors: result.errors,
          currentStep: result.currentStep,
          totalSteps: result.totalSteps,
        }
      } catch (error) {
        console.error('[ResuBoost] Autofill error:', error)
        this.showNotification(
          this.getErrorMessage(error),
          'error'
        )
        throw error
      } finally {
        // Hide progress indicator
        if (this.isMultiStep) {
          setTimeout(() => this.hideProgressIndicator(), 2000)
        }
      }
    }

    /**
     * Get user-friendly error message
     * @param {Error} error Error object
     * @returns {string} User-friendly message
     */
    getErrorMessage(error) {
      const errorMessages = {
        'No filler available': 'This page type is not supported for autofill',
        'Failed to load profile': 'Could not load your profile data. Please check your login.',
        'Network error': 'Network error. Please check your connection.',
        'Permission denied': 'Permission denied. Please enable the extension for this site.',
      }

      for (const [key, message] of Object.entries(errorMessages)) {
        if (error.message.includes(key)) {
          return message
        }
      }

      return 'An error occurred while filling the form. Please try again.'
    }

    /**
     * Highlight fields that were filled
     * @param {Array} filledFields Array of filled field info
     */
    highlightFilledFields(filledFields) {
      for (const field of filledFields) {
        try {
          // Find the element by name or id
          let element = null
          if (field.name) {
            element = document.querySelector(`[name="${field.name}"]`) ||
                      document.querySelector(`#${field.name}`)
          }

          if (element) {
            element.classList.add('resuboost-filled-field')

            // Remove highlight after animation
            setTimeout(() => {
              element.classList.remove('resuboost-filled-field')
            }, 1500)
          }
        } catch (e) {
          // Ignore highlighting errors
        }
      }
    }

    /**
     * Fill next step in multi-step form
     * @param {Object} profileData User profile data
     * @returns {Object} Result
     */
    async fillNextStep(profileData) {
      // Re-detect to get fresh state
      this.detectPlatform()

      if (this.filler && typeof this.filler.clickNextButton === 'function') {
        const clicked = await this.filler.clickNextButton()
        if (clicked) {
          // Wait for page to load, then fill
          await new Promise((resolve) => setTimeout(resolve, 1000))
          return await this.performAutofill(profileData)
        }
      }

      return { success: false, error: 'No next step available' }
    }

    /**
     * Extract job details from the page
     * @returns {Object} Job details
     */
    extractJobDetails() {
      if (this.filler && typeof this.filler.extractJobDetails === 'function') {
        return this.filler.extractJobDetails()
      }

      // Fallback generic extraction
      return {
        title: document.querySelector('h1')?.textContent?.trim() || '',
        company: this.extractCompanyName(),
        location: this.extractLocation(),
        description: this.extractDescription(),
      }
    }

    /**
     * Extract company name from page
     * @returns {string} Company name
     */
    extractCompanyName() {
      const selectors = [
        '[data-company-name]',
        '.company-name',
        '.employer-name',
        '[itemprop="hiringOrganization"]',
        '[class*="company"]',
        '[class*="employer"]',
      ]

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

    /**
     * Extract job location from page
     * @returns {string} Location
     */
    extractLocation() {
      const selectors = [
        '[data-job-location]',
        '.job-location',
        '.location',
        '[itemprop="jobLocation"]',
        '[class*="location"]',
      ]

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

    /**
     * Extract job description from page
     * @returns {string} Description (truncated)
     */
    extractDescription() {
      const selectors = [
        '[data-job-description]',
        '.job-description',
        '.description',
        '[itemprop="description"]',
        '[class*="description"]',
      ]

      for (const selector of selectors) {
        try {
          const element = document.querySelector(selector)
          if (element) {
            return element.textContent?.trim().slice(0, 1000) || ''
          }
        } catch (e) {
          continue
        }
      }

      return ''
    }

    /**
     * Inject the autofill button into the page
     */
    injectAutofillButton() {
      // Only inject if we have a filler and on a supported page
      if (!this.filler || document.getElementById(AUTOFILL_BUTTON_ID)) {
        return
      }

      // Check if there's a form on the page
      if (!this.detector.hasApplicationForm()) {
        return
      }

      const button = this.createAutofillButton()
      document.body.appendChild(button)

      console.log('[ResuBoost] Autofill button injected')
    }

    /**
     * Create the autofill button element
     * @returns {HTMLElement} Button element
     */
    createAutofillButton() {
      const button = document.createElement('button')
      button.id = AUTOFILL_BUTTON_ID
      button.setAttribute('aria-label', 'ResuBoost Autofill')
      button.innerHTML = this.getButtonContent('default')

      // Apply styles
      Object.assign(button.style, {
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        zIndex: '2147483647', // Maximum z-index
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '12px 20px',
        backgroundColor: '#2563eb',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        fontSize: '14px',
        fontWeight: '500',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        cursor: 'pointer',
        boxShadow: '0 4px 12px rgba(37, 99, 235, 0.4)',
        outline: 'none',
      })

      // Add hover/focus handlers
      button.addEventListener('mouseenter', () => {
        if (!button.disabled) {
          button.style.backgroundColor = '#1d4ed8'
        }
      })

      button.addEventListener('mouseleave', () => {
        if (!button.disabled) {
          button.style.backgroundColor = '#2563eb'
        }
      })

      button.addEventListener('focus', () => {
        button.style.boxShadow = '0 4px 12px rgba(37, 99, 235, 0.4), 0 0 0 3px rgba(37, 99, 235, 0.3)'
      })

      button.addEventListener('blur', () => {
        button.style.boxShadow = '0 4px 12px rgba(37, 99, 235, 0.4)'
      })

      button.addEventListener('click', () => this.handleAutofillButtonClick())

      return button
    }

    /**
     * Get button content for different states
     * @param {string} state Button state
     * @returns {string} HTML content
     */
    getButtonContent(state) {
      const icons = {
        default: `
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
          </svg>
          <span>Autofill</span>
        `,
        loading: `
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation: resuboost-spin 1s linear infinite;">
            <circle cx="12" cy="12" r="10" stroke-dasharray="31.4 31.4" stroke-dashoffset="0"></circle>
          </svg>
          <span>Filling...</span>
        `,
        success: `
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 6L9 17l-5-5"></path>
          </svg>
          <span>Done!</span>
        `,
        error: `
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
          <span>Error</span>
        `,
      }

      return icons[state] || icons.default
    }

    /**
     * Handle autofill button click
     */
    async handleAutofillButtonClick() {
      const button = document.getElementById(AUTOFILL_BUTTON_ID)
      if (!button || button.disabled) return

      // Set loading state
      button.disabled = true
      button.innerHTML = this.getButtonContent('loading')
      button.style.backgroundColor = '#2563eb'

      try {
        // Request profile data from background script
        const profileData = await chrome.runtime.sendMessage({ type: 'GET_PROFILE_DATA' })

        if (!profileData || profileData.error) {
          throw new Error(profileData?.error || 'Failed to load profile data')
        }

        const result = await this.performAutofill(profileData)

        // Set success state
        button.innerHTML = this.getButtonContent('success')
        button.style.backgroundColor = '#22c55e'

        // Log the application if successful
        try {
          const jobDetails = this.extractJobDetails()
          await chrome.runtime.sendMessage({
            type: 'LOG_APPLICATION',
            data: {
              ...jobDetails,
              platform: this.currentPlatform || 'generic',
              filledFields: result.filledFields?.length || 0,
              timestamp: new Date().toISOString(),
              url: window.location.href,
            },
          })
        } catch (logError) {
          console.warn('[ResuBoost] Could not log application:', logError)
        }

        // Reset button after delay
        setTimeout(() => {
          button.innerHTML = this.getButtonContent('default')
          button.style.backgroundColor = '#2563eb'
          button.disabled = false
        }, 2000)
      } catch (error) {
        console.error('[ResuBoost] Autofill button error:', error)

        // Set error state
        button.innerHTML = this.getButtonContent('error')
        button.style.backgroundColor = '#ef4444'

        // Reset button after delay
        setTimeout(() => {
          button.innerHTML = this.getButtonContent('default')
          button.style.backgroundColor = '#2563eb'
          button.disabled = false
        }, 2000)
      }
    }

    /**
     * Show progress indicator for multi-step forms
     */
    showProgressIndicator() {
      if (document.getElementById(PROGRESS_CONTAINER_ID)) return

      const container = document.createElement('div')
      container.id = PROGRESS_CONTAINER_ID

      Object.assign(container.style, {
        position: 'fixed',
        bottom: '80px',
        right: '20px',
        zIndex: '2147483646',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        padding: '12px 16px',
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        fontSize: '12px',
        color: '#374151',
        minWidth: '180px',
      })

      container.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2" style="animation: resuboost-spin 1s linear infinite;">
            <circle cx="12" cy="12" r="10" stroke-dasharray="31.4 31.4"></circle>
          </svg>
          <span>Filling form...</span>
        </div>
        <div style="width: 100%; height: 4px; background: #e5e7eb; border-radius: 2px; overflow: hidden;">
          <div id="resuboost-progress-bar" style="height: 100%; background: #3b82f6; width: 0%; transition: width 0.3s ease;"></div>
        </div>
        <div id="resuboost-progress-text" style="font-size: 11px; color: #6b7280;">Step 1</div>
      `

      document.body.appendChild(container)
    }

    /**
     * Update progress indicator
     * @param {number} current Current step
     * @param {number} total Total steps
     */
    updateProgress(current, total) {
      const bar = document.getElementById('resuboost-progress-bar')
      const text = document.getElementById('resuboost-progress-text')

      if (bar && total > 0) {
        const percentage = (current / total) * 100
        bar.style.width = `${percentage}%`
      }

      if (text) {
        text.textContent = total > 0 ? `Step ${current} of ${total}` : `Step ${current}`
      }
    }

    /**
     * Hide progress indicator
     */
    hideProgressIndicator() {
      const container = document.getElementById(PROGRESS_CONTAINER_ID)
      if (container) {
        container.remove()
      }
    }

    /**
     * Show notification toast
     * @param {string} message Message to display
     * @param {string} type Notification type (success, error, info, warning)
     * @param {number} duration Duration in ms
     */
    showNotification(message, type = 'info', duration = 3000) {
      // Remove existing notification
      const existing = document.getElementById(NOTIFICATION_ID)
      if (existing) {
        existing.remove()
      }

      const config = NOTIFICATION_TYPES[type] || NOTIFICATION_TYPES.info

      const notification = document.createElement('div')
      notification.id = NOTIFICATION_ID

      Object.assign(notification.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        zIndex: '2147483647',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '12px 16px',
        backgroundColor: config.bgColor,
        color: 'white',
        borderRadius: '8px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        fontSize: '14px',
        fontWeight: '500',
        maxWidth: '350px',
      })

      // Create SVG icon (safe - config.icon is from trusted source)
      const svgNS = 'http://www.w3.org/2000/svg'
      const svg = document.createElementNS(svgNS, 'svg')
      svg.setAttribute('width', '20')
      svg.setAttribute('height', '20')
      svg.setAttribute('viewBox', '0 0 24 24')
      svg.setAttribute('fill', 'none')
      svg.setAttribute('stroke', 'currentColor')
      svg.setAttribute('stroke-width', '2')
      svg.innerHTML = config.icon // Safe - config.icon is hardcoded in NOTIFICATION_TYPES

      // Create message span (use textContent to prevent XSS)
      const messageSpan = document.createElement('span')
      messageSpan.textContent = message // Safe - textContent does not interpret HTML

      notification.appendChild(svg)
      notification.appendChild(messageSpan)
      document.body.appendChild(notification)

      // Auto-remove after duration
      setTimeout(() => {
        notification.classList.add('hiding')
        setTimeout(() => notification.remove(), 300)
      }, duration)
    }

    /**
     * Observe page changes for SPA navigation
     */
    observePageChanges() {
      // Debounce function to avoid excessive re-detection
      let debounceTimer = null
      const debounce = (fn, delay) => {
        clearTimeout(debounceTimer)
        debounceTimer = setTimeout(fn, delay)
      }

      // Re-detect platform on significant DOM changes
      const observer = new MutationObserver((mutations) => {
        // Check if autofill button was removed
        if (!document.getElementById(AUTOFILL_BUTTON_ID)) {
          debounce(() => {
            this.detectPlatform()
            this.injectAutofillButton()
          }, 500)
        }
      })

      observer.observe(document.body, {
        childList: true,
        subtree: true,
      })

      // Also listen for URL changes (for SPAs)
      let lastUrl = window.location.href
      const urlObserver = new MutationObserver(() => {
        if (window.location.href !== lastUrl) {
          lastUrl = window.location.href
          debounce(() => {
            this.detectPlatform()
            this.injectAutofillButton()
          }, 1000)
        }
      })

      urlObserver.observe(document, { subtree: true, childList: true })
    }
  }

  // Initialize content script when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      const controller = new ContentController()
      controller.init()
    })
  } else {
    const controller = new ContentController()
    controller.init()
  }
})()
