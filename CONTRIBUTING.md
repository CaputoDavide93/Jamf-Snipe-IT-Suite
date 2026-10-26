# Contributing

Issues and pull requests are welcome. Most of what this suite does needs Jamf Pro, Snipe-IT, Azure AD and HiBob tenants, so the tests mock every external service and a report from a real environment is as useful as a fix.

## Report a bug or an environment

Open an issue with:

- What you ran, with tenant URLs, serial numbers and user names replaced by placeholders.
- What you expected and what happened, including the relevant log lines.
- Python version, operating system, and whether you ran it from a terminal, Docker or Fargate.

Remove tokens, passwords, tenant URLs, serial numbers and user names before you paste anything. Never attach `config/config.yaml`. To report a vulnerability, follow [SECURITY.md](SECURITY.md) instead of opening an issue.

## Send a change

```bash
git clone https://github.com/<your-fork>/Jamf-Snipe-IT-Suite.git && cd Jamf-Snipe-IT-Suite
make venv     # .venv from requirements.lock.txt, plus pytest and ruff
make check    # ruff, pytest, the generated command table, diagrams, icon
```

1. Branch from `main`.
2. Make the change and add a test where it fits. Every command that writes must keep its `--dry-run`.
3. Run `make check`. CI runs the same checks plus `terraform fmt` and `terraform validate`.
4. Open a pull request with a conventional title such as `fix: ...` or `docs: ...`.

`docs/modules.md` has a command table generated from `src/main.py`; run `make inventory` after changing a command. Diagrams come from `tools/gen_diagram.py` (`make diagram`). If you change what the CLI prints, retake the screenshots with `make screenshots`.

## Demo data only

The repository is public. Use `example.com` hosts, `192.0.2.x` addresses and made-up serials such as `DEMO0000101` in code, tests and docs. Never commit credentials, real tenant URLs or real names.
