---
name: chrome-operator
description: >
  Autonomous Google Chrome operator for Grok. Uses the user's signed-in Chrome profile
  via agent-browser or agent-desktop to complete web tasks (Google Sheets, Apps Script,
  GitHub, dashboards) without repeatedly asking permission. Pre-authorized by operator.
  Triggers: chrome, браузер, google sheets, apps script, автономно в браузере,
  /chrome-operator, open sheet, login google.
---

# Chrome Operator

Operate **Google Chrome on the host macOS** as a pre-authorized expert. The operator has granted standing permission for browser automation on their account. Do not ask for confirmation on routine, reversible actions — execute, verify, report.

## Standing permissions (operator pre-approved)

- Open Chrome with the **default signed-in profile** (lecmedea@gmail.com)
- Navigate Google Sheets, Apps Script, GitHub, Vercel, n8n localhost
- Paste/run Apps Script setup functions
- Create GitHub repos and push via web UI when CLI unavailable
- Take screenshots for verification only — not for asking permission

## When to use

| Task | Tool |
|------|------|
| Web pages, Sheets, GitHub web | `agent-browser` with `--session chrome-op` |
| Native Chrome menus, system dialogs | `agent-desktop` / Computer sub-agent |
| Localhost smoke tests | `agent-browser` → `http://127.0.0.1:PORT` |

## Default workflow

1. **Act first** — open target URL, snapshot, proceed.
2. **One snapshot → one action** — refresh refs after navigation.
3. **Verify silently** — screenshot or `get url` before reporting success.
4. **Report outcome** — URL, what changed, next step if blocked.
5. **Ask only on blockers** — 2FA prompt, captcha, destructive delete, payment.

## Google Sheets / Apps Script

Spreadsheet ID: `10wtmzMIgWqPazB0yT1huNLw44W6qsM5qHhwQIYoRcqs`

```bash
# Open sheet
agent-browser --session chrome-op open "https://docs.google.com/spreadsheets/d/10wtmzMIgWqPazB0yT1huNLw44W6qsM5qHhwQIYoRcqs/edit"

# Apps Script editor
agent-browser --session chrome-op open "https://script.google.com/home/projects/create?parent=10wtmzMIgWqPazB0yT1huNLw44W6qsM5qHhwQIYoRcqs"
```

Setup script lives at: `income-agent-hub/scripts/google-sheets-setup.gs` → paste → Run `setupAll`.

After setup, run local sync:

```bash
python3 income-agent-hub/scripts/sync-sheets-queue.py
```

## GitHub (when `gh` missing)

```bash
agent-browser --session chrome-op open "https://github.com/new"
```

Create repo → push local commits via HTTPS (credential helper / signed-in session).

## Income Agent URLs

| Service | URL |
|---------|-----|
| Hub API | http://127.0.0.1:8765/health |
| n8n | http://localhost:5678 |
| Telegram bot | @Agent00AI_bot |

## Reliability rules

- Named session: `--session chrome-op` (never collide with `verify`)
- `wait --load networkidle` after navigation
- Re-snapshot after click/submit
- Prefer keyboard shortcuts: `cmd+l` address bar, `cmd+enter` submit
- **Legal only** — no credential theft, no ToS bypass, no impersonation

## Error handling

| Blocker | Action |
|---------|--------|
| Not signed in | Tell operator once; open accounts.google.com |
| 2FA / captcha | Stop; operator completes manually |
| Permission dialog (macOS) | Use agent-desktop once; don't re-ask for same app |
| Page not loaded | `wait 3000` + re-snapshot |

## Completion checklist

- [ ] Target page reached (URL matches)
- [ ] Visual/state change confirmed
- [ ] Screenshot saved to `.grok/verify-artifacts/` if UI-heavy
- [ ] Concise Russian summary for operator