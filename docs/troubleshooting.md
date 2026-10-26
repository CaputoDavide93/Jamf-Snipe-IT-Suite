# Troubleshooting

Find the symptom, read the cause. Each symptom below matches a message the code logs. For run-by-run investigation on AWS (logs, a single machine, a leaver) see [operations.md](operations.md).

## The container exits at once: "No configuration found"

The entrypoint found neither `/app/config/config.yaml` nor both `JAMF_BASE_URL` and `SNIPEIT_BASE_URL` in the environment. Create `config/config.yaml` from the example, or set both variables. With `docker compose`, `./config` is mounted read-only, so the file has to exist on the host.

## "Missing Python dependencies, rebuild the Docker image"

The image is missing a required package. Rebuild it from `requirements.lock.txt` (`docker compose build`). Do not install packages inside a running container; its root filesystem is read-only.

## A job logs "Mutex held by '...' until ..."

Another run holds the lock, so this one backs off. That is the mutex working. If the holder's time is long past, the next run reclaims the lock by itself ("Mutex held by ... expired ... reclaiming"). If the message says the value is malformed or the expiry cannot be parsed, the run refuses to reclaim; inspect the lock parameter in SSM, as described in [operations.md](operations.md).

## A job logs "Mutex backend unavailable" or "acquisition refused"

The run could not reach SSM, or the task role lacks permission, and the mutex fails closed: the job does not start. Check network access to SSM and the task role's `ssm:GetParameter`, `ssm:PutParameter` and `ssm:DeleteParameter` rights on the `run-lock` parameter. For a local run with no AWS, set `MUTEX_DISABLED=true`. Never set it in ECS.

## "Snipe-IT returned 0 users, aborting"

`azure-starters` and `rehire-detection` stop when the Snipe-IT user list comes back empty, because a failed fetch would otherwise look like "nobody exists" and create duplicates. Check the Snipe-IT URL, the API token and any IP allow-list, then run again.

## "Could not load Azure AD data, aborting"

`rehire-detection` could not read Azure AD, so it did nothing. Check the tenant ID, client ID and secret.

## "AI Audit skipped: no LLM configured (set AI_API_KEY to enable)"

The AI audit is optional and needs an API key for an external AI service in `AI_API_KEY`. Without it `ai-audit` skips itself, and `user-match` falls back to the scoring steps alone. Nothing else is affected.

## A command changed nothing

Check whether the module is in dry-run. `rehire-detection` and `cleanup` default to it, and `modules.<name>.dry_run: true` or `MODULE_<NAME>_DRY_RUN=true` forces it for any module. A forced dry run cannot be turned back to live by a command-line flag. Look for `[DRY-RUN]` in the output.

## A Mac was not matched to anyone

The log and the Slack "Unmatched Devices" report name the local account it could not match. Typical causes: a new hire not yet in Azure AD, a shared lab Mac with only admin accounts, or a local username unlike the Snipe-IT one. Add a manual override in `config/user_overrides.json` (see [operations.md](operations.md)) and rebuild the image, or add the account to `matching.skip_usernames` if it should be ignored.

## A change to the Fargate settings had no effect

Fargate never reads `config.yaml`. Register a new task-definition revision with the new environment, then point all five EventBridge rule targets at it.

## The task never started and there is no log

The `FailedInvocations` alarm for the schedule fires when `RunTask` cannot launch. Check the subnets, the security group and the image tag, and that the image was built for `linux/amd64`.

## Still stuck

Open an [issue](https://github.com/CaputoDavide93/Jamf-SnipeIT-Suite/issues) with the command, the log lines around the error and the module's `--dry-run` output. Replace real names, serial numbers, hostnames and IP addresses with placeholders (use `192.0.2.x` for addresses) and never paste tokens.
