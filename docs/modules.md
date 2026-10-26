# Modules

Every module is one command: `python src/main.py <command>`. Every command that changes data accepts `--dry-run` (or `-n`) and prints what it would change instead.

## Lifecycle

| Module | What it does |
|--------|--------------|
| `azure-starters` | Creates Snipe-IT users for every member of the starters Azure AD group. Skips former employees (leave date passed) and aborts if the Snipe-IT fetch looks broken. Each user gets a unique random password. |
| `user-enrichment` | Copies Azure AD job titles and departments onto Snipe-IT users and keeps an append-only **Contractor** marker, so contractors stay identifiable. |
| `rehire-detection` | Reverses the leaver flow for returning employees. See [how it works](how-it-works.md#rehires-need-four-signals). Runs before every other lifecycle and sync module. |
| `leavers` | Tags departed users `[Disabled]` and flips their assets to *Pending*. Uses live group membership and leave dates, and re-checks each asset before changing it. |

## Sync

| Module | What it does |
|--------|--------------|
| `user-match` | Matches the local accounts on Jamf machines to Snipe-IT users (override, exact, email, normalised, fuzzy, then the optional AI step) and checks each asset out to the right person. |
| `snipe-to-jamf` | Writes the Snipe-IT asset ID into a Jamf extension attribute so the two records link to each other. |
| `model-sync` | Makes sure every hardware model that Jamf reports exists in Snipe-IT, then sets the right model on each asset. `--check-only` lists missing models and changes nothing. |
| `correction` | Repairs wrong asset assignments, using the machine's local account as the ground truth. |
| `peripherals-sync` | Reads HiBob equipment entitlements (read-only) and mirrors them as Snipe-IT accessory checkouts. |

## Maintenance

| Module | What it does |
|--------|--------------|
| `cleanup` | Merges duplicate users and removes junk accounts. Defaults to dry run until you switch it off. |
| `reconciliation` | Compares inventory across the systems and reports drift. |
| `username-standardize` | Normalises Snipe-IT usernames to `first.last` (the email prefix), honouring configured exceptions. |
| `ai-audit` | Weekly cross-platform audit of suspicious assignments. Needs the optional AI key and is skipped without it. |
| `health-check` | Scans for stuck states (assets pending too long, disabled users who still hold assets, orphan checkouts) and alerts Slack. |
| `wakeup` | Manual only. Sends redeploy commands to a Jamf smart group before a big sync. |

## One-off script

`src/scripts/import_shipment_history.py` bulk-imports a supplier shipment CSV into Snipe-IT accessories. It normalises messy device descriptions to canonical accessory names, skips laptops (they arrive through `user-match`), matches recipients to Snipe-IT users (exact, known correction, fuzzy), creates missing accessories and checks them out in rate-limited batches. It is a dry run by default. Run it from `src/`:

```bash
python -m scripts.import_shipment_history <csv> --dry-run     # preview
python -m scripts.import_shipment_history <csv> --execute     # apply
python -m scripts.import_shipment_history <csv> --analyze-only  # inspect the CSV offline
```

## Command inventory

The table below is generated from `src/main.py` and `src/docker_scheduler.py` by `tools/gen_modules_doc.py`. CI fails if it is stale.

<!-- AUTOGEN:modules -->
*22 CLI commands, generated from `src/main.py` by `tools/gen_modules_doc.py` — do not edit by hand.*

| Command | What it does | Scheduler default (cron) |
|---------|--------------|---------------------------|
| `leavers` | Mark assets of disabled Azure AD users as pending | `0 9 * * 1` |
| `rehire-detection` | Restore [Disabled] Snipe-IT users whose Azure AD account is active again | `35 18 * * 2` |
| `snipe-to-jamf` | Sync user information from Snipe-IT to Jamf Pro | `0 6 * * *` |
| `user-match` | Match Jamf computers to Snipe-IT users and provision assets | `0 9 * * 2` |
| `model-sync` | Sync hardware models between Jamf Pro and Snipe-IT | `0 2 * * 0` |
| `wakeup` | Send MDM redeploy commands to devices | — |
| `all` | Run all modules in sequence (except WakeUp) | — |
| `reconcile` | Reconcile inventory between Jamf Pro and Snipe-IT | — |
| `azure-starters` | Sync Azure AD starters group members to Snipe-IT users | `0 6 * * 1` |
| `correction` | Detect and fix wrong asset assignments from previous runs | `0 8 * * *` |
| `health-check` | Scan for stuck/inconsistent states and report to Slack | `0 9 * * *` |
| `pending-reconciliation` | Restore Pending assets whose owner is active again (Azure AD confirmed) | — |
| `jamf-location-cleanup` | Clear Jamf location/user for In-Stock and Retired machines | — |
| `ai-audit` | AI-powered cross-platform audit (security, compliance, anomalies) | `0 4 * * 0` |
| `cleanup` | Merge duplicate users and remove junk accounts | `0 3 * * 0` |
| `user-enrichment` | Push Azure AD fields (job title, dept) to Snipe-IT | `30 6 * * 1` |
| `peripherals-sync` | Sync HiBob equipment to Snipe-IT accessories | `0 8 * * 1` |
| `username-standardize` | Strip @domain from Snipe-IT usernames | — |
| `run-group` | Run a comma-separated list of modules sequentially under mutex | — |
| `health-server` | Start health check HTTP server | — |
| `reconciliation` | Reachable via `run-group` only | — |
| `monthly-digest` | Reachable via `run-group` only | — |
<!-- /AUTOGEN:modules -->

The **Scheduler default** column is the built-in cron each job falls back to in the container scheduler (`src/docker_scheduler.py`). `jobs:` entries in `config.yaml` override it, and in production the EventBridge rules in `terraform/` set the timing.

## Weekly schedule

The local scheduler runs in `Europe/London`. Each slot is 30 minutes or more apart, so a slow module cannot overlap the next one, and the run mutex skips a collision if one happens anyway.

| Day | Time | Job | Purpose |
|-----|------|-----|---------|
| Mon | 17:00 | `azure_starters` | Provision the week's new starters |
| Mon | 18:00 | `user_enrichment` | Titles, departments, contractor markers |
| Mon | 18:10 | `peripherals_sync` | HiBob equipment to accessories |
| Mon, Thu | 19:00 | `health_check` | Drift and stuck-state scan |
| Tue | 17:30 | `rehire_detection` | Restore returners before the sync chain |
| Tue | 18:00 | `correction` | Fix wrong assignments |
| Tue | 18:30 | `user_match` | Match machines and check them out |
| Tue | 19:00 | `snipe_to_jamf` | Push asset IDs to Jamf |
| Tue | 19:30 | `leavers` | Process departures last |
| Sun | 22:00 to 23:00 | housekeeping | `model_sync`, `cleanup`, `username_standardize`, `ai_audit`, `reconciliation` |
