/**
 * ResuBoost AI Extension Popup
 * Handles popup UI interactions and communication with background service worker
 */

import { StorageHelper } from '../lib/storage.js'
import { ApiClient } from '../lib/api.js'

const APP_URL = 'http://localhost:3000'

class PopupController {
  constructor() {
    this.storage = new StorageHelper()
    this.api = new ApiClient()
    this.elements = {}
  }

  async init() {
    this.cacheElements()
    this.attachEventListeners()
    await this.checkAuthStatus()
    await this.detectCurrentPage()
  }

  cacheElements() {
    this.elements = {
      authSection: document.getElementById('auth-section'),
      loggedOut: document.getElementById('logged-out'),
      loggedIn: document.getElementById('logged-in'),
      mainSection: document.getElementById('main-section'),
      userName: document.getElementById('user-name'),
      profileName: document.getElementById('profile-name'),
      loginBtn: document.getElementById('login-btn'),
      logoutBtn: document.getElementById('logout-btn'),
      autofillBtn: document.getElementById('autofill-btn'),
      trackBtn: document.getElementById('track-btn'),
      openAppLink: document.getElementById('open-app-link'),
      settingsLink: document.getElementById('settings-link'),
      pageStatus: document.getElementById('page-status'),
    }
  }

  attachEventListeners() {
    this.elements.loginBtn.addEventListener('click', () => this.handleLogin())
    this.elements.logoutBtn.addEventListener('click', () => this.handleLogout())
    this.elements.autofillBtn.addEventListener('click', () => this.handleAutofill())
    this.elements.trackBtn.addEventListener('click', () => this.handleTrackJob())
    this.elements.openAppLink.addEventListener('click', (e) => this.handleOpenApp(e))
    this.elements.settingsLink.addEventListener('click', (e) => this.handleOpenSettings(e))
  }

  async checkAuthStatus() {
    try {
      const authData = await this.storage.get(['accessToken', 'user'])

      if (authData.accessToken && authData.user) {
        this.showLoggedInState(authData.user)
        await this.loadProfile()
      } else {
        this.showLoggedOutState()
      }
    } catch (error) {
      console.error('Error checking auth status:', error)
      this.showLoggedOutState()
    }
  }

  showLoggedInState(user) {
    this.elements.loggedOut.classList.add('hidden')
    this.elements.loggedIn.classList.remove('hidden')
    this.elements.mainSection.classList.remove('hidden')
    this.elements.userName.textContent = user.name || user.email || 'Connected'
  }

  showLoggedOutState() {
    this.elements.loggedOut.classList.remove('hidden')
    this.elements.loggedIn.classList.add('hidden')
    this.elements.mainSection.classList.add('hidden')
  }

  async loadProfile() {
    try {
      const profile = await this.storage.get('activeProfile')
      if (profile && profile.activeProfile) {
        this.elements.profileName.textContent = profile.activeProfile.name || 'Default Profile'
      } else {
        this.elements.profileName.textContent = 'No profile selected'
      }
    } catch (error) {
      console.error('Error loading profile:', error)
      this.elements.profileName.textContent = 'Error loading profile'
    }
  }

  async detectCurrentPage() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })

      if (!tab || !tab.url) {
        this.updatePageStatus('unsupported', 'No active tab')
        return
      }

      // Send message to content script to detect page type
      const response = await chrome.tabs.sendMessage(tab.id, { type: 'DETECT_PAGE' })

      if (response && response.supported) {
        this.updatePageStatus('supported', `${response.platform} detected`)
        this.elements.autofillBtn.disabled = false
      } else {
        this.updatePageStatus('unsupported', 'Not a job application page')
        this.elements.autofillBtn.disabled = true
      }
    } catch (error) {
      // Content script might not be loaded on this page
      this.updatePageStatus('unsupported', 'Page not supported')
      this.elements.autofillBtn.disabled = true
    }
  }

  updatePageStatus(status, message) {
    const badge = this.elements.pageStatus.querySelector('.status-badge')
    badge.className = `status-badge ${status}`
    badge.textContent = message
  }

  async handleLogin() {
    // Open the main app login page in a new tab
    // TODO: Implement OAuth flow or token-based login
    chrome.tabs.create({ url: `${APP_URL}/login?extension=true` })
  }

  async handleLogout() {
    try {
      await this.storage.clear()
      this.showLoggedOutState()

      // Notify background script
      chrome.runtime.sendMessage({ type: 'LOGOUT' })
    } catch (error) {
      console.error('Error logging out:', error)
    }
  }

  async handleAutofill() {
    const btn = this.elements.autofillBtn
    btn.disabled = true
    btn.classList.add('loading')

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })

      // Request profile data from background script
      const profileData = await chrome.runtime.sendMessage({ type: 'GET_PROFILE_DATA' })

      if (!profileData || profileData.error) {
        throw new Error(profileData?.error || 'Failed to load profile data')
      }

      // Send autofill command to content script
      const response = await chrome.tabs.sendMessage(tab.id, {
        type: 'AUTOFILL',
        data: profileData,
      })

      if (response && response.success) {
        this.showNotification('Form filled successfully!', 'success')
      } else {
        throw new Error(response?.error || 'Autofill failed')
      }
    } catch (error) {
      console.error('Autofill error:', error)
      this.showNotification(error.message, 'error')
    } finally {
      btn.disabled = false
      btn.classList.remove('loading')
    }
  }

  async handleTrackJob() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })

      // Get job details from content script
      const jobDetails = await chrome.tabs.sendMessage(tab.id, { type: 'GET_JOB_DETAILS' })

      if (!jobDetails) {
        throw new Error('Could not extract job details')
      }

      // Send to background script to save
      const response = await chrome.runtime.sendMessage({
        type: 'TRACK_JOB',
        data: {
          ...jobDetails,
          url: tab.url,
        },
      })

      if (response && response.success) {
        this.showNotification('Job added to tracker!', 'success')
      } else {
        throw new Error(response?.error || 'Failed to track job')
      }
    } catch (error) {
      console.error('Track job error:', error)
      this.showNotification(error.message, 'error')
    }
  }

  handleOpenApp(e) {
    e.preventDefault()
    chrome.tabs.create({ url: APP_URL })
  }

  handleOpenSettings(e) {
    e.preventDefault()
    chrome.tabs.create({ url: `${APP_URL}/settings` })
  }

  showNotification(message, type = 'info') {
    // TODO: Implement toast notification
    console.log(`[${type}] ${message}`)
    alert(message) // Temporary - replace with proper notification
  }
}

// Initialize popup when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  const popup = new PopupController()
  popup.init()
})
