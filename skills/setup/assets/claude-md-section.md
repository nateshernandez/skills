## Building features with kit

- **Building a feature** → `/kit:build <request>`; specs, plans, reviews, and reports live in `specs/<id>/`
- **Where it stands** → `/kit:build <spec number>` resumes from the files in `specs/<id>/`
- **Gates** → `.claude/kit/config.json` names the commands every task must pass
- **Decision records** → `docs/decisions/`, written by the build that first implements the choice
