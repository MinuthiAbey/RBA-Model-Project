# Lightweight Risk-Based Authentication for Small Web Applications

A risk engine that scores every sign-in from 0 to 100 and decides whether to allow it, ask for a one-time code or block it, with plain-English reasons. Four interchangeable scorers are compared on the same real-world login data, with a focus on users who have little or no sign-in history (cold start):

| Scorer | Kind |
|---|---|
| Fixed rules | Points per warning sign (new country, new device, unusual hour, ...) |
| Freeman et al. (2016) | Statistical model of how unusual the sign-in is for this user |
| Isolation Forest | Unsupervised anomaly detection |
| Random Forest | Supervised, trained on sign-ins from known attacker IPs |

LightRBA, a small web application, shows the engine working live. It is a demonstration only: no research result comes from it.

## Results

From the final run of the notebook, on 13,102 test-period sign-ins from attacker IPs that had the correct password, with every model allowed to challenge 5% of legitimate sign-ins (thresholds set on validation data):

| Scorer | ROC AUC | Attempts flagged | On accounts with no history |
|---|---|---|---|
| Random Forest | 0.939 | 63.6% | 73.1% |
| Fixed rules | 0.790 | 18.3% | 27.4% |
| Freeman | 0.753 | 18.3% | 27.4% |
| Isolation Forest | 0.429 | 6.9% | 2.0% |

"Flagged" means asked for a one-time code or blocked. Rules and Freeman give every first-time user the same top score, so their whole budget goes to new accounts. Every scorer scores a sign-in in under 9 ms on a laptop (95th percentile). The results hold for this dataset and its attacker-IP labels.

## Folder layout

```
api/        Python scoring service the web app calls (SQLite accounts and history)
engine/     the risk engine: history, features, the four scorers, calibration, decisions, reasons
models/     trained models and thresholds (the Random Forest is rebuilt by make train)
notebook/   stand-alone notebook: raw CSV to every result, step by step (runs on Google Colab)
pipeline/   download, prepare, simulated attacks, train, evaluate, figures
tests/      91 unit tests
tools/      attack simulator (localhost only), demo scenarios, latency benchmark
web/        LightRBA web app (Next.js)
```

The dataset and generated results live next to this folder, in `../data` and `../results` (set in `config.yaml`).

## Requirements

- Python 3.12, Node.js 20 or newer, and `make`
- About 12 GB of free disk (the dataset CSV is 9 GB) and 8 GB of RAM

## Running it

```
make setup       # virtual environment with the pinned versions (requirements.lock), and the web packages
make data        # downloads the dataset from Zenodo, checks its MD5, converts and splits it
make research    # simulated attacks, training, evaluation and figures
make test        # the unit tests
make demo        # scoring service + web app at http://127.0.0.1:3000 (Ctrl+C stops both)
```

With the demo running, in a second terminal:

```
make scenarios   # the four presentation scenarios
make attack      # credential-stuffing simulator (refuses anything but localhost)
make benchmark   # scoring time per model, plus a full sign-in request
```

The demo seeds ten accounts; their password is in `api/seed.py`. To reset it, stop the demo, delete `../data/lightrba.db` and start it again.

## Notebook

`notebook/rba_models_colab.ipynb` rebuilds every reported table and figure from the raw CSV, with no other project code. Set `CSV_PATH` in the first cell and run the cells in order; it pins scikit-learn 1.9.1 so the forests come out the same on any machine. It takes about three minutes on a laptop and peaks at about 4 GB of memory.

## Dataset

Login Data Set for Risk-Based Authentication (CC BY 4.0), synthesised from a real single sign-on service:

- Wiefling, S., Jørgensen, P. R., Thunem, S., & Lo Iacono, L. (2022). *Login data set for risk-based authentication* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.6782156
- Wiefling, S., Jørgensen, P. R., Thunem, S., & Lo Iacono, L. (2023). Pump up password security! Evaluating and enhancing risk-based authentication on a real-world large-scale online service. *ACM Transactions on Privacy and Security, 26*(1). https://doi.org/10.1145/3546069

The dataset is not included in this repository.
