PYTHON_BIN ?= python3

.PHONY: bootstrap check syntax

bootstrap:
	PYTHON_BIN="$(PYTHON_BIN)" bash scripts/bootstrap-controller.sh

check:
	.venv/bin/python scripts/verify-controller.py

syntax:
	.venv/bin/ansible-playbook --syntax-check playbook.yml
