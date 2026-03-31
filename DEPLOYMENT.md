# Deploying the AI Trader — Free Cloud Options

## Option 1: GitHub Actions (Recommended — Zero Setup) ✅

This uses `.github/workflows/trade.yml` already in this repo.

### Steps:

1. **Push this repo to GitHub** (can be Private — Actions still runs free)
   ```bash
   git init
   git add .
   git commit -m "Initial trader setup"
   git remote add origin https://github.com/YOUR_USER/trader.git
   git push -u origin main
   ```

2. **Add your API keys as GitHub Secrets** (never in code!)
   - Go to your repo → `Settings` → `Secrets and variables` → `Actions`
   - Add:
     - `ALPACA_API_KEY` → your Alpaca paper key
     - `ALPACA_SECRET_KEY` → your Alpaca paper secret

3. **That's it.** The bot will run automatically every hour from:
   - `10:30 ART` (US market open) to `17:00 ART` (market close)
   - **Only on weekdays (Mon–Fri)**
   - You can also click **"Run workflow"** manually in the Actions tab

4. **View logs** → Actions tab → pick any run → download `trading-log` artifact

### Limitations:
- Each run is **stateless** (no persistent memory between cycles)
- GitHub cancels jobs running over 6 hours (won't be an issue)
- ~2000 minutes/month free (each run takes ~5-10 min → ~200 free runs/month)

---

## Option 2: Oracle Cloud Always Free (Best for 24/7) 🏆

Oracle gives you a **permanently free ARM VM** (4 CPU, 24GB RAM). It never expires.

### Steps:

1. Sign up at https://www.oracle.com/cloud/free/
2. Create a VM instance (Ampere A1, Ubuntu 22.04)
3. SSH into your VM and run:

```bash
# Install Python
sudo apt update && sudo apt install -y python3-pip git screen

# Clone your repo
git clone https://github.com/YOUR_USER/trader.git
cd trader/trading_system

# Install dependencies
pip3 install -r requirements.txt

# Create .env file with your keys
echo "ALPACA_API_KEY=your_key" >> .env
echo "ALPACA_SECRET_KEY=your_secret" >> .env
echo "ENVIRONMENT=paper" >> .env
echo "ALPACA_PAPER=true" >> .env

# Run the scheduler in the background (survives disconnects)
screen -S trader
python3 scripts/scheduler.py
# Press Ctrl+A then D to detach
```

4. To reconnect and check logs: `screen -r trader`

### Advantages:
- Runs 24/7, persistent memory, full logs
- Can also run a database for trade history
- Zero cost forever

---

## Option 3: PythonAnywhere (Simplest 1-Click)

1. Sign up at https://www.pythonanywhere.com (free)
2. Upload your code via the Files tab
3. Go to **Tasks** → Add scheduled task:
   ```
   /home/YOU/trader/trading_system/scripts/paper_runner.py
   ```
4. Set schedule: **Hourly** between 14:00–20:00 UTC

### Limitation: Only 1 free scheduled task.

---

## Summary Table

| Platform | Cost | Persistent | Setup Time | Best For |
|---|---|---|---|---|
| **GitHub Actions** | Free (2000 min/mo) | ❌ Stateless | ~5 min | Quick start |
| **Oracle Cloud** | Free forever | ✅ Yes | ~20 min | Production |
| **PythonAnywhere** | Free (limits) | ✅ Yes | ~10 min | Beginners |
| **Railway** | 500 hr/mo free | ✅ Yes | ~10 min | Modern UI |
