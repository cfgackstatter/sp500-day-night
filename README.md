# Overnight Return

Compare **overnight** (close → open), **intraday** (open → close), and **buy & hold** cumulative returns for any Yahoo Finance ticker. Built with Dash; deployable on AWS Elastic Beanstalk.

**Live demo:** [sp500-day-night-env](http://sp500-day-night-env.eba-muader23.us-east-1.elasticbeanstalk.com/)

## Features

- Cumulative return chart for overnight, intraday, and buy & hold
- Period presets (YTD / 1Y / 3Y / 5Y / 10Y) plus custom date range
- Total return and annualized Sharpe (mean / vol × √252) per strategy
- Maintain tickers in `tickers.txt` or via Add / Remove / Refresh in the UI
- Data loaded once at startup; Refresh re-downloads from Yahoo Finance

## Requirements

- Python 3.10+

## Quick start

```bash
git clone https://github.com/cfgackstatter/overnight-return.git
cd overnight-return
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 application.py
```

Open [http://localhost:8080](http://localhost:8080).

## Tickers

Default list is in `tickers.txt` (one symbol per line; `#` starts a comment):

```text
SPY
QQQ
DIA
IWM
```

Edit the file or use the app controls. Changes made in the UI are written back to `tickers.txt`.

## Strategies

| Strategy   | Window              | Daily return                         |
|------------|---------------------|--------------------------------------|
| Overnight  | Close → next open   | `(Open_t − Close_{t−1}) / Close_{t−1}` |
| Intraday   | Open → close        | `(Close_t − Open_t) / Open_t`        |
| Buy & hold | Close → close       | `(Close_t − Close_{t−1}) / Close_{t−1}` |

Prices come from Yahoo Finance daily OHLC via [`yfinance`](https://github.com/ranaroussi/yfinance) (adjusted). History is requested from 1990 onward (subject to ticker availability).

## Project layout

```text
overnight-return/
├── application.py      # Dash entry point (WSGI: application)
├── layout.py           # UI and callbacks
├── data_utils.py       # Download, strategies, metrics
├── tickers.txt         # User-maintained ticker list
├── assets/style.css
├── requirements.txt
└── .elasticbeanstalk/  # EB config (optional)
```

## Deploy (Elastic Beanstalk)

Requires the [EB CLI](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3.html) and AWS credentials.

```bash
eb init
eb create sp500-day-night-env   # or: eb deploy
eb open
```

`application.py` exposes `application` for Gunicorn/EB.
