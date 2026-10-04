# Override with e.g. `make setup PYTHON=python3.13` if python3.12 is not installed.
PYTHON ?= python3.12
VENV := .venv
PY := $(VENV)/bin/python

.PHONY: setup data attacks train evaluate figures research demo attack scenarios benchmark test

setup:
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt
	cd web && npm install

data:
	$(PY) -m pipeline.download
	$(PY) -m pipeline.prepare

attacks:
	$(PY) -m pipeline.simulate_attacks

train:
	$(PY) -m pipeline.train

evaluate:
	$(PY) -m pipeline.evaluate

figures:
	$(PY) -m pipeline.figures

research: data attacks train evaluate figures

# Scoring API + LightRBA web platform (landing page, sign-in lab, dashboard). Ctrl+C stops both.
demo:
	@trap 'kill 0' INT TERM EXIT; \
	$(PY) -m api.server & \
	cd web && npm run dev

attack:
	$(PY) -m tools.attack_simulator

scenarios:
	$(PY) -m tools.demo_scenarios

benchmark:
	$(PY) -m tools.benchmark_latency

test:
	$(PY) -m pytest
