# AI Trading System (MVP Scaffolding)

A strictly typed, probabilistically driven, event-driven backtesting and paper-trading engine.
This MVP implements the V4 AI Architecture, focusing purely on quantitative risk management (EV math, fractional Kelly sizing, and uncertainty penalties). 

## Constraints
- **Live Trading**: Explicitly disabled. No broker hooks exist.
- **Environment**: Forced `paper` simulation via `config.py`.

## Setup & Installation

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Mac/Linux:
   source .venv/bin/activate
   ```

2. Install strictly pinned dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the System

To run the automated math and logic test suite (verifying EV, kill-switches, and Kelly sizing bounds):
```bash
python -m unittest tests/test_risk.py
```

To run the end-to-end dry simulation (Data -> Agent Proposal -> Risk Manager EV checks -> Paper Broker execution with artificial latency/slippage):
```bash
python scripts/main.py
```

## Alpaca Paper Trading Setup

This system uses [Alpaca](https://alpaca.markets/) for live paper-trading testing.

1. **Create an Alpaca Account**: Go to https://app.alpaca.markets/signup and sign up for a free account.
2. **Access Paper Dashboard**: Upon logging in, look at the top-right corner or sidebar. Ensure the toggle is switched to **Paper Trading** (the UI usually has a yellow "Paper" or "Simulated" badge).
3. **Generate Keys**: On the Paper Dashboard home page, click **"View Your API Keys"** in the right column, then click **"Generate New API Key"**.
4. **Copy to .env**: Copy your `.env.example` file to `.env` in the project root:
   ```bash
   cp .env.example .env
   ```
   Paste the Keys into the `.env` file. Proper Paper keys typically start with `PK`.
5. **Verify Connection**: Run the verification script which ensures auth is successful.
   ```bash
   python scripts/verify_alpaca.py
   ```
