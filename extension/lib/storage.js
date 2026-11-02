/**
 * ResuBoost AI Extension Storage Helper
 * Promise wrapper around chrome.storage.local, shared by the popup and the
 * background service worker.
 *
 * Every read resolves to an object keyed by the requested key(s), matching
 * chrome.storage semantics: `await storage.get('settings')` gives
 * `{ settings: ... }`, not the bare value.
 */

export class StorageHelper {
  /**
   * @param {chrome.storage.StorageArea} [area] Storage area (defaults to chrome.storage.local)
   */
  constructor(area) {
    this.area = area || globalThis.chrome?.storage?.local
    if (!this.area) {
      throw new Error('chrome.storage is not available in this context')
    }
  }

  /**
   * Read one or more keys.
   * @param {string|string[]|null} keys Key, list of keys, or null for everything
   * @returns {Promise<Object>} Object keyed by the requested keys
   */
  async get(keys = null) {
    const result = await this.area.get(keys)
    return result || {}
  }

  /**
   * Write key/value pairs.
   * @param {Object} items Values to store
   * @returns {Promise<void>}
   */
  async set(items) {
    await this.area.set(items)
  }

  /**
   * Remove one or more keys.
   * @param {string|string[]} keys Key or list of keys
   * @returns {Promise<void>}
   */
  async remove(keys) {
    await this.area.remove(keys)
  }

  /**
   * Remove everything this extension has stored.
   * @returns {Promise<void>}
   */
  async clear() {
    await this.area.clear()
  }
}
