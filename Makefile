# One entry point for the checks CI runs. `make check` before every push.
PYTHON := .venv/bin/python

.PHONY: venv test lint inventory diagram check screenshots social-preview

venv: ## Project environment: locked dependencies, pytest and ruff
	python3 -m venv .venv
	$(PYTHON) -m pip install -q -r requirements.lock.txt
	$(PYTHON) -m pip install -q pytest ruff

test: ## The pytest suite (every external service is mocked)
	$(PYTHON) -m pytest -q tests

lint: ## ruff
	$(PYTHON) -m ruff check .

inventory: ## Regenerate the command table in docs/modules.md
	python3 tools/gen_modules_doc.py

diagram: ## Redraw docs/assets/*.svg
	python3 tools/gen_diagram.py

check: lint test ## Everything CI checks, apart from Terraform
	python3 tools/gen_modules_doc.py --check
	python3 tools/gen_diagram.py --check
	sh tools/brand/check-icon.sh

screenshots: venv ## Retake docs/assets/screenshots/ against the demo mock (not CI)
	test -x .venv-screenshots/bin/python || ( \
		python3 -m venv .venv-screenshots && \
		.venv-screenshots/bin/pip install -q -r tools/screenshots/requirements.txt )
	.venv-screenshots/bin/python -m playwright install chromium
	.venv-screenshots/bin/python tools/screenshots/take_screenshots.py

social-preview: ## Redraw docs/assets/social-preview.png (needs Google Chrome and pillow)
	python3 tools/brand/brand_kit.py social --repo Jamf-Snipe-IT-Suite --name "Jamf-SnipeIT Suite" --tagline "Keep Jamf Pro and Snipe-IT in step with Azure AD and HiBob, on a schedule" --chip "Dry run first" --chip "AWS Fargate" --chip "Pending, never delete" --icon docs/assets/brand/icon.svg
