/**
 * ResuBoost AI Extension Content Script
 * Main entry point for content script functionality
 * Handles form detection, autofill button injection, and message handling
 */

;(function () {
  'use strict'

  // Prevent multiple injections
  if (window.__resuboostInjected) {
    return
  }
  window.__resuboostInjected = true

  const AUTOFILL_BUTTON_ID = 'resuboost-autofill-btn'

  /**
   * Content Script Controller
   */
  class ContentController {
    constructor() {
      this.detector = new PlatformDetector()
      this.currentPlatform = null
      this.filler = null
    }

    init() {
      this.detectPlatform()
      this.setupMessageListener()
      this.injectAutofillButton()
      this.observePageChanges()
    }

    detectPlatform() {
      this.currentPlatform = this.detector.detect()

      if (this.currentPlatform) {
        console.log(`[ResuBoost] Detected platform: ${this.currentPlatform}`)
        this.filler = this.getFiller(this.currentPlatform)
      } else {
        console.log('[ResuBoost] No supported platform detected')
      }
    }

    getFiller(platform) {
      const fillers = {
        linkedin: typeof LinkedInFiller !== 'undefined' ? new LinkedInFiller() : null,
        greenhouse: typeof GreenhouseFiller !== 'undefined' ? new GreenhouseFiller() : null,
        lever: typeof LeverFiller !== 'undefined' ? new LeverFiller() : null,
        workday: typeof WorkdayFiller !== 'undefined' ? new WorkdayFiller() : null,
      }

      return fillers[platform] || (typeof GenericFiller !== 'undefined' ? new GenericFiller() : null)
    }

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

    async handleMessage(message) {
      switch (message.type) {
        case 'DETECT_PAGE':
          return {
            supported: !!this.currentPlatform,
            platform: this.currentPlatform,
            hasForm: this.detector.hasApplicationForm(),
          }

        case 'AUTOFILL':
          return await this.performAutofill(message.data)

        case 'GET_JOB_DETAILS':
          return this.extractJobDetails()

        default:
          return { error: 'Unknown message type' }
      }
    }

    async performAutofill(profileData) {
      if (!this.filler) {
        throw new Error('No filler available for this platform')
      }

      try {
        const result = await this.filler.fill(profileData)
        return { success: true, filledFields: result.filledFields }
      } catch (error) {
        console.error('[ResuBoost] Autofill error:', error)
        throw error
      }
    }

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

    extractCompanyName() {
      // Try common selectors for company name
      const selectors = [
        '[data-company-name]',
        '.company-name',
        '.employer-name',
        '[itemprop="hiringOrganization"]',
      ]

      for (const selector of selectors) {
        const element = document.querySelector(selector)
        if (element) {
          return element.textContent?.trim() || ''
        }
      }

      return ''
    }

    extractLocation() {
      const selectors = [
        '[data-job-location]',
        '.job-location',
        '.location',
        '[itemprop="jobLocation"]',
      ]

      for (const selector of selectors) {
        const element = document.querySelector(selector)
        if (element) {
          return element.textContent?.trim() || ''
        }
      }

      return ''
    }

    extractDescription() {
      const selectors = [
        '[data-job-description]',
        '.job-description',
        '.description',
        '[itemprop="description"]',
      ]

      for (const selector of selectors) {
        const element = document.querySelector(selector)
        if (element) {
          return element.textContent?.trim().slice(0, 1000) || ''
        }
      }

      return ''
    }

    injectAutofillButton() {
      if (!this.currentPlatform || document.getElementById(AUTOFILL_BUTTON_ID)) {
        return
      }

      const button = this.createAutofillButton()
      document.body.appendChild(button)
    }

    createAutofillButton() {
      const button = document.createElement('button')
      button.id = AUTOFILL_BUTTON_ID
      button.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
        </svg>
        <span>Autofill</span>
      `

      // Apply styles
      Object.assign(button.style, {
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        zIndex: '999999',
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
        transition: 'all 0.2s ease',
      })

      button.addEventListener('mouseenter', () => {
        button.style.backgroundColor = '#1d4ed8'
        button.style.transform = 'translateY(-2px)'
      })

      button.addEventListener('mouseleave', () => {
        button.style.backgroundColor = '#2563eb'
        button.style.transform = 'translateY(0)'
      })

      button.addEventListener('click', () => this.handleAutofillButtonClick())

      return button
    }

    async handleAutofillButtonClick() {
      const button = document.getElementById(AUTOFILL_BUTTON_ID)
      if (!button) return

      button.disabled = true
      button.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation: spin 1s linear infinite;">
          <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          <path d="M9 12l2 2 4-4"></path>
        </svg>
        <span>Filling...</span>
      `

      try {
        // Request profile data from background script
        const profileData = await chrome.runtime.sendMessage({ type: 'GET_PROFILE_DATA' })

        if (!profileData || profileData.error) {
          throw new Error(profileData?.error || 'Failed to load profile data')
        }

        await this.performAutofill(profileData)

        button.innerHTML = `
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 6L9 17l-5-5"></path>
          </svg>
          <span>Done!</span>
        `
        button.style.backgroundColor = '#22c55e'

        setTimeout(() => {
          button.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
            <span>Autofill</span>
          `
          button.style.backgroundColor = '#2563eb'
          button.disabled = false
        }, 2000)
      } catch (error) {
        console.error('[ResuBoost] Autofill error:', error)
        button.innerHTML = `
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
          <span>Error</span>
        `
        button.style.backgroundColor = '#ef4444'

        setTimeout(() => {
          button.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
            <span>Autofill</span>
          `
          button.style.backgroundColor = '#2563eb'
          button.disabled = false
        }, 2000)
      }
    }

    observePageChanges() {
      // Re-detect platform on SPA navigation
      const observer = new MutationObserver(() => {
        if (!document.getElementById(AUTOFILL_BUTTON_ID)) {
          this.detectPlatform()
          this.injectAutofillButton()
        }
      })

      observer.observe(document.body, {
        childList: true,
        subtree: true,
      })
    }
  }

  // Add CSS animation for spinner
  const style = document.createElement('style')
  style.textContent = `
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
  `
  document.head.appendChild(style)

  // Initialize content script
  const controller = new ContentController()
  controller.init()
})()
