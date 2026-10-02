# Design guide

Every screen draws from one theme in light and dark. Tokens live only in `<tokens file>`; screens are built from the components in `<components folder>`, the layouts in `<layouts folder>`, and the patterns in `<patterns folder>`. Lint and kit's token check fail on drift and name what to use instead. Where the look came from: [look.md](look.md).

## Look at it

- **The gallery** → on the dev server, open `<gallery route>`: Foundations shows every token by name, Components every component in each state, then a page per layout and pattern. Production builds have no gallery
- **Screenshots** → `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/screens.py <dir> <route>` writes phone and desktop shots in light and dark
- **The theme** → light, dark, or system (the default), chosen from <where the choice lives>

## Check it

- **Lint** → rejects raw colours, palette colours, arbitrary sizes, and native controls outside the components folder (see What lint rejects)
- **Tokens** → kit's `check_tokens.py` runs in every gate: each text pair at least 4.5:1 and each focus ring or control border at least 3:1, in both themes; no colour in any other CSS file
- **Accessibility** → axe on every route in `<route list file>` and every gallery page, light and dark; a new page adds its route there
- **UX checks** → UX probes run `tests/kit/ux-checks.ts`: side scroll, tap targets under 44px, clipped text, focus lost to the page

## Tokens

Use each through its class (`bg-<token>`, `text-<token>`, `border-<token>`) or `var(--<token>)`. Every token has a light and a dark value; a new one also gets a swatch on Foundations.

- **`--background` / `--foreground`** → the page, and body text and headings on it
- **`--card` / `--card-foreground`** → cards and their text
- **`--popover` / `--popover-foreground`** → menus, select lists, and other floating layers
- **`--muted` / `--muted-foreground`** → quiet fills (skeletons, table header bands); secondary text (labels, captions, help)
- **`--accent` / `--accent-foreground`** → hover and selected fill for neutral items; not the brand colour
- **`--primary` / `--primary-foreground`** → the one solid accent fill: the primary button, checked controls; one per view
- **`--secondary` / `--secondary-foreground`** → secondary button fill
- **`--border`, `--input`, `--ring`** → hairlines; control borders; focus rings
- **`--success`, `--warning`, `--danger`, `--info`, each with `-bg`** → status as text on its own tint; state, never decoration
- <each further token from look.md, with what it's for>

## Type, spacing, radii, elevation

- **Type** → <size> labels and captions; <size> body, tables, and controls (the default); <size> section headings; <size> page titles
- **Faces** → <UI face> for UI; <mono face> only for IDs and codes; tabular figures for numbers in columns, right-aligned
- **Spacing** → the 4px grid: <control height> controls, <row height> rows; 44px controls on touch screens
- **Radii** → <badges>, <controls>, <cards>, <dialogs and panels>
- **Elevation** → depth from tone steps and hairlines; the only shadow is for floating layers

## Components

One line per need, filled in as the kit is built: `<need> → <component> from <path>; <variants or when not to use it>`.

- **An action** → `Button`: one primary per view; outline, ghost, destructive, link; a loading state while pending
- **A field** → a label above the control; errors linked with `aria-invalid` and `aria-describedby`
- <each component the build adds>
- **Missing a component** → add it to the components folder, restyle it to the tokens, and show it on Components before hand-rolling one

## Pick a layout

Every screen is one page type, built with that type's layout.

- **Any app page** → inside the app shell → [App shell](#app-shell)
- **Many records of one kind** → list → [List](#list)
- **One record** → detail → [Detail](#detail)
- **Creating or editing a record** → form → [Form](#form)
- **Settings for an account, the workspace, or a feature** → settings → [Settings](#settings)
- **A screen that fits none** → ask the requester; a new layout arrives with a spec decision, its section here, and its gallery page

### App shell

- **Navigation** → <sidebar or top bar>; the current place marked with `aria-current="page"`
- **Page title** → one `h1` per page, first in the content
- **Phone width (under 768px)** → navigation opens from a menu button as a sheet that traps focus and returns it to the button

### List

- **Header** → the `h1` and one line on what the list holds; one primary with a verb-object label ("Create invoice") on the right
- **Search** → a field labelled for the object ("Search invoices…"), kept in the URL so reload and Back keep it
- **Rows** → the name or ID first, linking to the detail page; status as a badge; numbers right-aligned; row actions in a "…" menu, destructive last
- **Long content** → names and emails wrap to show in full; at phone width secondary columns hide before anything scrolls sideways
- **No records yet / nothing matches** → [No records yet](#no-records-yet) keeps only the header; nothing matching keeps the search and offers to clear it

### Detail

- **Header** → the `h1` with its status beside it, one muted line under it, then at most one primary action, one outline, and a "…" menu for the rest
- **Properties** → label and value rows; an empty value is a prompt ("Assign", "Add label"), never "None"
- **Phone width** → properties move under the title, above the content; nothing scrolls sideways

### Form

- **Container by field count** → a dialog up to 5 fields, a side sheet for 6 to 15, a full page past that; count every control
- **Fields** → the label above the control; "Optional" after the label when most fields are required; help text under the control
- **Footer** → Cancel, then the one primary naming a verb and object ("Create client"), or "Save changes" on an edit
- **Invalid submit** → each error replaces its field's help text and says what to enter; focus moves to the first; nothing saves or closes
- **Guards** → Esc, close, or Cancel after edits asks "Discard changes?" with Keep editing first; ⌘Enter or Ctrl+Enter submits from any field

### Settings

- **Rows** → the label and a one-line description on the left, the control on the right; under the width of both, the control drops below
- **Saving** → switches and selects save as they change; a section of text fields has its own Save and shows a muted "Saved" for 2 seconds
- **Danger zone** → the last section; each row says the consequence and has a destructive button naming the action

## Pick a pattern

Every screen handles the same moments the same way.

- **An action succeeded or failed** → [Notices](#notices)
- **Removing something** → [Removing things](#removing-things)
- **Waiting for data** → [Waiting](#waiting)
- **A list with no records yet** → [No records yet](#no-records-yet)
- **Anything, from the keyboard** → [Keyboard and focus](#keyboard-and-focus)

### Notices

- **Where** → bottom right, newest on top, three at most; full width on a phone
- **Success** → past tense, object first, no exclamation mark ("Invoice INV-1047 sent"); leaves after 4 seconds, or 8 with Undo
- **Failure** → the title says what failed, the description what to do; stays until dismissed; Retry only when trying again could work
- **Not a notice** → an invalid field (error under it) or a section saved in place (a muted "Saved")
- **Focus** → a notice never takes focus on its own; one that closes while focused hands it back to where it came from

### Removing things

- **Reversible (archive, remove a label)** → act at once, then a notice with Undo; no dialog
- **Permanent** → a dialog asking "Delete <type> <name>?", saying what goes with it and that it can't be undone; Cancel has focus; the button repeats the verb and object
- **Permanent and costly (cascading, billing, the workspace)** → also ask for the name typed exactly before the button enables
- **After** → the dialog closes, a notice says it's done, and focus moves to the next row's same control, never the page body

### Waiting

- **At once** → navigation, the title, the primary action, and toolbars; only the region holding the data waits
- **Placeholders** → shaped like the content at its real size, shown only after 200ms; a screen reader hears "Loading <objects>…"
- **Refresh** → keeps the old content, dimmed and `aria-busy`, until the new content lands
- **Inside a button** → a spinner, and the button disabled while it works

### No records yet

- **What stays** → the page header and its create action
- **What shows** → the object's icon, a title ("No invoices yet"), one line on what the object is for, and the same create action

### Keyboard and focus

- **Reaching things** → every control in reading order with a visible focus ring, in both themes
- **Overlays** → menus, dialogs, and sheets trap Tab and return focus to their trigger on close
- **A control that leaves while focused** → hands focus to its neighbour (the next row, else the one before, else the list's header), never the page body

## What lint rejects

Outside the components folder, lint fails on:

- **Raw colours** (`bg-[#1b1b1b]`, `style={{ color: '#f00' }}`) → a token class or `var(--token)`
- **Palette colours** (`bg-red-500`, `text-zinc-900`, `bg-white`) → a token class; palette colours don't follow the theme
- **Arbitrary sizes** (`w-[13px]`, `style={{ padding: '13px' }}`) → the type scale, spacing steps, and radii above
- **Native controls** (`<button>`, `<input>`, `<select>`, `<textarea>`) → the component that wraps them

The components themselves may tune raw values; that is where a new size or state belongs.

## Growing the guide

- **A feature needs a layout or pattern the guide lacks** → its spec decides the shape; its build adds the component, a section here, and a gallery page
- **A second feature reuses a piece one feature built** → move it to the shared folder and give it a section here
- **A piece only one feature uses** → it stays in that feature
