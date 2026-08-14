PYTHON_BIN ?= python3

.PHONY: bootstrap check syntax test-static test-live

bootstrap:
	PYTHON_BIN="$(PYTHON_BIN)" bash scripts/bootstrap-controller.sh

check:
	.venv/bin/python scripts/verify-controller.py

syntax:
	.venv/bin/ansible-playbook --syntax-check playbook.yml

test-static:
	.venv/bin/python tests/run_acceptance.py static

test-live:
	.venv/bin/python tests/run_acceptance.py live --inventory inventory.yml --config config.yml
