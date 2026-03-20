# Label Accessibility Fix Guide

## Problem
The `jsx-a11y/label-has-associated-control` ESLint rule requires all `<label>` elements to be properly associated with form controls for accessibility.

## Solution Pattern

### Pattern 1: Simple Label + Input/Select/Textarea
```tsx
// BEFORE ❌
<label className="...">Field Name</label>
<input type="text" value={value} onChange={handler} />

// AFTER ✅
<label htmlFor="field-id" className="...">Field Name</label>
<input id="field-id" type="text" value={value} onChange={handler} />
```

### Pattern 2: Labels in Array/Loop
```tsx
// BEFORE ❌
{items.map((item, index) => (
  <div key={index}>
    <label>Item {index}</label>
    <input value={item} />
  </div>
))}

// AFTER ✅
{items.map((item, index) => (
  <div key={index}>
    <label htmlFor={`item-${index}`}>Item {index}</label>
    <input id={`item-${index}`} value={item} />
  </div>
))}
```

### Pattern 3: Radio Button Groups
```tsx
// BEFORE ❌
<label>Group Label</label>
<div>
  {options.map(option => (
    <label key={option}>
      <input type="radio" name="group" value={option} />
      {option}
    </label>
  ))}
</div>

// AFTER ✅
<div role="group" aria-label="Group Label">
  <div className="...">Group Label</div>
  <div>
    {options.map(option => (
      <label key={option}>
        <input type="radio" name="group" value={option} />
        {option}
      </label>
    ))}
  </div>
</div>
```

Note: For radio buttons where the label wraps the input, no htmlFor/id is needed.
But the parent group label should use role="group" and aria-label instead of <label>.

### Pattern 4: Nested Inputs (Label wraps input)
```tsx
// Already correct ✅ - No changes needed
<label>
  <input type="checkbox" />
  <span>Label text</span>
</label>
```

## Files to Fix (55 total errors remaining)

### Status by File:
- ✅ src/app/documents/page.tsx - Partially fixed (7 labels fixed, more remaining)
- ⏳ src/app/career/page.tsx - Partially fixed (need to check remaining)
- ⏳ src/app/cover-letters/page.tsx - Not started
- ⏳ src/app/interview/page.tsx - Not started
- ⏳ src/app/jobs/filters/page.tsx - Not started
- ⏳ src/app/profile/page.tsx - Not started
- ⏳ src/app/settings/page.tsx - Not started

## Systematic Fix Process

For each file:

1. **Find all label errors:**
   ```bash
   npm run lint -- src/app/FILENAME 2>&1 | grep "label-has-associated"
   ```

2. **List all labels in file:**
   ```bash
   grep -n "<label" src/app/FILENAME
   ```

3. **For each label:**
   - Identify the associated input/select/textarea
   - Add unique `id` to the input (use descriptive name like `field-name`)
   - Add matching `htmlFor="field-id"` to the label
   - For radio button groups, convert parent label to div with role="group"

4. **Verify fixes:**
   ```bash
   npm run lint -- src/app/FILENAME 2>&1 | grep "label-has-associated"
   ```

## ID Naming Convention

Use descriptive, kebab-case IDs that indicate the field's purpose:

- `achievement-title` for achievement title input
- `base-salary` for salary input
- `job-description-cover` for job description in cover letter (add context if multiple)
- `select-resume-qa` for resume selector in Q&A section

## Special Cases

### Multiple Similar Fields
When the same field name appears in different sections, add context:
```tsx
// Cover letter section
<label htmlFor="job-description-cover">Job Description</label>
<textarea id="job-description-cover" />

// Interview section
<label htmlFor="job-description-interview">Job Description</label>
<textarea id="job-description-interview" />
```

### Dynamic Lists
Use template literals for dynamic IDs:
```tsx
{items.map((item, idx) => (
  <>
    <label htmlFor={`item-${idx}`}>{item.name}</label>
    <input id={`item-${idx}`} />
  </>
))}
```

## Current Progress

### Completed Fixes:
1. src/app/career/page.tsx:
   - ✅ achievement-title
   - ✅ achievement-date
   - ✅ achievement-description
   - ✅ achievement-tags
   - ✅ base-salary
   - ✅ bonus-percentage
   - ✅ stock-value
   - ✅ benefits-value
   - ✅ other-compensation
   - ✅ negotiation-scenario
   - ✅ current-offer
   - ✅ target-salary
   - ✅ company-name
   - ✅ role-level
   - ✅ leverage-points

2. src/app/documents/page.tsx:
   - ✅ job-application-link
   - ✅ select-resume-cover
   - ✅ company-name-cover
   - ✅ position-cover
   - ✅ job-description-cover
   - ✅ Tone radio group (converted to role="group")
   - ✅ generated-cover-letter

### Remaining Files:
Need to systematically process remaining labels in all 7 files.

## Automation Note

This cannot be auto-fixed by ESLint. Each label-input pair must be manually reviewed to ensure:
1. Correct semantic association
2. Unique IDs (no duplicates)
3. Meaningful ID names
4. Proper handling of special cases (radio groups, dynamic lists)

## Next Steps

1. Continue with remaining labels in documents/page.tsx
2. Move to cover-letters/page.tsx
3. Process interview/page.tsx
4. Handle jobs/filters/page.tsx
5. Fix profile/page.tsx
6. Complete settings/page.tsx
7. Return to career/page.tsx for any remaining issues
8. Final verification run

## Verification Command

After all fixes:
```bash
npm run lint 2>&1 | grep "label-has-associated-control" | wc -l
```

Target: 0 errors
