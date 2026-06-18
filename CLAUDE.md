# CLAUDE.md — Strava Auto-Kudos Bot

> Spec-driven working doc for this fork. This file is the source of truth for
> **what we're building, the plan, the constraints, and what changed**.
> Update the **Phase Tracker** statuses and the **Change / Decision Log** as
> work happens. Keep it accurate — it is loaded into context every session.

## Mission
Get a working *personal* auto-kudos bot running: a fork of
[`isaac-chung/strava-kudos`](https://github.com/isaac-chung/strava-kudos)
(Python + Playwright + GitHub Actions). Upstream is unmaintained and partially
broken; we are modernizing it. Keep changes **minimal and reviewable** — this is
a ~190-line script, not a rewrite.

## How we work (spec-driven)
1. The plan lives in the **Phase Tracker** below. Work one phase at a time.
2. Before non-trivial code changes, confirm the relevant spec item here.
3. After a change lands, append to the **Change / Decision Log** (date, what,
   why). Flip the phase/checkbox status.
4. If reality contradicts the spec (e.g. Strava's login flow differs from what's
   described), update the spec first, then code.
5. **PR review comments (incl. Copilot):** for each comment, review it, then
   implement the fix or consciously decide against it (with a reason). Fold the
   fix into the PR the comment is on, and **reply to that comment** recording the
   resolution (what changed + commit) before the PR is merged.

## Hard constraints (NEVER violate)
- **Credentials** only via env vars / GitHub secrets (`STRAVA_EMAIL`,
  `STRAVA_PASSWORD`). Never commit, print, or log them. Never echo them in CI.
- Keep **≥1s delay** between kudos clicks; keep the **`max_run_duration` cap**
  (currently 540s).
- **Firefox only** via Playwright — upstream author confirms Chromium fails.
  Keep Firefox.
- Don't **hammer login** repeatedly in a short window (Strava may temp-block the
  account). Reuse a session where practical during testing.
- If Strava forces **OTP/email-code or CAPTCHA** with no password path, **stop
  and report options** — do not fight it.
- Don't change the **feed-parsing logic** unless it's actually broken.

## Repository facts
- **Branch strategy:** the fork's `main` IS the working branch. Required because
  GitHub only runs *scheduled* workflows from the default branch.
- **Remotes:** `origin` → `github.com/karapk/strava-kudos` (the fork),
  `upstream` → `github.com/isaac-chung/strava-kudos`.
- **Local env:** system Python is **3.14.0**; **no venv yet** (first task);
  Playwright not installed.
- **Account:** logs in with **email + password**, no SSO (confirmed).
- Recent login/cookies/terms commits in history are **upstream's** attempts, not
  ours.

## How the existing code works (`give_kudos.py`, class `KudosGiver`)
- `__init__`: reads `STRAVA_EMAIL` / `STRAVA_PASSWORD`; launches **Firefox**
  (sync API); `max_run_duration=540`.
- `email_login()`: goes to `/login`, optionally clicks a "Reject" cookie button,
  fills email + password textboxes, clicks "Log In". ⚠️ **Most likely
  breakage** — assumes one-page email+password form; Strava now defaults to an
  emailed one-time code with a "use password instead" option.
- `_run_with_retries()`: generic retry-with-sleep helper. Keep it.
- `_get_page_and_own_profile()`: loads `dashboard?num_entries=100`, scrolls
  PageDown/PageUp ×5 to defeat lazy loading, reads own athlete ID from
  `.user-menu > a`.
- Feed parsing: items via `[data-testid=web-feed-entry]`; clicks
  `data-testid=unfilled_kudos`; skips own activities (athlete-ID compare), skips
  club posts (`group-header` / `.clubMemberPostHeaderLinks`), handles
  multi-participant group activities.
- `give_kudos()`: optionally accepts updated terms, iterates feed, prints
  `Kudos given: N`, closes browser.
- Workflow `.github/workflows/give_kudos.yml`: cron `30 5-23/6 * * *` (~4
  runs/day) + `workflow_dispatch`.

## Phase Tracker

Status key: ✅ done · 🔄 in progress · ⬜ not started · 🚧 blocked

| Phase | Description | Status |
|------|-------------|--------|
| 0 | Research; repo chosen over webhook/extension alternatives | ✅ |
| 1 | Repo forked + cloned; branch strategy set | ✅ |
| 2 | Local proof of concept (session reuse + full headless run) | ✅ |
| 3 | Modernize workflow + requirements | ✅ |
| 4 | GitHub Actions setup (user does most in browser) | ✅ |
| 5 | Schedule & tune cron | ✅ |
| 6 | Longevity (keepalive; optional upstream PR) | 🔄 current |

### Phase 2 — Local proof of concept
- [x] Create venv, `pip install playwright` (current), `playwright install firefox`.
- [x] Run **headed** with env vars set; observe where login breaks.
- [~] ~~Patch `email_login()` for the password path.~~ **ABANDONED** — Strava
      blocks automated login (persistent "An unexpected error occurred" wall on
      the email step, across 3 retried runs). Per the hard constraints we stop
      fighting it. Replaced login automation with **session reuse**:
      `save_session.py` (manual one-time login → `strava_state.json`), and
      `give_kudos.py` now loads that session instead of logging in.
- [x] **Capture session:** user ran `save_session.py`, logged in by hand,
      `strava_state.json` written and validated.
- [x] Confirm a full run: `give_kudos.py` loaded session → dashboard →
      `Kudos given: 24`, clean exit (2026-06-10). User verifying on Strava.
- [x] Re-test **headless** — the validated run above is already headless
      (default `headless=True`) and behaves the same. No UA/viewport tweak
      needed.
- [x] QoL: `main()` now screenshots `error.png` on unhandled failure (and
      re-raises so the job still fails). Feed parsing untouched. Done alongside
      Phase 3's failure-only artifact upload.

**Acceptance:** `python give_kudos.py` completes **headless** locally using a
saved session, gives kudos to un-kudoed friend activities, skips own activities
and club posts, exits cleanly within the duration cap.

### Phase 3 — Modernize the workflow
- [x] `runs-on: ubuntu-20.04` → `ubuntu-latest` (20.04 retired; jobs won't start).
- [x] `actions/checkout@v3` → `@v4`; `actions/setup-python@v4` → `@v5`.
- [x] Python `3.9.10` → `3.11`.
- [x] `requirements.txt` `playwright==1.30.0` → `1.60.0` (matches local/tested).
- [x] CI: `playwright install firefox --with-deps`.
- [x] Add **failure-only** artifact upload of `error.png` (`upload-artifact@v4`,
      `if: failure()`, `if-no-files-found: ignore`).
- [x] Workflow `env` now passes **`STRAVA_STATE_JSON`** (not email/password).
- [ ] Commit + push to fork's `main` (via PR — branch `chore/modernize-workflow`).

### Phase 4 — GitHub Actions setup (mostly user, in browser)
- [x] Actions enabled on the fork (verified via `gh` — `enabled: true`).
- [x] Secret **`STRAVA_STATE_JSON`** set (full contents of `strava_state.json`;
      read via the `STRAVA_STATE_JSON` env var). Email/password secrets are
      **no longer used** — login is not automated.
- [x] Triggered via `workflow_dispatch` — succeeded (`Kudos given: 65`, 2m46s,
      2026-06-18); athlete-id redaction verified in the public log. CI failures
      are debugged via the **Actions logs** (no screenshot artifact on this
      public repo). **Note:** the session expires; periodically re-run
      `save_session.py` locally and update the secret (see Phase 6).

### Phase 5 — Schedule & tune
- [x] Was 4 runs/day UTC (`30 5-23/6 * * *`).
- [x] Retuned to user preference: 09:00 / 14:00 / 18:00 / 21:00 **US Central
      (CDT)** = `0 2,14,19,23 * * *` UTC. 4 runs/day, ≥3h apart (within the "no
      more than every 2–3 hours" limit). Chose the simple UTC cron over a
      DST-aware gate job to keep the workflow minimal — accepts a 1h winter
      (CST) shift, which is fine for this bot.

### Phase 6 — Longevity
- [ ] Keepalive: GitHub disables cron workflows after **60 days** of repo
      inactivity. Add an action or documented periodic-commit habit.
- [ ] (Optional, later) Clean PR back to upstream from a branch off
      `upstream/main` with **only the general fixes** (runner bump, action bumps,
      Playwright upgrade, login fix) — exclude personal cron changes. Open an
      upstream issue announcing the fix first.

## Known breakages (verified)
1. **Workflow runner retired** — `ubuntu-20.04` no longer starts jobs.
2. **Playwright pin stale** — `1.30.0` (early 2023). Upgrade.
3. **Login is bot-blocked** — Strava rejects *automated* login on this account:
   submitting the email via Playwright reliably returns "An unexpected error
   occurred. Please try again." (3 retried runs, even with the email correctly
   re-filled). Conclusion: do **not** automate login. Use **session reuse**
   (`save_session.py` → `strava_state.json`) instead.

## Login flow (verified 2026-06)
Strava's `/login` is **passwordless-first**, and — critically — **hostile to
automation**:
- **STEP 1** `/login`: email input `#desktop-email` (placeholder "Your Email") +
  a `Log In` submit button. **No password field here.** Cookie banner is
  **Cookiebot** with an `OK` button (old `Reject` click was a silent no-op).
  Google/Apple SSO buttons also present (ignore).
- **STEP 2** "Switch to one-time codes" interstitial: **"Email me a code"**
  button + a **"Use password instead"** orange text link at the bottom (the
  password path the user remembered — it lives *here*, after email submit).
- **STEP 3**: would be the password field + `Log In`.
- **BLOCKER:** automating STEP 1 → the email submit returns "An unexpected
  error occurred." every time, so we never reliably reach STEP 2/3. This is
  anti-bot behavior, not a selector bug. **We don't fight it** (hard
  constraint). Login is now done **by hand once** via `save_session.py`; the
  bot reuses the saved session.

Temp investigation helper: `inspect_login.py` (gitignored — delete before any
upstream PR) walks the flow and dumps selectors + screenshots per step. Kept for
now in case a future, non-automated login path opens up.

## Change / Decision Log
_Newest first. One entry per meaningful change or decision._

- **2026-06-18** — **Phase 4 done (bot live in CI); Phase 5 cron retuned.**
  `workflow_dispatch` run succeeded — session reuse worked in CI, `Kudos given:
  65`, 2m46s, athlete-id redaction held in the public log. Secret set + cron
  active = the bot now runs automatically. Retuned cron `30 5-23/6 * * *` →
  `0 2,14,19,23 * * *` (09:00/14:00/18:00/21:00 US Central CDT) for peak
  activity-completion times; 4 runs/day, ≥3h apart. Chose the simple UTC cron
  over a DST-aware gate job (keeps the workflow minimal) — accepts a 1h winter
  shift. Phase 6 (longevity/keepalive) is next.
- **2026-06-18** — **Addressed Copilot review on PR #3 + documented the review
  process.** Fixed the stale `main()` comment (claimed the screenshot is uploaded
  as an artifact — untrue since PR #3) and stopped logging the Strava athlete id
  (`print("id", …)` → `print("Found own profile id.")`), since public-repo
  Actions logs would expose it (the only identifying output in the script).
  Added step 5 to "How we work": every PR review comment (incl. Copilot) is
  reviewed, implemented (or consciously declined), and replied to before merge.
- **2026-06-17** — **Phase 3 merged (PR #2); dropped the public `error.png`
  artifact.** PR #2 (workflow modernization + the `main()` cleanup hardening from
  Copilot review — construction inside `try`, single `finally` that closes the
  browser and stops the Playwright driver, guarded screenshot) merged to `main`.
  Then, because the fork is **public**, removed the `upload-artifact` step so a
  failure screenshot of the logged-in feed isn't world-downloadable;
  `give_kudos.py` still writes `error.png` locally, and CI failures are diagnosed
  from the credential-free Actions logs. Phase 4 underway: Actions enabled and
  the workflow is registered; only the `STRAVA_STATE_JSON` secret remains before
  a first `workflow_dispatch`.
- **2026-06-11** — **Phase 3: modernized the workflow.** `give_kudos.yml`:
  `ubuntu-20.04`→`ubuntu-latest`, `checkout@v3`→`@v4`, `setup-python@v4`→`@v5`,
  Python `3.9.10`→`3.11`, `playwright install`→`playwright install firefox
  --with-deps`, and a failure-only `error.png` artifact (`upload-artifact@v4`).
  The `env` block now passes `STRAVA_STATE_JSON` (the saved session) instead of
  `STRAVA_EMAIL`/`STRAVA_PASSWORD`. `requirements.txt` `playwright`
  `1.30.0`→`1.60.0` (matches local). `give_kudos.py` `main()` screenshots
  `error.png` on unhandled failure then re-raises. Done on branch
  `chore/modernize-workflow`; Phase 4 (user adds the `STRAVA_STATE_JSON` secret +
  triggers) is next.
- **2026-06-10** — **Phase 2 acceptance met.** First full session-reuse run:
  `give_kudos.py` loaded `strava_state.json`, walked 100 feed entries headless,
  skipped club posts + own activities, printed `Kudos given: 24`, clean exit. 3
  entries hit the pre-existing "owners-name" skip (fail-safe — skipped, never
  wrongly kudo'd); feed parsing left untouched per constraint. Phase 2 → ✅;
  Phase 3 (workflow modernization) is next.
- **2026-06-10** — **Pivoted login → session reuse.** Confirmed via
  `inspect_login.py` (headed + screenshots) that the real flow is email →
  "Switch to one-time codes" interstitial (with a "Use password instead" link) →
  password page. But **every automated email submit returns "An unexpected error
  occurred"** (3 retried runs, email re-filled each time) — Strava is blocking
  bot login. Per the hard constraints, stopped fighting it. Added
  **`save_session.py`** (manual one-time login → `strava_state.json`) and
  rewrote `give_kudos.py`: removed broken `email_login()`, added
  `_load_storage_state()` (reads `STRAVA_STATE_JSON` env or `STRAVA_STATE_FILE`
  path) + `start_session()`; `__init__` now builds a `browser.new_context(
  storage_state=…)`. Gitignored `strava_state.json` (it's a credential) and
  `inspect_login.py`. Both files byte-compile; awaiting user's first
  `save_session.py` run to validate a full kudos run.
- **2026-06-10** — Phase 2 started. Installed Playwright **1.60.0** + Firefox
  **150.0.2** in `venv`. Confirmed login breakage via headless probe: STEP 1 has
  no password field (passwordless-first flow). User confirmed STEP 2 offers OTP
  code with a "use password instead" option. Built `inspect_login.py` to capture
  exact STEP 2/3 selectors via a watchable headed run; awaiting that output
  before rewriting `email_login()`.
- **2026-06-10** — Created `CLAUDE.md` as the spec/plan/change tracker.
  Confirmed repo state: no venv, system Python 3.14.0, Playwright not installed;
  remotes `origin`=karapk fork / `upstream`=isaac-chung; recent login-related
  commits are upstream's, so Phase 2 login work is genuinely unstarted. Entering
  Phase 2.
