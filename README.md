# S&P 500 Overnight vs Intraday Returns Analysis

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Dash](https://img.shields.io/badge/Dash-2.18+-green.svg)](https://dash.plotly.com/)
[![AWS](https://img.shields.io/badge/AWS-Elastic%20Beanstalk-orange.svg)](https://aws.amazon.com/elasticbeanstalk/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An interactive web application that analyzes whether stock market returns occur primarily during overnight periods (market close to next day open) or during regular trading hours (open to close). Built with Dash and deployed on AWS Elastic Beanstalk.

## 🌟 Live Demo

[**View Live Application →**](http://sp500-day-night-env.eba-muader23.us-east-1.elasticbeanstalk.com/)

## 📊 Features

- **Real-time Data**: Fetches historical data from Yahoo Finance for major indices
- **Interactive Analysis**: Compare overnight vs intraday vs buy-and-hold strategies
- **Multiple Indices**: Support for SPY, QQQ, DIA, and IWM
- **Date Range Selection**: Analyze any time period with responsive date picker
- **Performance Metrics**: Clear visualization of cumulative returns with detailed statistics
- **Professional UI**: Clean, monochrome design optimized for financial analysis
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- AWS CLI configured with appropriate credentials
- Git

### Local Development

#### Clone the repository

```console
git clone https://github.com/cfgackstatter/sp500-day-night.git
cd sp500-day-night
```

#### Create virtual environment

```console
python3 -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

#### Install dependencies

```console
pip install -r requirements.txt
```

#### Run the application

```console
python application.py
```

#### Visit http://localhost:8080

### Cloud Deployment (AWS Elastic Beanstalk)

#### Initialize EB application

```console
eb init
```

#### Create and deploy environment

```console
eb create sp500-day-night-env
```

#### Open deployed application

```console
eb open
```

## 📁 Project Structure

```sp500-day-night/
├── application.py # Main Dash app (AWS EB entry point)
├── layout.py # UI layout and callbacks
├── data_utils.py # Data fetching and calculations
├── assets/
│ └── style.css # Custom styling
├── requirements.txt # Python dependencies
├── .gitignore # Git ignore patterns
├── .ebignore # EB deployment exclusions
├── .elasticbeanstalk/ # EB configuration
│ └── config.yml
└── README.md # This file
```

## 🔬 Strategy Analysis

The application implements three distinct investment strategies:

### 1. Overnight Strategy
- **Definition**: Hold positions from market close (4:00 PM ET) to next day's market open (9:30 AM ET)
- **Calculation**: `(Open_t - Close_t-1) / Close_t-1`
- **Hypothesis**: Tests if returns accrue primarily when markets are closed

### 2. Intraday Strategy  
- **Definition**: Hold positions from market open to market close on the same day
- **Calculation**: `(Close_t - Open_t) / Open_t`
- **Hypothesis**: Tests if returns accrue during regular trading hours

### 3. Buy & Hold Strategy
- **Definition**: Continuously hold positions (baseline comparison)
- **Calculation**: `(Close_t - Close_t-1) / Close_t-1`
- **Purpose**: Traditional investment approach for comparison

## 📈 Data Sources

- **Provider**: Yahoo Finance via `yfinance` library
- **Frequency**: Daily OHLC (Open, High, Low, Close) data
- **History**: Up to 10 years of historical data
- **Updates**: Data refreshed on each application startup
- **Indices Supported**:
  - **SPY**: S&P 500 SPDR ETF
  - **QQQ**: NASDAQ-100 ETF  
  - **DIA**: Dow Jones Industrial Average ETF
  - **IWM**: Russell 2000 ETF

## 🛠️ Technology Stack

### Backend
- **[Dash](https://dash.plotly.com/)**: Web application framework
- **[Plotly](https://plotly.com/python/)**: Interactive charting library
- **[pandas](https://pandas.pydata.org/)**: Data manipulation and analysis
- **[yfinance](https://github.com/ranaroussi/yfinance)**: Financial data retrieval
- **[NumPy](https://numpy.org/)**: Numerical computing

### Frontend
- **HTML5/CSS3**: Responsive web interface
- **Custom CSS**: Professional monochrome styling
- **Interactive Components**: Dash core components for user interaction

### Deployment
- **[AWS Elastic Beanstalk](https://aws.amazon.com/elasticbeanstalk/)**: Cloud platform
- **[Gunicorn](https://gunicorn.org/)**: Python WSGI HTTP Server
- **GitHub**: Version control and collaboration

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.