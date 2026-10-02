# Example spec

A real spec from the first `/build` run, renumbered to the current ID format (a browser-only time tracker), for reference when filling assets/spec-template.md.

````markdown
---
id: 001-track
status: approved
size: M
---

# Time tracker

Someone types what they're working on, times it, and sees today's entries with durations.

## Decide

- **1.D1 Two entries share a description** → kept as separate entries, not merged
  - _Alt:_ merge into one summed entry, which hides how many sessions it took
- **1.D2 Order of today's list** → newest entry first
  - _Alt:_ oldest first, reading top to bottom like a log
- **1.D3 What counts as "today"** → local midnight to local midnight
  - _Alt:_ rolling 24 hours, which drifts from the calendar day the user expects
- **1.D4 Where entries live** → browser localStorage, no account or server
  - _Alt:_ sessionStorage, which would lose entries when the tab closes
- **1.D5 Duration display** → `MM:SS`, switching to `H:MM:SS` past one hour
  - _Alt:_ always `H:MM:SS`, noisier for short entries

## Behaviors

- **1.B1 Visitor opens /track with no entries yet** → description field, disabled Start, "no entries yet" in the list
- **1.B2 Visitor clicks Start with an empty description** → Start stays disabled; nothing starts
- **1.B3 Visitor types a description and clicks Start** → timer runs and visibly ticks up; field locks; Start becomes Stop
- **1.B4 Visitor clicks Stop** → entry appears in today's list with its description and duration; field unlocks and clears for the next entry
- **1.B5 Page is reloaded while a timer is running** → the same timer keeps running with its description and elapsed time, per 1.D4
- **1.B6 Page is reloaded after entries were stopped** → today's list still shows them, per 1.D4
- **1.B7 An entry was stopped before local midnight** → it no longer appears once it's a new day, per 1.D3
- **1.B8 Viewed at 375px wide** → field, button, and list stay usable with no horizontal scroll

## Not doing

- Editing or deleting a saved entry
- Running more than one timer at a time
- A totals-per-day summary
- Exporting or syncing entries across devices

## Looks like

![Idle state, no entries](screens/track-idle-mobile.png)
![Timer running with one stopped entry](screens/track-running-desktop.png)
````
