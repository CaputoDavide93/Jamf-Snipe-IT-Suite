# FAQ

## What is Jamf-SnipeIT Suite?

It is a Python tool, run on a schedule, that keeps Jamf Pro, Snipe-IT, Azure AD and HiBob consistent with each other: new starters get Snipe-IT users, Macs are checked out to the right person, leavers' assets go to *Pending*, and returning staff are restored. It is MIT licensed and deploys to AWS Fargate with Terraform or runs locally and in Docker.

## Who is it for?

IT teams that run Jamf Pro for Macs and Snipe-IT as the asset register, and use Azure AD for identity and HiBob for HR. If you use only some of those systems, the modules that need the others can be switched off with `modules.<name>.enabled`.

## Does it delete anything?

It does not delete leavers or their assets: a leaver's name is tagged `[Disabled]` and their assets move to *Pending*. `cleanup` is the exception that merges duplicate users and removes junk accounts, and it starts as a dry run until you switch that off.

## How do I preview what it will change?

Add `--dry-run` (or `-n`) to any command that changes data, for example `python src/main.py leavers --dry-run`. It prints what it would change and writes nothing.

## Does it write to HiBob or Azure AD?

No. Azure AD and HiBob are read-only sources. Jamf Pro and Snipe-IT are the only systems it writes to, and Slack receives reports.

## How does it decide a returning employee is back?

All four signals must agree: the Azure AD account is enabled, the person is in neither the leavers nor the disabled group, no leave date has passed, and HiBob lists them as active. Anything less goes to Slack for a person to decide. See [how it works](how-it-works.md#rehires-need-four-signals).

## Is the AI service required?

No. It is optional and used only to resolve ambiguous machine-to-person matches and for the weekly `ai-audit`. Set `AI_API_KEY` to enable it. Audit payloads are tokenised by default, so identifiers stay out of the prompt unless you set `modules.ai_audit.allow_external_pii`.

## Can two jobs run at the same time?

No. Every scheduled job takes a lock in SSM first. If the lock is held, the later job is skipped instead of interleaving with the first. If SSM is unreachable the job refuses to start.

## Which Jamf Pro and Snipe-IT versions work?

Unknown. No versions are recorded, and the tests and screenshots use mocks that follow the documented response shapes. If you run it against a specific version, please [say so in an issue](https://github.com/CaputoDavide93/Jamf-SnipeIT-Suite/issues).

## Can I run it without AWS?

Yes. `python src/main.py` runs every module from a terminal, and `docker compose up` runs the scheduler. For a local run without AWS set `MUTEX_DISABLED=true` so the lock does not look for SSM.

## How do I add a person who needs SAML login to Snipe-IT?

Set their Snipe-IT `Username` to their full email address and add that address to `preserved_usernames` in `config/user_overrides.json`, or `username-standardize` will shorten it again on its next run. The steps are in [operations.md](operations.md).

## How do I wake Macs that stopped checking in?

Use the manual-only `wakeup` command, which sends redeploy commands to a Jamf smart group: `python src/main.py wakeup --group <id>` (or `--serial`, or `--file`). Add `--dry-run` first.
