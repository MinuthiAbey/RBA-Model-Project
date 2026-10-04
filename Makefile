# Override with e.g. `make setup PYTHON=python3.13` if python3.12 is not installed.
PYTHON ?= python3.12
VENV := .venv
PY := $(VENV)/bin/python

.PHONY: setup data attacks train evaluate figures research demo attack scenarios benchmark test

setup:
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt
	cd demo && npm install

data:
	$(PY) research/01_download.py
	$(PY) research/02_prepare.py

attacks:
	$(PY) research/03_inject_attacks.py

train:
	$(PY) research/04_train.py

evaluate:
	$(PY) research/05_evaluate.py

figures:
	$(PY) research/06_figures.py

research: data attacks train evaluate figures

# Risk engine service + DemoShop web app (shop, sign-in and /dashboard). Ctrl+C stops both.
demo:
	@trap 'kill 0' INT TERM EXIT; \
	$(PY) -m service.server & \
	cd demo && npm run dev

attack:
	$(PY) -m attack.stuffing

scenarios:
	$(PY) scripts/demo_scenarios.py

benchmark:
	$(PY) scripts/benchmark_latency.py

test:
	$(PY) -m pytest
