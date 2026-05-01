---
name: interaction-design
description: >
  Apply interaction design (IxD) principles and frameworks to product and service design work.
  Use this skill when designing or evaluating interaction flows, micro-interactions, feedback
  mechanisms, affordances, mental models, component states, response time, animation and
  transitions, error recovery, input validation, task flows, or navigation patterns.
  Core audiences: product designers, UX designers, UI designers, service designers, and
  interaction designers working on digital products and services.
  Trigger on: interaction flow, micro-interaction, affordance, feedback design, state design
  (hover/focus/error/loading/empty), response time, transition, animation, mental model,
  task flow, user flow, navigation design, interaction spec, handoff annotation, gesture,
  input validation, error state, loading state, empty state, system feedback, signifier,
  design review, interaction audit, IxD principles.
metadata:
  version: 1.0.0
---
# Interaction Design
A practitioner's guide to interaction design for product designers, UX designers, UI designers,
service designers, and interaction designers. This skill covers the full scope of IxD work —
from foundational principles to practical state design, flow specification, and interaction review.
## What This Skill Covers
- Designing and specifying interactions: flows, states, transitions, affordances
- Evaluating interaction quality against established principles
- Writing interaction specifications and handoff annotations
- Micro-interaction design (trigger, rules, feedback, loops)
- Feedback system design: timing, type, and hierarchy
- Response time standards and perceived performance
- Role-specific IxD responsibilities across design disciplines
- Common interaction anti-patterns and how to fix them
Tell Claude what you need. Examples:
- "Help me design the interaction flow for a multi-step checkout"
- "What states does this button need?"
- "Review this interaction — does the feedback arrive at the right time?"
- "I need to write an interaction spec for this drag-and-drop feature"
- "What's the right animation duration for this modal?"
- "How should I handle empty states in this dashboard?"
---
## The 5 Dimensions of Interaction Design
Interaction design operates across five materials. Every interaction is composed of some combination of these dimensions.
| Dimension | What It Is | Design Questions |
|---|---|---|
| **Words** | Labels, instructions, microcopy, error messages, button text | Is the language clear and action-oriented? Does it set accurate expectations? |
| **Visual representations** | Icons, images, typography, color, data visualizations | Does the visual communicate the interaction affordance clearly? |
| **Physical objects/space** | Device type, screen size, input modality (touch/mouse/voice/keyboard), physical environment | Is the interaction designed for the right input modality and context of use? |
| **Time** | Duration of transitions, animation timing, response latency, sequences | Does timing feel responsive and purposeful? Does it communicate state change? |
| **Behaviour** | System responses to user actions — what the product does, how it reacts | Does the system behaviour match the user's mental model and stated intent? |
When designing an interaction, identify which dimensions are in play. Most interaction failures
are dimension mismatches — a system behaviour that contradicts the visual affordance, or
microcopy that does not match what actually happens.
---
## Core Principles
### Norman's 6 Fundamentals
Norman's 6 fundamentals remain the most widely applicable framework for interaction quality.
**Visibility**
Make the state of the system and available actions visible. Users should not have to guess
what the system is doing or what they can do next.
- Visible current state (selected, loading, active, error)
- Visible affordances (interactive elements look interactive)
- Visible navigation and location within the product
❌ A form that submits silently with no loading state
✅ A submit button that transitions to a spinner immediately on click
**Feedback**
Every action should produce an immediate, perceivable response. The system must communicate
that it received the user's input and what it did with it.
- Immediate acknowledgment (within 100ms — before processing completes)
- Clear outcome communication (success, failure, in-progress)
- Feedback proportional to action significance
❌ A delete action with no confirmation, animation, or acknowledgment
✅ A delete action that shows an undo toast immediately, then fades the item out
**Constraints**
Limit available actions to only those that are valid in context. Prevent errors rather than
recovering from them.
- Disable invalid actions rather than showing errors after attempting them
- Use progressive disclosure to surface only relevant controls
- Form fields that only accept valid input types
❌ Allowing date entry as free text, then showing "invalid date" on submit
✅ Using a date picker that constrains selection to valid dates only
**Mapping**
The relationship between controls and their effects should be intuitive. Controls should
spatially or conceptually relate to what they affect.
- Scroll up → content moves up (natural mapping)
- Volume slider increases left-to-right
- A "Next" button is on the right; "Back" is on the left
❌ A brightness control labeled only with an icon that looks like contrast
✅ A slider labeled "Brightness" that increases in the direction of "more light"
**Consistency**
Similar actions should work similarly throughout the product. Users build mental models
from patterns — breaking them causes errors and confusion.
- Internal consistency: same component behaves the same way everywhere
- External consistency: aligns with platform conventions users already know
- Consistency across breakpoints and platforms
❌ Swipe-to-dismiss works in one list but not another
✅ Every destructive action uses the same confirmation pattern
**Affordance**
UI elements should look like they behave. The appearance of a component should signal
how to interact with it.
- Buttons look pressable
- Draggable elements have visible drag handles or respond to hover with a cursor change
- Tappable items have sufficient size and visual weight
❌ Flat text that is actually a link but looks identical to static body text
✅ Links are underlined or use a distinct color that is never applied to non-interactive text
---
### Tognazzini's 19 Principles
The 19 principles cover the broader system of human-computer interaction.
These are applied principles for practitioners.
**Anticipation**
Bring information and tools to users before they need to search for them. Design ahead
of the user's next step.
- Surface related actions contextually
- Pre-fill known data (shipping address from account)
- Warn before a destructive point in a flow
**Autonomy**
Users need to feel in control. The system should operate within constraints the user
understands and can override.
- Allow customization of defaults
- Never take irreversible action without explicit confirmation
- Show system state transparently so users know what is happening
**Consistency**
Maintain consistency at four levels: within the product, across the platform, across
industry conventions, and with user expectations. When in doubt, consistency with user
expectations matters most.
**Defaults**
Defaults should represent the best choice for most users in most situations. Make them
easy to override, clearly labeled, and meaningful — not just the safest technical choice.
- Smart defaults reduce friction for common cases
- Default selections should be clearly indicated
- Avoid jargon in default labels
**Discoverability**
If users cannot find a feature, it does not exist for them. Controls should be visible
and accessible without requiring prior knowledge.
- Navigation should expose primary paths without instruction
- Features should be discoverable through exploration, not manuals
- Progressive disclosure for advanced features, not hidden features
**Efficiency of the User**
Optimize for the user's time, not the system's. Common tasks should be fast. Expert
users should have shortcuts. The most-used path should be the shortest path.
- Keyboard shortcuts for frequent actions
- Bulk actions for repeat operations
- Single-click for primary actions (not multi-step confirmation for common tasks)
**Explorable Interfaces**
Users should be able to explore without fear. Reversible actions allow experimentation.
- Undo for all destructive actions
- Preview before committing (image crop, document format)
- Breadcrumbs and clear back navigation
**Fitts's Law**
Time to acquire a target = f(distance, size). Larger targets and shorter distances reduce
interaction time and error.
- Touch targets: minimum 44×44px (iOS/Android), 48×48px (Material)
- Mouse targets: minimum 32×32px
- Primary CTAs should be the largest interactive element in the area
- Place related actions close together
- Use screen edges and corners — they are infinite targets in one direction
**Latency Reduction**
Respond to input within 100ms. If processing takes longer, acknowledge the action
immediately and show progress.
- 0–100ms: no feedback needed beyond visual state change
- 100ms–1s: show a loading indicator (spinner or skeleton)
- 1s–10s: show a progress indicator with estimated completion
- 10s+: allow background processing, notify on completion
**Learnability**
Interfaces should be learnable over time, not just usable on first contact. Expert usage
should be faster than novice usage.
- Reveal progressive complexity as users gain experience
- Tooltips and inline guidance for non-obvious features
- Don't optimize only for first-time use
**Metaphors**
Use metaphors that accurately convey what a system does. Abandon them when they constrain
or mislead.
- A "trash" icon affords deletion and recovery
- A "folder" affords organization and nesting
- Avoid metaphors that imply constraints that do not exist
**Protect the User's Work**
Never destroy data due to interface errors or unexpected user behavior. Auto-save
continuously, provide undo, and confirm before overwriting.
- Auto-save drafts
- Warn before navigating away from unsaved state
- Never clear a form on validation failure
**Readability**
Text must be legible for your full user population, not just ideal conditions.
- Minimum 16px body text for web
- 4.5:1 contrast ratio minimum (WCAG AA)
- Line length 50–75 characters for prose
- Test with users over 50 and in bright light conditions
**Simplicity**
Simple is not the same as minimal. Simplicity means reducing unnecessary complexity
while preserving all functionality users need.
- Use progressive disclosure, not feature removal
- Avoid false simplicity that hides necessary controls
- Every element on screen should earn its place
**State**
Track where users are and what they have done. Restore state across sessions.
- Remember scroll position, form progress, open panels
- Clearly indicate current location (breadcrumbs, active nav item)
- Distinguish between new and visited content
**Visible Navigation**
Users should always know where they are, where they can go, and how to get back.
- Highlight active location in navigation
- Breadcrumbs for deep hierarchies
- Back button behavior should match expectations (browser and native)
- Never trap users in a flow without an obvious exit
**Aesthetics**
Visual design affects perceived usability. A polished interface is trusted more.
- Aesthetic quality is not decoration — it signals care and quality
- Never let aesthetic trends degrade usability
- Test visual changes for their effect on task performance
**Color**
Color communicates meaning. Design for users who cannot rely on color alone.
- Never use color as the sole indicator of meaning (error, success, required)
- Support color-blind users with shape, pattern, and label
- Red for errors only — don't use red for neutral actions
**Human-Interface Objects**
Interactive objects should behave consistently regardless of where they appear. A button
is a button. A link is a link.
- Component behavior should be predictable from appearance
- Reuse established patterns rather than reinventing interaction for each screen
---
### NNGroup's Interactivity Attributes
NNGroup identifies eight interaction qualities that shape how users perceive the product —
and by extension, the brand behind it.
| Attribute | Definition | Design Implication |
|---|---|---|
| **Responsiveness** | Speed of element reaction to input | Every action needs acknowledgment within 100ms |
| **Direct manipulation** | Whether users interact with objects themselves or through intermediaries | Drag-and-drop vs. menus; direct editing vs. form dialogs |
| **Precision** | Granularity of user control | Slider with fine control vs. coarse steps |
| **Pliability** | Ease of effecting change | How much effort does it take to change something? |
| **Continuous vs. discrete** | Smooth vs. stepped transitions | Volume slider vs. volume buttons |
| **Clear labels/feedback** | How well the system communicates available actions and consequences | Tooltips, labels, ARIA, helper text |
| **Expected behavior** | Alignment with user mental models | Does it do what it looks like it does? |
| **Consistency** | Conformity to established patterns | Same component → same behavior, always |
---
## Response Time and Feedback Design
### The Three Response Thresholds
| Threshold | Time | User Perception | Design Response |
|---|---|---|---|
| **Instantaneous** | ≤ 0.1s | Feels direct, no delay perceived | Visual state change only (button active state) |
| **Flow maintained** | 0.1s – 1.0s | User notices delay but stays focused | Spinner or skeleton screen |
| **Attention limit** | 1s – 10s | User disengages; must retain focus consciously | Progress indicator with estimated time |
| **Abandonment risk** | > 10s | Users leave, especially on web | Background processing + notification on complete |
### Feedback Types
**Visual feedback** — the default. Every interaction should have a visual state change.
**Motion feedback** — communicates that change is happening and in what direction.
- Page transitions communicate navigation direction (slide left = forward)
- Height animations communicate expand/collapse
- Fade communicates appearance/disappearance
**Haptic feedback** — for native mobile. Use sparingly and for meaningful confirmation.
- Success: single tap
- Warning: double tap
- Error: buzz pattern
**Audio feedback** — contextual. Avoid for routine actions.
### Perceived Performance Patterns
**Skeleton screens** — show layout structure while content loads. Better than spinners
for page-level content because they reduce perceived wait time and prevent layout shift.
**Optimistic UI** — apply the result of an action immediately in the UI before server
confirmation. Roll back on failure. Best for high-confidence actions (like, follow, upvote).
**Progress indicators** — use for actions over 1 second where the user is waiting. Show
percentage when deterministic; use animated indicator when indeterminate.
**Instant transitions** — avoid animating page-level transitions faster than 150ms or
slower than 400ms. The sweet spot is 200–300ms.
→ *See [reference/response-time.md](reference/response-time.md) for full implementation patterns.*
---
## Designing Interactions
### Component States
Every interactive component needs a complete state set. Missing states cause visual
regressions, accessibility failures, and inconsistent behavior.
| State | When It Applies | Design Requirements |
|---|---|---|
| **Default** | Initial, uninteracted state | Clear affordance of interactivity |
| **Hover** | Cursor/pointer over element (desktop) | Subtle visual change; avoid large layout shifts |
| **Focus** | Keyboard or programmatic focus | Must be visible (WCAG 2.4.7); never remove outline without replacement |
| **Active/Pressed** | During click/tap/down event | Immediate response; tactile feedback |
| **Loading** | Processing action | Spinner or skeleton; disable further input |
| **Disabled** | Not interactive | Visually muted; clearly not clickable |
| **Error** | Invalid input or action failure | Clear message; recovery path shown |
| **Success** | Action completed successfully | Positive confirmation; proceed prompt |
| **Empty** | No content to display | Helpful message; guide to add content |
| **Skeleton** | Content loading | Show layout structure; reduce perceived wait |
---
## Anti-Patterns
Organized by the dimension most likely to cause each failure.
### Words
- Error messages that blame the user ("you entered wrong data")
- Placeholder text as labels
- Jargon and technical terms in UI copy
- Inconsistent button labels for the same action
### Visual
- Color as the only indicator of state
- Low contrast text
- Missing focus indicators
- Inconsistent button styles
### Physical/Space
- Touch targets too small
- Clickable areas not aligned with visual affordance
- No hover state for desktop interactions
- Missing keyboard support
### Time
- Silent failures
- No loading state for async operations
- Spinners without progress indication for long operations
- Transitions too fast to perceive or too slow to tolerate
### Behaviour
- Inconsistent action naming
- No confirmation for destructive actions
- No undo for irreversible actions
- Form data lost on validation failure
