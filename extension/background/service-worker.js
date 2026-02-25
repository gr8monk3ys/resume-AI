/**
 * ResuBoost AI Extension Background Service Worker
 * Handles background tasks, API communication, and message routing
 */

import { StorageHelper } from '../lib/storage.js'
import { ApiClient } from '../lib/api.js'

const storage = new StorageHelper()
const api = new ApiClient()

// Configuration
const CONFIG = {
  API_BASE_URL: 'http://localhost:8000/api',
  APP_URL: 'http://localhost:3000',
  TOKEN_REFRESH_INTERVAL: 14 * 60 * 1000, // 14 minutes (tokens expire in 15)
}

/**
 * Initialize extension on install
 */
chrome.runtime.onInstalled.addListener(async (details) => {
  console.log('[ResuBoost] Extension installed:', details.reason)

  if (details.reason === 'install') {
    // Open onboarding page
    chrome.tabs.create({
      url: `${CONFIG.APP_URL}/extension-welcome`,
    })
  }

  // Initialize storage with defaults
  await storage.set({
    settings: {
      autoFillEnabled: true,
      showAutofillButton: true,
      trackApplications: true,
    },
  })
})

/**
 * Handle messages from popup and content scripts
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender)
    .then(sendResponse)
    .catch((error) => {
      console.error('[ResuBoost] Message handler error:', error)
      sendResponse({ error: error.message })
    })
  return true // Keep channel open for async response
})

/**
 * Main message handler
 * @param {Object} message Message object
 * @param {Object} sender Sender information
 * @returns {Promise<Object>} Response
 */
async function handleMessage(message, sender) {
  console.log('[ResuBoost] Received message:', message.type)

  switch (message.type) {
    case 'GET_PROFILE_DATA':
      return await getProfileData()

    case 'TRACK_JOB':
      return await trackJob(message.data)

    case 'LOGIN':
      return await handleLogin(message.data)

    case 'LOGOUT':
      return await handleLogout()

    case 'GET_AUTH_STATUS':
      return await getAuthStatus()

    case 'REFRESH_TOKEN':
      return await refreshToken()

    case 'GET_SETTINGS':
      return await getSettings()

    case 'UPDATE_SETTINGS':
      return await updateSettings(message.data)

    default:
      return { error: 'Unknown message type' }
  }
}

/**
 * Get user profile data for autofill
 * @returns {Promise<Object>} Profile data
 */
async function getProfileData() {
  try {
    // Check if we have cached profile data
    const cached = await storage.get('profileData')
    const cacheAge = await storage.get('profileDataTimestamp')

    // Use cache if less than 5 minutes old
    if (cached.profileData && cacheAge.profileDataTimestamp) {
      const age = Date.now() - cacheAge.profileDataTimestamp
      if (age < 5 * 60 * 1000) {
        return cached.profileData
      }
    }

    // Fetch fresh profile data from API
    const authData = await storage.get(['accessToken'])

    if (!authData.accessToken) {
      throw new Error('Not authenticated. Please log in.')
    }

    const profile = await api.getProfile(authData.accessToken)

    // Cache the profile data
    await storage.set({
      profileData: profile,
      profileDataTimestamp: Date.now(),
    })

    return profile
  } catch (error) {
    console.error('[ResuBoost] Failed to get profile data:', error)
    throw error
  }
}

/**
 * Track a job application
 * @param {Object} jobData Job details
 * @returns {Promise<Object>} Result
 */
async function trackJob(jobData) {
  try {
    const authData = await storage.get(['accessToken'])

    if (!authData.accessToken) {
      throw new Error('Not authenticated. Please log in.')
    }

    const result = await api.createJobApplication(authData.accessToken, {
      title: jobData.title,
      company: jobData.company,
      location: jobData.location,
      url: jobData.url,
      description: jobData.description,
      status: 'Bookmarked',
      source: jobData.platform || 'Extension',
    })

    // Show notification
    chrome.notifications.create({
      type: 'basic',
      iconUrl: '../icons/icon128.png',
      title: 'Job Tracked',
      message: `"${jobData.title}" at ${jobData.company} has been added to your tracker.`,
    })

    return { success: true, job: result }
  } catch (error) {
    console.error('[ResuBoost] Failed to track job:', error)
    throw error
  }
}

/**
 * Handle user login
 * @param {Object} credentials Login credentials
 * @returns {Promise<Object>} Auth result
 */
async function handleLogin(credentials) {
  try {
    const result = await api.login(credentials.username, credentials.password)

    await storage.set({
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
      user: result.user,
    })

    // Start token refresh timer
    startTokenRefreshTimer()

    return { success: true, user: result.user }
  } catch (error) {
    console.error('[ResuBoost] Login failed:', error)
    throw error
  }
}

/**
 * Handle user logout
 * @returns {Promise<Object>} Result
 */
async function handleLogout() {
  try {
    // Clear stored data
    await storage.remove(['accessToken', 'refreshToken', 'user', 'profileData', 'profileDataTimestamp'])

    // Stop token refresh timer
    stopTokenRefreshTimer()

    return { success: true }
  } catch (error) {
    console.error('[ResuBoost] Logout failed:', error)
    throw error
  }
}

/**
 * Get current authentication status
 * @returns {Promise<Object>} Auth status
 */
async function getAuthStatus() {
  const authData = await storage.get(['accessToken', 'user'])

  return {
    isAuthenticated: !!authData.accessToken,
    user: authData.user || null,
  }
}

/**
 * Refresh the access token
 * @returns {Promise<Object>} Result
 */
async function refreshToken() {
  try {
    const authData = await storage.get(['refreshToken'])

    if (!authData.refreshToken) {
      throw new Error('No refresh token available')
    }

    const result = await api.refreshToken(authData.refreshToken)

    await storage.set({
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
    })

    return { success: true }
  } catch (error) {
    console.error('[ResuBoost] Token refresh failed:', error)
    // Clear auth data on refresh failure
    await handleLogout()
    throw error
  }
}

/**
 * Get extension settings
 * @returns {Promise<Object>} Settings
 */
async function getSettings() {
  const data = await storage.get('settings')
  return data.settings || {}
}

/**
 * Update extension settings
 * @param {Object} newSettings Updated settings
 * @returns {Promise<Object>} Result
 */
async function updateSettings(newSettings) {
  const current = await getSettings()
  const updated = { ...current, ...newSettings }

  await storage.set({ settings: updated })

  return { success: true, settings: updated }
}

// Token refresh timer management
let tokenRefreshTimer = null

function startTokenRefreshTimer() {
  stopTokenRefreshTimer()

  tokenRefreshTimer = setInterval(async () => {
    try {
      await refreshToken()
      console.log('[ResuBoost] Token refreshed successfully')
    } catch (error) {
      console.error('[ResuBoost] Token refresh failed:', error)
    }
  }, CONFIG.TOKEN_REFRESH_INTERVAL)
}

function stopTokenRefreshTimer() {
  if (tokenRefreshTimer) {
    clearInterval(tokenRefreshTimer)
    tokenRefreshTimer = null
  }
}

// Check auth status on startup and start refresh timer if needed
chrome.runtime.onStartup.addListener(async () => {
  const status = await getAuthStatus()
  if (status.isAuthenticated) {
    startTokenRefreshTimer()
  }
})

/**
 * Handle external messages (from the web app)
 * Used for OAuth flow completion
 */
chrome.runtime.onMessageExternal.addListener((message, sender, sendResponse) => {
  if (message.type === 'AUTH_CALLBACK') {
    // Handle OAuth callback from web app
    handleLogin(message.data)
      .then((result) => {
        sendResponse(result)
        // Close the login tab if it exists
        if (sender.tab) {
          chrome.tabs.remove(sender.tab.id)
        }
      })
      .catch((error) => {
        sendResponse({ error: error.message })
      })
    return true
  }
})

/**
 * Context menu for quick actions
 */
chrome.runtime.onInstalled.addListener(() => {
  // Create context menu for job links
  chrome.contextMenus.create({
    id: 'trackJob',
    title: 'Track this job with ResuBoost',
    contexts: ['link'],
    documentUrlPatterns: [
      '*://*.linkedin.com/*',
      '*://*.indeed.com/*',
      '*://boards.greenhouse.io/*',
      '*://jobs.lever.co/*',
      '*://*.myworkdayjobs.com/*',
    ],
  })
})

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'trackJob') {
    try {
      // Get job details from the page
      const response = await chrome.tabs.sendMessage(tab.id, { type: 'GET_JOB_DETAILS' })

      if (response) {
        await trackJob({
          ...response,
          url: info.linkUrl || tab.url,
        })
      }
    } catch (error) {
      console.error('[ResuBoost] Context menu action failed:', error)
    }
  }
})

console.log('[ResuBoost] Background service worker initialized')
