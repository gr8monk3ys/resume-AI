/**
 * Reusable localStorage → backend API migration utility.
 *
 * Checks if localStorage has data for a given key, and if the backend
 * API returns empty results, batch-creates items via the API, then
 * clears localStorage.
 */

const MIGRATION_PREFIX = 'resuboost_migrated_'

export async function migrateLocalStorage<TRaw, TCreate>(
  key: string,
  listFn: () => Promise<unknown[]>,
  createFn: (item: TCreate) => Promise<unknown>,
  mapFn: (raw: TRaw) => TCreate
): Promise<{ migrated: number; failed: number }> {
  // Check if already migrated
  if (typeof window === 'undefined') {
    return { migrated: 0, failed: 0 }
  }

  const migratedKey = `${MIGRATION_PREFIX}${key}`
  if (localStorage.getItem(migratedKey)) {
    return { migrated: 0, failed: 0 }
  }

  // Check if localStorage has data
  const raw = localStorage.getItem(key)
  if (!raw) {
    return { migrated: 0, failed: 0 }
  }

  let items: TRaw[]
  try {
    items = JSON.parse(raw) as TRaw[]
    if (!Array.isArray(items) || items.length === 0) {
      return { migrated: 0, failed: 0 }
    }
  } catch {
    return { migrated: 0, failed: 0 }
  }

  // Check if backend already has data (don't migrate if so)
  try {
    const existing = await listFn()
    if (existing.length > 0) {
      // Backend already has data — mark as migrated, clear localStorage
      localStorage.setItem(migratedKey, 'true')
      localStorage.removeItem(key)
      return { migrated: 0, failed: 0 }
    }
  } catch {
    // If we can't check the backend, skip migration this time
    return { migrated: 0, failed: 0 }
  }

  // Batch create via API
  let migrated = 0
  let failed = 0

  for (const item of items) {
    try {
      const mapped = mapFn(item)
      await createFn(mapped)
      migrated++
    } catch {
      failed++
    }
  }

  // Only clear localStorage if all items migrated successfully
  if (failed === 0) {
    localStorage.setItem(migratedKey, 'true')
    localStorage.removeItem(key)
  }

  return { migrated, failed }
}
