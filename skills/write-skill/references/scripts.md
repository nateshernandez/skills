# Skill scripts

An agent runs the script and reads what comes back; every byte lands in its context. A script must run from any directory, with no setup.

## Shape

- **Starting a script** → shebang, usage docstring, `def main() -> int`, `sys.exit(main())`
  - _Because:_ one shape means every script reads, runs, and composes the same way
- **Script does more than one job** → split it
  - _Because:_ one script = one job, same as one skill = one flow
- **Needs a third-party package** → declare it inline (PEP 723 `# /// script`) and run with `uv run`
  - _Because:_ the skill must work wherever it's copied, with no install step
- **Referencing a file** → resolve it from `Path(__file__).parent`, `${CLAUDE_SKILL_DIR}`, or an argument
  - _Because:_ the agent may run the script from any working directory
  - ✗ `open("references/format.md")` ✓ `Path(__file__).parent.parent / "references" / "format.md"`
- **Sharing code between scripts** → keep them in one folder and import the sibling module directly
  - _Because:_ Python already puts the script's folder on `sys.path`; editing it confuses the type checker

## Input and output

- **Invoked with missing or bad arguments** → print the usage docstring to stderr and return 1
  - _Because:_ an agent recovers from a usage message, not from a traceback
- **Reporting** → results to stdout, problems to stderr, exit 0 only on success
  - _Because:_ the agent branches on the exit code and reads the right stream
- **Writing a message** → keep it short and name the file and the fix
  - _Because:_ vague or long output wastes the agent's context
  - ✗ `Error: validation failed` ✓ `Flow: 12 nodes (max 10); split the skill`
- **Script needs input** → take it from arguments or stdin, never an interactive prompt
  - _Because:_ an agent can't answer a prompt; the run just hangs
