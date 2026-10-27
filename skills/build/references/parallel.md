# Parallel builds

A plan whose tasks list `needs` and `files` can be built side by side. Each builder works in its own git worktree, so builders never share a tree, a gate, or a server port.

## When

- **A wave** → standard mode, `build.parallel` above 1, and `spec_status.py <id>` listing two or more tasks under `ready now`
  - Otherwise build the one ready task as before; a plan with no `needs` is a sequential list
- **Turbo and size S** → one builder, no waves
- **The first task** → the planner makes it the shared surface (types, stubs, dependencies, registries), so later tasks mostly add files

## Running a wave

1. Take up to `build.parallel` tasks from `ready now`
2. Start one builder per task in the same message, each with the Agent tool's `isolation: "worktree"`; the prompt is the spec ID, the task ID, the round, and the word `wave`
3. Each returns its task ID, `passes` with its branch name (from `git branch --show-current`) and a progress line, or `blocked: <reason>`
4. As each finishes, land it, in the order they passed: `land_task.py <id> <task> <branch> --line "<progress line>"`
   - It checks the task passed in its worktree and touched only its `files`, replays its commits on the spec branch, marks it passing, and removes the worktree
5. When the wave is landed, commit `tasks.json` and `progress.md` once, then run `gate.py <id>` once on the merged tree
6. Ask `spec_status.py` for the next ready tasks; stop when none are left

## When something goes wrong

- **A builder reports blocked** → land the others; fix the plan or tests yourself, then run the task again on the new tip
- **`land_task.py` reports a conflict or stray files** → the plan's `files` or `needs` were wrong; fix tasks.json (`check_tasks.py`), then rebuild that task from the current tip
- **The wave gate is red** → one `F` task per failing test, as after a review; never reopen a landed task
- **A worktree builder fails its setup** → check `build.worktree_setup`; every builder in the wave will fail the same way

## Cost

Each builder starts cold and runs its own gate, so a wave of three costs about three builders in tokens and finishes in about the time of the slowest. Waves pay off when tasks are independent and the gate is fast, which is why unit-level tests run in the task gate and the full end-to-end suite waits for the full gate.
