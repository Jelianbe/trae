# Interaction Patterns and Flows Reference

Common interaction design patterns with state specifications, flow structures, and
design guidance. Use this as a reference when designing or reviewing specific interaction types.

---

## Forms

Forms are the most common interaction pattern and the one most frequently done poorly.
Good form design minimizes cognitive load, prevents errors, and recovers gracefully from them.

### Form Anatomy

```
Form title (optional)
│
├── Field group (related fields)
│   ├── Label (always visible, above the field)
│   ├── Input (text, select, date, etc.)
│   ├── Helper text (optional: format guidance, constraints)
│   └── Error message (inline, below field)
│
├── Field group ...
│
├── Actions
│   ├── Primary: Submit / Save / Continue
│   └── Secondary: Cancel / Back (optional)
│
└── Form-level error (when submit fails and no inline error applies)
```

### Field States

| State | Visual | Copy |
|---|---|---|
| Default | Border, label, placeholder | Placeholder: example or format hint |
| Focus | Highlighted border, no placeholder | — |
| Filled | Border, label, value | — |
| Valid | Border (or green checkmark for critical fields) | — |
| Error | Red border + red error icon + error message | Specific: what is wrong + how to fix |
| Disabled | Reduced opacity, cursor: not-allowed | Optional: why disabled |
| Read-only | No border, no cursor change | — |
| Loading (async validation) | Spinner in field, disabled | "Checking availability..." |

### Validation Timing

**On blur (recommended for most fields)**

Validate when the user leaves a field. This gives them time to complete their input
before seeing errors, reducing the perception of being judged as they type.

**On change (for specific cases)**

Validate in real time for:

- Password strength meters (user expects live feedback)
- Character count limits (user needs to know remaining characters)
- Async availability checks (username, email) — add 300ms debounce

**On submit (required, plus inline)**

Always re-validate on submit. Never rely on only on-blur validation — users
may have skipped fields. Show all errors inline at their fields on submit failure.

**Anti-pattern: submit-only validation**

Validate only on submit and clear the form on failure. This forces users to
re-enter all their data. Never do this.

### Error Message Formula

```
[What happened] + [Why (if not obvious)] + [How to fix]
```

Examples:

- "Email address is not valid — check for typos like missing @ or .com"
- "Password must be at least 8 characters — currently 5"
- "This username is already taken — try adding numbers or using a different name"
- "Card number must be 16 digits"

Anti-patterns:

- "Invalid input" — says nothing
- "Error" — says nothing
- "This field is required" — acceptable but minimal; add format guidance when possible

### Multi-Step Forms

**When to use multi-step:**

- More than 8 fields total
- Fields can be logically grouped into distinct categories
- Users may not have all information at once and need to return

**Multi-step flow structure:**

```
Step 1: [Category]
Step 2: [Category]
Step 3: Review
Step 4: Submit → Success
```

**Requirements:**

- Step indicator showing current step and total steps
- Forward navigation only available when current step is valid
- Back navigation preserves all entered data
- Review step before final submission for high-stakes forms
- Auto-save progress so users can return
- Clear confirmation of successful submission

### Form Success States

**Inline success (minor form, e.g., newsletter signup)**

```
Fields replaced with: ✓ "You're subscribed! Check your inbox for a confirmation."
```

**Page success (major form, e.g., order placed)**

```
Navigate to dedicated confirmation page
Confirmation number, summary of what was submitted
Clear next actions ("Track your order", "Return to home")
Email confirmation sent (mention it on the page)
```

**Toast success (settings change)**

```
Settings saved automatically → "Saved" indicator in save button
Or: toast at bottom of screen: "Settings saved"
```

---

## Navigation

Navigation design is IxD, not just IA. The interaction qualities of navigation —
how quickly it responds, how it communicates current location, how it handles depth —
determine whether users feel oriented or lost.

### Navigation Patterns

**Top navigation bar (horizontal)**

Best for: web apps with 3–7 primary sections, shallow hierarchy.

States per item:

- Default: text or icon + text
- Hover: background highlight, cursor: pointer
- Active/current: underline, bold, or background — always distinct from hover
- Focus: visible focus ring (not just the active state)

**Side navigation (vertical)**

Best for: apps with 5+ sections, deep hierarchy, frequent switching between sections.

States per item:

- Same as top navigation
- Expandable sections: chevron rotates on expand, child items indent
- Active section: parent item highlighted even when child is active

**Bottom tab bar (mobile)**

Best for: native mobile apps, 3–5 primary sections.

States per item:

- Default: icon + label
- Active: filled icon, colored, label bolded
- Badge: notification count overlaid on icon
- Tap: immediate visual response (scale or color transition)

**Breadcrumbs**

Best for: hierarchies deeper than 2 levels, product catalogues, file systems.

Interaction:

- Each ancestor is a link
- Current page is text only (not a link)
- On mobile: collapse to "... > Current Page" to save space

### Back Navigation

Back navigation is one of the most violated IxD conventions.

**Expected behavior:**

- Hardware/browser back: go to the previous route in the user's navigation history
- Back button in UI: same — go to the previous screen/view, preserving any state from that screen

**Common violations:**

- Back button that resets a form (should preserve it)
- Back button that navigates to the "default" parent screen instead of where the user came from
- Modal close button that navigates back two levels instead of one

**Sheet / drawer back:**

When a bottom sheet or side drawer is open, back (hardware or browser) should close it,
not navigate to the previous route.

### Navigation Feedback

The active navigation item must always be visually distinct.
This is a visibility requirement — users need to know where they are.

Minimum active state requirements:

- Color change (not just a subtle tint — must be clearly different from inactive)
- Optional: weight change (bold), icon change (outlined to filled), underline
- Must have sufficient contrast — active vs inactive must be distinguishable without color

---

## Search

Search has two distinct phases: input and results. Each needs careful interaction design.

### Search Input

**Instant search (search-as-you-type)**

- Trigger: on change, with 200–300ms debounce
- Show: skeleton results or spinner in results area while fetching
- Show results: as soon as they arrive (do not wait for full debounce period to expire if results return faster)
- Empty query: show recent searches or suggested categories

**Submit search (form)**

- Trigger: Enter or search button click
- Loading: progress indicator in the search button or results area
- Navigate to results page

### Search States

| State | What to Show |
|---|---|
| Empty (no query) | Recent searches, trending, suggested categories |
| Typing (query active) | Autocomplete suggestions, recent matches |
| Loading results | Skeleton rows or spinner |
| Results found | Results list, result count, applied filters |
| No results | "No results for [query]" + suggestions (check spelling, broader terms, related) |
| Error | "Search is temporarily unavailable" + retry link |

### Search Results

**Result item states:**

- Default, hover, focus, active (clicked/tapped)
- Visited: text color change (web convention)

**Filtering and sorting:**

- Applied filters: displayed as chips above results with "×" to remove
- Sort: dropdown or button group, immediately re-sort without page reload
- Filter changes: show loading state in results area while fetching, not full-page load

**Pagination vs. infinite scroll:**

| Pattern | Use When |
|---|---|
| Pagination | Users need to navigate to specific pages, share URLs to specific results, or compare items across pages |
| Infinite scroll | Browsing/discovery context, user does not need to return to specific positions, content is homogeneous |
| Load more button | Compromise: user controls loading, maintains scroll position, works with back button |

---

## Onboarding

Onboarding is the interaction that introduces users to a product for the first time (or to
a new major feature). Bad onboarding is one of the primary causes of early user dropout.

### Onboarding Principles

**Show value before asking for effort**

Let users experience the product before requiring account creation, permissions, or setup.

**Progressive onboarding over upfront tutorials**

- Do not force users through a tutorial before they can use the product
- Instead: contextual coach marks that appear at the first encounter with each feature
- Just-in-time guidance: surface the explanation when the user needs it

**Empty states as onboarding**

The first time a user sees an empty section of the product, tell them:

- What this section does
- How to populate it
- Why they would want to

### Onboarding Flow Patterns

**Account setup flow (required before use)**

```
Sign up → Verify email → [Profile setup: name, photo, preferences] → First meaningful action
```

Minimize required steps. Everything that can be deferred should be deferred.

**Feature introduction (coach marks)**

```
User encounters feature for first time
→ Tooltip or spotlight overlay: "This is [feature]. [What it does in one sentence]. [CTA: Got it / Learn more]"
→ Dismissed on: "Got it" click, clicking outside, or after 8 seconds
→ Never shown again after dismissal
```

**Empty state onboarding**

```
Empty list / dashboard section
→ Illustration (optional) + heading: "[Section name]"
→ Description: "When you [action], [results] will appear here."
→ CTA button: "[Primary action to add content]"
```

### What Not to Do

❌ Mandatory video tutorial before first use
❌ Multi-screen wizard for information that could be collected progressively
❌ "Skip" options that leave users in a broken state
❌ Onboarding that assumes the user has completed setup when they haven't
❌ Progress bars for onboarding that are misleading about actual effort required

---

## Error Handling

Error handling is the interaction design work that most directly determines whether
users trust your product. A product that handles errors gracefully is a product that
feels reliable.

### Error Hierarchy

| Error Type | Scope | Display Pattern |
|---|---|---|
| Field validation error | Single field | Inline below the field |
| Form validation error | Multiple fields or form-level | Summary above form + inline at fields |
| Action error (save failed) | Single action | Toast (recoverable) or inline message (blocking) |
| Page-level error | Entire view | Full-page error state with recovery path |
| System error | Product unavailable | Error page with status and estimated resolution |

### Error Message Formula (repeated from Forms, applies everywhere)

```
[What happened] + [Why, if non-obvious] + [What to do next]
```

- "Payment failed — your card was declined. Check your card details or try a different card."
- "File is too large. Maximum size is 10 MB. Try compressing the file before uploading."
- "Connection lost. Your changes have been saved locally and will sync when you're back online."

### Recoverable vs. Non-Recoverable Errors

**Recoverable** — user can take action to resolve:

- Validation failure: fix the input
- Network error: retry
- Permission error: request access or sign in
- Quota exceeded: upgrade or delete items

**Non-recoverable** — user cannot resolve; system must recover:

- Server error (500): show status, estimated resolution time, support contact
- Data loss: never let this happen; auto-save and undo prevent it
- Critical account error: clear path to support

### Error Recovery Patterns

**Toast with retry (transient action failure)**

```
Toast: "Couldn't save changes. [Retry]"
Duration: stays until dismissed or retry succeeds
Position: bottom center (web) or top (mobile)
```

**Inline error with guidance (form failure)**

```
Form-level message at top (if multiple fields fail): "Please fix 3 errors below."
Field-level: red border + error icon + specific message + fix guidance
Submit button: remains disabled until all errors resolved
```

**Full-page error (navigation to broken route)**

```
Heading: "Page not found" or "Something went wrong"
Body: Brief explanation
Actions:
  Primary: Go back / Return to [previous screen]
  Secondary: Go to home
Contact: Link to support for 5xx errors
```

---

## Empty States

An empty state is not the absence of content — it is its own designed state.
Empty states occur when:

- A user is new (no data yet)
- A search or filter returns no results
- A user has cleared all items
- A feature is unavailable

### Empty State Anatomy

```
[Illustration or icon — optional]
[Heading: What this space is for]
[Description: Why it's empty + what the user can do]
[CTA: Primary action to add content or resolve]
```

### Empty State Types

**"First use" empty state**

User has not yet created any content.

```
Illustration representing the content type
Heading: "No [items] yet"
Description: "[Items] you [create/add/save] will appear here."
CTA: "[+ Create your first item]"
```

**"No results" empty state (search/filter)**

A query returned no matches.

```
Icon or illustration
Heading: "No results for '[query]'"
Description options:
  - "Check your spelling or try a different search term."
  - "Try removing some filters."
  - "[Link: Browse all items] instead"
No CTA for creating new content (user was looking, not creating)
```

**"User cleared all items" empty state**

User deliberately removed everything.

```
Minimal — just a brief message, no elaborate illustration
Heading: "[Section] is empty"
Optional CTA if re-adding is the likely next action
Undo option if the clearing was recent
```

**"Feature unavailable" empty state**

A section is locked, requires upgrade, or is temporarily unavailable.

```
Lock icon or relevant illustration
Heading: "Upgrade to access [feature]" or "[Feature] is temporarily unavailable"
Description: What the feature does and what is needed to access it
CTA: "[Upgrade plan]" or "[Learn more]" or "[Check status page]"
```

---

## Modals and Overlays

Modals interrupt the user's flow. Use them only when the interaction:

1. Requires focused attention on a single task
2. Requires a decision before the user can proceed
3. Is too complex for inline or contextual display

### When NOT to use modals

- For displaying information only (use inline or a dedicated page)
- For complex forms with more than 5 fields (use a dedicated page)
- For content that the user will need to reference while working (use a panel or inline)
- As onboarding (use contextual patterns instead)

### Modal States

| State | Requirements |
|---|---|
| Open | Focus moves into modal, background scrolling locked, backdrop dims background |
| Active (with form) | All states for form elements apply |
| Loading | Spinner in modal body or footer, primary action disabled |
| Error | Inline error message in modal, does not close modal |
| Success | Modal closes, toast or inline confirmation appears |
| Close / dismiss | Via close icon, backdrop click, or Escape key (all three must work) |

### Modal Focus Management (Accessibility)

1. When modal opens: focus moves to first interactive element in modal (or modal heading)
2. Tab cycle stays inside the modal (focus trap)
3. When modal closes: focus returns to the element that triggered it
4. Escape key closes the modal

Failing to implement this makes modals inaccessible to keyboard users.

### Modal Confirmation Dialogs

Used for destructive or irreversible actions.

**Anatomy:**

```
Heading: "[Specific action] [Object name]?"
Body: Brief explanation of consequences (for destructive actions)
Actions:
  Primary (destructive): [Red button: "Delete [item]"]
  Secondary: "Cancel"
```

**Examples:**

- Delete confirmation: "Delete this document? This cannot be undone."
- Unsaved changes: "Leave without saving? Your changes will be lost."
- Permission request: "Allow access to your location? This lets us show you nearby items."

### Modal Size Guidelines

| Type | Size | Use When |
|---|---|---|
| Small confirmation | 400px max-width | Destructive action confirmations, simple alerts |
| Medium dialog | 600px max-width | Form with 2–5 fields, simple multi-step confirmations |
| Large dialog | 800px max-width | Complex forms, rich content, image galleries |

Never use a modal for content that exceeds the large dialog size — use a dedicated page instead.

### Sheet / Bottom Drawer

Mobile pattern for contextual actions that does not fully interrupt flow.

**When to use:**

- Quick actions from a list (archive, share, edit)
- Filters and sort options
- Threaded comments or replies
- Map location picker

**Interaction:**

- Swipe down to dismiss
- Drag handle at top for dismissing by dragging
- Back hardware button dismisses
- Does not lock background scrolling as strictly as modals (allows some interaction)

---

## Drag and Drop

Drag and drop is one of the most complex interactions to implement well. It requires
careful attention to affordance, feedback, and accessibility.

### Affordance

Users must know an element is draggable before they try to drag it.

**Visual indicators of draggability:**

- Visible drag handle (grip dots or handle icon)
- Cursor change on hover (grab → grabbing)
- Hover state on the entire row/item
- Lift shadow on drag start

**Accessible drag indicators:**

- "Drag to reorder" visible text or ARIA label
- Keyboard alternative: up/down arrows for reordering
- Screen reader announcement: "Item name, position 3 of 7. Press up or down arrow to move."

### Drag States

| State | Visual | Behavior |
|---|---|---|
| Default | Standard appearance | — |
| Hover | Subtle highlight or cursor change | Hints at draggability |
| Drag start | Element lifts (shadow, scale 1.02), placeholder shows drop position | Element follows cursor/finger |
| Dragging | Elevated shadow, reduced opacity (0.8) | Position updates as user drags |
| Drop target hover | Target area highlights, insertion indicator shows | Drop will occur at indicator |
| Drop | Element animates to new position | Slot closes, other items reflow |
| Cancel (drop outside valid area) | Element animates back to original position | — |

### Feedback During Drag

**Drag start:**

- Haptic feedback (mobile): light tap on drag start
- Sound feedback (if implemented): subtle tap sound

**Over valid drop target:**

- Drop target highlights
- Insertion indicator appears at drop position
- ARIA live region announces: "Over [target]. Drop to move to position [n]."

**Successful drop:**

- Brief success haptic (mobile)
- Element snaps to new position with 200ms ease-out animation
- ARIA: "Moved [item name] to position [n]."

**Cancel:**

- Element animates back to original position
- No haptic/sound on cancel

### Keyboard Support (Accessibility)

| Key | Action |
|---|---|
| Tab | Focus moves to draggable item |
| Space/Enter | Picks up item, announces "Grabbed [item]. Use arrow keys to move." |
| Up/Down arrow | Moves item in list, announces new position |
| Space/Enter | Drops item at new position |
| Escape | Cancels drag, returns to original position |

---

## Gestures

Gestures are native mobile interactions. They require careful consideration of discoverability,
accessibility, and platform conventions.

### Common Gestures

| Gesture | Platform | Use When |
|---|---|---|
| Tap | Mobile, Desktop | Primary selection |
| Long press / Long tap | Mobile | Context menu, preview |
| Swipe horizontal | Mobile | Navigation, reveal actions |
| Swipe vertical | Mobile | Scroll, pull to refresh |
| Pinch | Mobile | Zoom in/out |
| Drag | Mobile, Desktop | Move, drag and drop |
| Two-finger tap | Mobile | Zoom out (maps) |

### Pull to Refresh

**Pattern:**

```
User pulls list down from top
→ Spinner/activity indicator appears below header
→ Release triggers refresh
→ New content loads, indicator animates out
```

**Duration thresholds:**

- <1s refresh: indicator shows briefly, content updates seamlessly
- 1–5s: spinner remains, content updates on load
- >5s: consider background refresh + notification pattern

### Swipe Actions

**List item swipe (iOS style):**

```
Swipe left → Red delete button revealed
Swipe left → Additional actions (archive, edit) revealed
Swipe threshold: ~80px before action commits
```

**Navigation swipe (iOS):**

```
Edge swipe from left → Go back
Edge swipe disabled when no back history
```

### Gesture Accessibility

**Why gestures fail accessibility:**

- Motor impairments make precise gestures difficult
- Touch targets too small for gesture accuracy
- No keyboard alternative provided

**Solutions:**

- Always provide a non-gesture alternative (e.g., long-press OR button for context menu)
- Make gesture targets large enough (minimum 44×44px)
- Allow customization of gesture sensitivity
- Test with assistive touch enabled

---

## Toggle and Switch

Toggle switches are for binary settings that take effect immediately.
They are NOT for actions that require confirmation or have delayed effect.

### Toggle States

| State | Visual | When |
|---|---|---|
| Off | Track: gray, Thumb: left | Default, disabled |
| On | Track: colored (green/blue), Thumb: right | Enabled |
| Hover (off) | Track: slightly lighter gray | Desktop hover |
| Hover (on) | Track: slightly darker | Desktop hover |
| Disabled | Reduced opacity (0.5), cursor: not-allowed | Not interactive |
| Loading | Spinner in thumb | Processing the change |

### Toggle vs. Checkbox vs. Radio

| Pattern | Use When | Immediate Effect? |
|---|---|---|
| Toggle | Binary setting (on/off) | Yes — takes effect immediately |
| Checkbox | Binary selection within a form | No — takes effect on form submit |
| Radio | Single selection from 2+ options | No — takes effect on form submit |

**Anti-pattern:**

Using a toggle for an action that requires confirmation:

```
❌ "Delete all drafts?" toggle → would delete immediately with no confirmation
✅ "Auto-delete after 30 days" toggle → appropriate for immediate setting change
```

### Toggle Copy

- Label describes the state when ON
- Use action-oriented labels: "Enable notifications" not "Notifications enabled"
- For preference toggles: "Dark mode" not "Enable dark mode"

---

## Loading States

Loading states are the primary mechanism for maintaining user confidence during
asynchronous operations. Every async operation needs a loading state.

### Loading State Decision Tree

```
Is the operation visible?
├── Yes: Is it replacing a small UI element?
│   ├── Yes: Inline spinner in element
│   └── No: Is it replacing a full section?
│       ├── Yes: Skeleton screen
│       └── No: Spinner with context label
└── No: Is it a page navigation?
    ├── Yes: Full-page skeleton or progress indicator
    └── No: Background — notify on complete
```

### Skeleton Loading Best Practices

1. **Match the actual layout** — skeleton must match the real content structure exactly
2. **Consistent shimmer** — all skeleton elements should animate in sync
3. **No layout shift** — skeleton and real content must have identical dimensions
4. **Progressive reveal** — content fades in as it loads, skeleton fades out
5. **Error fallback** — if content fails to load, skeleton transitions to error state

### Skeleton Timing

```
0–200ms: Show skeleton immediately
200ms–2s: Keep skeleton, content loads progressively if possible
>2s: Keep skeleton, add estimated time if available
>10s: Consider background loading + notification
```

### When to Use Progress Bars

- File upload/download
- Multi-step operations where user is waiting
- Batch processing
- Any operation where percentage complete is determinable

**Never show a progress bar that does not move** — it destroys user trust.
If you cannot determine progress, use an indeterminate progress indicator (pulsing bar) instead.
