# Security checklist

Walk each entry point the diff adds or changes: endpoints, server actions, handlers, CLI arguments, pages reading params, and anything reading environment variables. The project's own checklist, `.claude/kit/checklists/security.md`, adds stack-specific checks.

- **Validation** → every field is validated on the server; client checks don't count
- **Authorization** → the server decides who may act; IDs from the client are never trusted
- **Exposure** → responses carry only fields the caller needs
- **Secrets** → server-only values never reach client bundles, logs, or error messages
- **Injection** → no string-built SQL, shell commands, or file paths from input
- **XSS** → no raw HTML rendered from input; no `javascript:` links from data
- **SSRF** → no server fetch of user-supplied URLs without an allowlist
- **Abuse** → repeats and large payloads are bounded where the spec or plan says so
- **Errors** → messages don't leak stack traces, paths, or other users' data
- **Dependencies** → the configured `audit`; high or critical in a runtime dependency is a blocker

## Probe patterns

- **Skip client validation** → call the endpoint directly (`request.post` in Playwright, `fetch` in Vitest) with the bad payload
- **Cross-user access** → act as user A, then request user B's resource by ID
- **Repeats** → send the same request in parallel and count what was stored
