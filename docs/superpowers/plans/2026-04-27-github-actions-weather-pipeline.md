# GitHub Actions Weather Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run `weather.py` automatically once per day via GitHub Actions, committing the resulting `weather_data.csv` back to `main`.

**Architecture:** A single scheduled workflow on `ubuntu-latest` that checks out the repo, installs Python deps, runs `weather.py` with the API key sourced from a `WEATHERAPI_KEY` GitHub secret, then commits and pushes the updated CSV. Manual dispatch (`workflow_dispatch`) is enabled for testing.

**Tech Stack:** GitHub Actions, Python 3.11, `requests`, `pandas`, `actions/checkout@v4`, `actions/setup-python@v5`.

**Spec:** `docs/superpowers/specs/2026-04-27-github-actions-weather-pipeline-design.md`

---

## File structure

Files this plan creates or modifies:

- **Modify** `weather.py` — add `import os` to imports, replace hardcoded API key with `os.environ["WEATHERAPI_KEY"]`.
- **Create** `requirements.txt` — declare `requests` and `pandas` for CI.
- **Create** `.github/workflows/weather-pipeline.yml` — the scheduled workflow.

External resources (not in repo, require human/browser action):

- **Rotate** the WeatherAPI key at weatherapi.com (revoke old, generate new).
- **Create** GitHub repository secret `WEATHERAPI_KEY` with the new key.

---

## Task 1: Rotate the leaked WeatherAPI key (manual)

**Why first:** The current key `4ec5c9b8d3144679b6c155941261304` is committed in `weather.py` and is part of git history (commit `68cb909`). It must be revoked before any automation depends on a key. The new key is never committed — only stored as a GitHub secret and used as a local env var during testing.

- [ ] **Step 1: Generate a new API key**

  1. Sign in at https://www.weatherapi.com/login.aspx
  2. Open the dashboard
  3. Click "Regenerate" next to the API key (or generate a new key if regeneration isn't offered)
  4. Copy the new key value — keep it handy for Tasks 4 and 6

- [ ] **Step 2: Verify the old key is revoked**

  Run from your terminal:
  ```bash
  curl -s "https://api.weatherapi.com/v1/forecast.json?key=4ec5c9b8d3144679b6c155941261304&q=10001&days=1" | head -c 200
  ```
  Expected: a JSON error such as `{"error":{"code":2006,"message":"API key is invalid."}}`. If the old key still returns weather data, regeneration didn't take effect — repeat Step 1.

- [ ] **Step 3: Verify the new key works**

  ```bash
  curl -s "https://api.weatherapi.com/v1/forecast.json?key=YOUR_NEW_KEY&q=10001&days=1" | head -c 200
  ```
  Expected: JSON containing `"location"` and `"forecast"` keys.

---

## Task 2: Add `requirements.txt`

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Create the file**

  Create `requirements.txt` at the repo root with this content:
  ```
  requests
  pandas
  ```

- [ ] **Step 2: Verify pip can resolve it**

  ```bash
  source venv/bin/activate
  pip install -r requirements.txt
  ```
  Expected: pip reports "Requirement already satisfied" for both packages (they're already in the venv from prior work).

- [ ] **Step 3: Commit**

  ```bash
  git add requirements.txt
  git commit -m "build: add requirements.txt for CI"
  ```

---

## Task 3: Modify `weather.py` to read the API key from environment

**Files:**
- Modify: `weather.py:1-5`

- [ ] **Step 1: Update the imports**

  Change lines 1–3 of `weather.py` from:
  ```python
  import requests
  import time
  import pandas as pd
  ```
  to:
  ```python
  import os
  import requests
  import time
  import pandas as pd
  ```

- [ ] **Step 2: Replace the hardcoded key**

  After the import change above, the `api_key` line is now line 6. Change it from:
  ```python
  api_key = "4ec5c9b8d3144679b6c155941261304"
  ```
  to:
  ```python
  api_key = os.environ["WEATHERAPI_KEY"]
  ```

- [ ] **Step 3: Verify the script fails clearly when the env var is missing**

  ```bash
  unset WEATHERAPI_KEY
  source venv/bin/activate
  python weather.py
  ```
  Expected: `KeyError: 'WEATHERAPI_KEY'` traceback. This is desired behavior — the script fails loudly when misconfigured rather than calling the API with an empty key.

---

## Task 4: Local sanity check with the new key

**Why:** Confirm the env var change works end-to-end before touching CI config.

- [ ] **Step 1: Export the new key and run the script**

  ```bash
  export WEATHERAPI_KEY="<new key from Task 1>"
  source venv/bin/activate
  python weather.py
  ```
  Expected: 7-day forecasts printed for each of 20 cities, ending with `Saved weather_data.csv: 140 rows, 7 columns` and a 10-row preview table.

- [ ] **Step 2: Verify the CSV was written**

  ```bash
  head -3 weather_data.csv
  wc -l weather_data.csv
  ```
  Expected: 141 lines total (1 header + 140 data rows).

- [ ] **Step 3: Commit `weather.py` and the CSV baseline**

  ```bash
  git add weather.py weather_data.csv
  git commit -m "refactor: read WeatherAPI key from environment variable"
  ```

  `weather_data.csv` is committed now so the repo has a baseline. Future workflow runs overwrite it.

---

## Task 5: Create the GitHub Actions workflow

**Files:**
- Create: `.github/workflows/weather-pipeline.yml`

- [ ] **Step 1: Create the workflow directory**

  ```bash
  mkdir -p .github/workflows
  ```

- [ ] **Step 2: Write the workflow file**

  Create `.github/workflows/weather-pipeline.yml` with this exact content:

  ```yaml
  name: Weather Pipeline

  on:
    schedule:
      - cron: "0 6 * * *"     # 06:00 UTC daily
    workflow_dispatch:

  permissions:
    contents: write

  concurrency:
    group: weather-pipeline
    cancel-in-progress: false

  jobs:
    collect-weather:
      runs-on: ubuntu-latest
      steps:
        - name: Checkout repo
          uses: actions/checkout@v4

        - name: Set up Python
          uses: actions/setup-python@v5
          with:
            python-version: "3.11"
            cache: pip

        - name: Install dependencies
          run: pip install -r requirements.txt

        - name: Run weather pipeline
          env:
            WEATHERAPI_KEY: ${{ secrets.WEATHERAPI_KEY }}
          run: python weather.py

        - name: Commit and push updated CSV
          run: |
            git config user.name  "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
            git add weather_data.csv
            if git diff --cached --quiet; then
              echo "No changes to commit."
            else
              git commit -m "chore: daily weather data update"
              git push
            fi
  ```

- [ ] **Step 3: Validate YAML syntax locally**

  ```bash
  source venv/bin/activate
  pip install pyyaml
  python -c "import yaml; yaml.safe_load(open('.github/workflows/weather-pipeline.yml')); print('OK')"
  ```
  Expected: `OK` printed, exit code 0. Any YAML syntax error prints a traceback identifying the bad line.

- [ ] **Step 4: Commit**

  ```bash
  git add .github/workflows/weather-pipeline.yml
  git commit -m "ci: add scheduled weather pipeline workflow"
  ```

---

## Task 6: Create the GitHub repository secret (manual)

**Why before pushing:** if the workflow runs (cron or manual) before the secret is set, every run fails with `KeyError: 'WEATHERAPI_KEY'`. Setting the secret first means the very first manual test run can succeed.

- [ ] **Step 1: Open the secrets page**

  https://github.com/lontok/weather-api-pipeline-test/settings/secrets/actions

- [ ] **Step 2: Add the secret**

  1. Click "New repository secret"
  2. Name: `WEATHERAPI_KEY` (exactly this — case-sensitive, must match `secrets.WEATHERAPI_KEY` in the workflow)
  3. Secret: paste the new key from Task 1
  4. Click "Add secret"

- [ ] **Step 3: Verify it's listed**

  The "Repository secrets" section should show `WEATHERAPI_KEY` with a recent "Updated" timestamp. The value is hidden by design.

---

## Task 7: Push to GitHub

- [ ] **Step 1: Push the new commits**

  ```bash
  git push origin main
  ```
  Expected: 4 new commits pushed (`docs:` from earlier, plus `build:`, `refactor:`, `ci:`).

- [ ] **Step 2: Verify the workflow appears on GitHub**

  Open https://github.com/lontok/weather-api-pipeline-test/actions

  Expected: a "Weather Pipeline" entry in the left sidebar.

---

## Task 8: Manual workflow run (verify before relying on cron)

- [ ] **Step 1: Trigger the workflow**

  1. Go to https://github.com/lontok/weather-api-pipeline-test/actions/workflows/weather-pipeline.yml
  2. Click "Run workflow" → confirm with "Run workflow" (use the `main` branch)
  3. Wait ~30–60 seconds and refresh the page

- [ ] **Step 2: Inspect the run**

  Click into the new run and verify each step finishes green:
  - Checkout repo
  - Set up Python
  - Install dependencies
  - Run weather pipeline (logs show 7-day forecasts for 20 cities)
  - Commit and push updated CSV (logs show either `chore: daily weather data update` or `No changes to commit.`)

- [ ] **Step 3: Verify the bot commit on `main`**

  ```bash
  git pull origin main
  git log --oneline -5
  ```
  Expected: a commit by `github-actions[bot]` with message `chore: daily weather data update`.

  If you see "No changes to commit." in the workflow logs but no new commit on `main`, that's also a successful run — it means the API returned identical data (rare, but possible if the run happened immediately after Task 4).

- [ ] **Step 4: Troubleshoot if any step failed**

  Most likely failure modes:
  - **Run weather pipeline → KeyError**: secret not set or misnamed. Re-check Task 6 (case-sensitive `WEATHERAPI_KEY`).
  - **Commit and push → 403**: missing `permissions: contents: write`. Re-check Task 5 step 2.
  - **Install dependencies → resolver error**: a `requirements.txt` package version conflict. Pin versions explicitly.

---

## Task 9: Wait one day, verify the cron fires

- [ ] **Step 1: Mark a calendar reminder for ~07:00 UTC tomorrow**

  GitHub-scheduled triggers can be delayed several minutes during high load. Don't conclude the cron is broken until ~07:00 UTC.

- [ ] **Step 2: Inspect the scheduled run**

  Open https://github.com/lontok/weather-api-pipeline-test/actions and confirm a new run appeared between 06:00 and ~07:00 UTC, triggered by `schedule` (not `workflow_dispatch`).

- [ ] **Step 3: Verify today's daily commit**

  ```bash
  git pull origin main
  git log --oneline --author="github-actions" -5
  ```
  Expected: a `chore: daily weather data update` commit dated today.

- [ ] **Step 4: Done**

  The pipeline is live. `weather_data.csv` will refresh daily without intervention.

  Future maintenance:
  - If GitHub auto-disables the schedule after a long failure streak (60+ days of consecutive failures), re-enable it from the Actions tab.
  - To change the schedule, edit the `cron:` line and push.
  - If the WeatherAPI key is ever leaked again, repeat Task 1 + Task 6.
