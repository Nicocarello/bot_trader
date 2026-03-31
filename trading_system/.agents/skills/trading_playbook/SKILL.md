---
name: trading_playbook
description: Structured rules for disciplined short-term professional trading.
---

# Trading Principles
1. **Capital Preservation First**: No single trade should ever wipe out a significant portion of the account.
2. **Context is King**: Technical signals must align with market regime and news context.
3. **Patience Over Frequency**: It is better to miss a good trade than to enter a bad one.

# Entry/Exit Rules
1. **Momentum Entry**: Price must be above 20 SMA AND Z-Score must be > 1.0 (indicating strength).
2. **Mean Reversion Entry**: Price must be outside Bollinger Bands AND Z-Score must be extreme (< -2.0 for longs).
3. **Volatility Exit**: Exit immediately if volatility (ATR or BB width) spikes beyond the 90th percentile of the day.
4. **Profit Target/Stop Loss**: Minimum R:R (Risk/Reward) of 1:2. Static Stop Loss at 2% from entry.

# No-Trade Conditions
1. **Conflict**: If Momentum says BUY and Mean Reversion says SELL, NO TRADE.
2. **Low Volatility**: If Bollinger Band width is in the bottom 10th percentile (the "Squeeze"), do not enter simple momentum trades.
3. **News Uncertainty**: If RAG Confidence is < 0.3, the trade must have a consensus score > 0.8 to proceed.

# Risk Management Rules
1. **Max Position Size**: No single position can exceed 5% of total account equity.
2. **Total Exposure**: Total open positions cannot exceed 25% of total account equity (maintaining 75% cash buffer).
3. **Daily Loss Limit**: Stop trading if daily realized/unrealized loss exceeds 2% of equity.

# Coordination Discipline
1. **Override**: The Coordinator must reject any trade that violates the 5% position size rule or 25% total exposure rule regardless of signal strength.
2. **Regime Lockdown**: In `bear_volatile` or `ranging_choppy` regimes, eliminate all "Buy" signals unless consensus score is > 0.9.
