---
id: <id>
status: draft
size: L
---

# Core screens and patterns

An agent building any screen picks its layout from the guide and handles every common moment the same way.

## Decide

- **<n>.D1 How an agent picks a layout** → the guide maps each screen type to one layout, its rules, and a gallery example
  - _Alt:_ guidelines only, agents compose freely from components; more freedom, more drift (design lens)
- **<n>.D2 Form container** → a dialog up to 5 fields, a side sheet for 6 to 15, a full page past that
  - _Alt:_ always a full page; one rule, slower for small edits (UX lens)
- **<n>.D3 Notices** → bottom right, three at most; 4 seconds, 8 with Undo; failures stay until dismissed
  - _Alt:_ top centre; more visible, but covers page headers and actions (design lens)
- **<n>.D4 Removing things** → reversible acts at once with Undo; permanent asks in a dialog naming the item
  - _Alt:_ a dialog for everything; simpler, but trains people to click through (UX lens)
- **<n>.D5 Waiting** → the frame shows at once; placeholders shaped like the content only after 200ms
  - _Alt:_ a spinner in the content area; simpler, but the page jumps when data lands (design lens)

## Behaviors

- **<n>.B1 Any app page at phone width** → navigation opens from a menu button, traps focus, and returns it on close
- **<n>.B2 List layout in the gallery** → title, one primary action, search; each row links to its detail page
- **<n>.B3 Detail layout in the gallery** → title, status, primary and secondary actions, then properties and content
- **<n>.B4 Longest real names and emails at phone width** → shown in full by wrapping; nothing scrolls sideways
- **<n>.B5 Form submitted with a missing field** → error under the field saying what to enter; focus moves there; nothing saved
- **<n>.B6 Form closed with Esc after edits** → asks to discard changes; untouched, it closes at once
- **<n>.B7 Settings layout in the gallery** → label-left rows, each section saves on its own, a muted Saved after
- **<n>.B8 An action succeeds** → a past-tense notice, with Undo when reversible; focus stays where it was
- **<n>.B9 An action fails** → the notice says what failed and what to do; Retry only when retrying could work
- **<n>.B10 User deletes a permanent item** → dialog names it, Cancel has focus, the button repeats the verb and object
- **<n>.B11 A list with no records yet** → an icon, a title, one line on what it's for, and the create action
- **<n>.B12 Keyboard only, in every pattern** → focus is visible, overlays return it, and a removed control hands it on

## Not doing

- Domain layouts such as boards, timesheets, or invoices, until a feature needs one
- Filters, bulk selection, and a command palette, until a feature needs them
- Real data behind the layouts; the gallery uses fixed samples

## Looks like

![List layout](screens/list-desktop-light.png)
![Detail at phone width, dark](screens/detail-mobile-dark.png)
![Form in a side sheet](screens/form-desktop-light.png)
![Delete confirm](screens/confirm-desktop-light.png)

<a one-theme app shows every screen in that theme>
