# Design: Scheduled GitHub Actions for the Weather Pipeline

**Date:** 2026-04-27
**Status:** Approved
**Author:** Greg Lontok (with Claude Code)

## Goal

Run `weather.py` automatically once a day on GitHub Actions, commit the resulting `weather_data.csv` back to the `main` branch, and rely on GitHub's default email notifications when a run fails.

## Non-goals

- Hourly or more frequent collection
- Artifact uploads or external storage (the committed CSV is the record)
- Slack, Discord, or other notification integrations
- Retry logic inside the workflow
- Time-series accumulation (each run overwrites the CSV)
- Data validation or schema checks on the API response

## Architecture

```
GitHub Actions (cron, daily 06:00 UTC)
        │
        ▼
Job: collect-weather (ubuntu-latest)
  1. Checkout repo
  2. Set up Python 3.11
  3. pip install -r requirements.txt
  4. Run weather.py
       └── env: WEATHERAPI_KEY ← secrets.WEATHERAPI_KEY
  5. git add weather_data.csv
  6. git commit (skip if no diff)
  7. git push origin main
        │
        ├── success: silent ✅
        └── failure: GitHub auto-emails repo owner
```

`06:00 UTC` is roughly 11:00 PM Pacific the previous day. GitHub's scheduled triggers can be delayed by several minutes during high load, which is acceptable for a daily pipeline.

## Changes to existing code

### 1. Move the API key out of `weather.py`

Add `import os` to the imports at the top of the file (alongside `requests`, `time`, `pandas`).

Then replace line 5 of `weather.py`:

```python
api_key = "4ec5c9b8d3144679b6c155941261304"
```

with:

```python
api_key = os.environ["WEATHERAPI_KEY"]
```

The script will fail with a clear `KeyError` if the variable is missing. That is the right behavior, because a silent fallback would call the API with an empty key and produce confusing downstream errors.

**Rotate the leaked key.** The current key is in git history. Generate a new key at weatherapi.com, revoke the old one, and store only the new key as a GitHub secret. The old value in history then becomes harmless.

### 2. Add `requirements.txt`

```
requests
pandas
```

Versions are unpinned for now since this is a learning project. If a future release breaks the script, that is part of the learning. Pin later with `pip freeze > requirements.txt` if needed.

### 3. Create the `WEATHERAPI_KEY` GitHub secret

In the repository on github.com:

1. Settings → Secrets and variables → Actions → New repository secret
2. Name: `WEATHERAPI_KEY`
3. Value: the new (rotated) WeatherAPI key
4. Save

## New file: `.github/workflows/weather-pipeline.yml`

```yaml
name: Weather Pipeline

on:
  schedule:
    - cron: "0 6 * * *"     # 06:00 UTC daily
  workflow_dispatch:         # also allow manual runs from the Actions tab

permissions:
  contents: write            # needed so the job can push the CSV back

concurrency:
  group: weather-pipeline
  cancel-in-progress: false  # if a run is somehow still going, let it finish

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

### Design choices

- **`workflow_dispatch`** gives a "Run workflow" button on the Actions tab so the workflow can be triggered manually for testing without waiting on the cron.
- **`permissions: contents: write`** is required because the default `GITHUB_TOKEN` is read-only. Without it, the push step fails with HTTP 403.
- **`concurrency`** prevents two daily runs overlapping if one is delayed.
- **`cache: pip`** speeds up subsequent runs by caching `requests` and `pandas`.
- **No-op guard on the commit step** avoids creating empty commits if the CSV is byte-identical to the previous run.
- **Bot identity** uses GitHub's official `github-actions[bot]` noreply address so commits are attributed to the workflow rather than impersonating a user.

## Failure handling

- GitHub emails the repo owner on workflow failure (default behavior, no extra setup).
- After 60 days of consecutive failures, GitHub auto-disables the schedule. Re-enable from the Actions tab if it ever happens.
- No in-workflow retries. A single failed run is acceptable; the next day's run will try again.
- The existing `time.sleep(1)` between cities in `weather.py` already paces requests and stays.

## Testing plan

Three checkpoints, in order:

1. **Local sanity check.** After editing `weather.py`:
   ```
   export WEATHERAPI_KEY="<your new key>"
   python weather.py
   ```
   Confirms the env var change did not break anything.

2. **Manual workflow run.** Once the workflow file is committed and the secret is set, click "Run workflow" on the Actions tab. This validates:
   - The secret is wired up
   - Python install and dependency install work
   - The push back to `main` succeeds (proves `contents: write` is set)
   - A new commit `chore: daily weather data update` appears on `main`

3. **Wait one day.** Confirm the cron actually fires at ~06:00 UTC. Some delay is normal.

If step 2 fails, the Actions log identifies the failing step. The most likely failure mode is the push step if `permissions: contents: write` was omitted, which is why step 2 happens before relying on the schedule.

## Open questions

None.

## Future enhancements (not in scope)

- Append mode for time-series accumulation
- Artifact upload for per-day historical snapshots
- Data validation step before commit
- Slack or Discord notifications on failure
