# Stock Trading Simulator

A comprehensive stock trading simulation platform with advanced features including equity curve analysis, limit orders, stop-loss/take-profit orders, and real-time performance metrics.

## Features

### Core Trading Features
- **Real-time Stock Data**: Support for both real market data (via akshare) and mock data generation
- **Buy/Sell Operations**: Execute trades with configurable transaction costs (fees, slippage)
- **Portfolio Management**: Track holdings, costs, and profit/loss in real-time
- **Trade History**: Complete record of all transactions with detailed information

### Advanced Order Types
- **Limit Orders**: Place buy/sell orders at specific price levels
- **Stop-Loss Orders**: Automatically sell when price drops below threshold
- **Take-Profit Orders**: Automatically sell when price reaches target profit
- **Pending Orders Management**: View and cancel pending orders

### Performance Analytics
- **Equity Curve**: Visual representation of portfolio value over time
- **Performance Metrics**:
  - Total Return & CAGR (Compound Annual Growth Rate)
  - Sharpe Ratio (risk-adjusted returns)
  - Maximum Drawdown
  - Win Rate & Profit Factor
- **Real-time Updates**: Metrics update automatically as trades are executed

### Risk Management
- **Auto Trading Rules**:
  - Stop-loss protection (automatic sell on loss threshold)
  - Scale in/out (gradual position adjustment)
- **Configurable Trading Costs**: Customize fee rates, minimum fees, and slippage
- **Portfolio Diversification**: Manage multiple stocks simultaneously

### Data & Visualization
- **K-line Charts**: 60-day candlestick charts with volume indicators
- **Historical Data**: Synthetic OHLC data generation for offline use
- **News Events**: Simulate market events (good/bad news) affecting stock prices
- **Date Navigation**: Backtest by navigating through historical dates

### User Interface
- **Modern UI**: Clean, intuitive interface with organized panels
- **Stock Universe Management**: Customize the list of tradable stocks
- **Calendar Integration**: Easy date selection for historical trading
- **Responsive Layout**: Efficient use of screen space with organized panels

## Installation

### Prerequisites
- Python 3.7 or higher
- tkinter (usually included with Python)

### Dependencies

Install required packages:

```bash
pip install -r requirements.txt
```

### Optional Dependencies

For real market data (optional):
```bash
pip install akshare
```

If `akshare` is not available, the simulator will automatically use mock data mode.

## Usage

### Basic Usage

1. Run the simulator:
```bash
python mock.py
```

2. On first launch, you'll be prompted to set your initial capital.

3. Select a date using the calendar (defaults to today).

4. Choose a stock from the list.

5. Enter the number of shares and click "Buy" or "Sell".

### Placing Orders

1. Select a stock from the list.
2. In the "Orders" panel:
   - Choose **Side**: Buy or Sell
   - Choose **Type**: Limit, Stop Loss, or Take Profit
   - Enter **Price/Trigger**: Target price for limit orders, trigger price for stop/take-profit
   - Enter **Shares**: Number of shares
   - Click **Place Order**

3. Orders will execute automatically when conditions are met (price reaches limit/trigger).

### Managing Risk

Access **Trading Settings** to configure:
- Fee rate (as fraction of trade value)
- Minimum fee per trade
- Slippage per share
- Stop-loss threshold (%)
- Scale in/out thresholds and fractions

### Performance Tracking

View your performance metrics in the left panel:
- **Total Return**: Overall portfolio return percentage
- **CAGR**: Annualized return rate
- **Sharpe Ratio**: Risk-adjusted performance
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Ratio of gross profit to gross loss

The equity curve chart shows your portfolio value over time.

## File Structure

```
TRADING/
├── mock.py                 # Main application file
├── stock_data.json          # Cached stock price data (auto-generated)
├── trade_data.json          # Trade records and account data (auto-generated)
├── stock_list.json          # Custom stock universe (optional)
└── stock_events.json        # Market event definitions (optional)
```

## Configuration

### Mock Data Mode

By default, the simulator uses mock data if `akshare` is unavailable. To force mock mode:

```bash
export STOCK_SIM_USE_MOCK=1
python mock.py
```

### Custom Stock Universe

Create `stock_list.json` in the same directory:

```json
{
  "AAPL": "Apple Inc.",
  "MSFT": "Microsoft Corporation",
  "GOOGL": "Google LLC"
}
```

## Features in Detail

### Equity Curve Analysis
The equity curve tracks your portfolio value over time, allowing you to:
- Visualize performance trends
- Identify periods of drawdown
- Assess strategy effectiveness

### Order Execution Logic
- **Limit Orders**: Execute when market price reaches or exceeds your limit price
- **Stop-Loss**: Triggers when price falls to or below trigger price
- **Take-Profit**: Triggers when price rises to or above trigger price

Orders are checked automatically when:
- Stock data is loaded
- Date changes
- Manual refresh occurs

### Auto Trading Rules
Configure automatic trading based on:
- **Stop-Loss**: Sell entire position if loss exceeds threshold
- **Scale Out**: Sell portion of position when profit reaches threshold
- **Scale In**: Buy more shares when loss reaches threshold (but before stop-loss)

## Troubleshooting

### Matplotlib Not Available
If charts don't display, install matplotlib:
```bash
pip install matplotlib
```

### No Stock Data
- Check internet connection if using real data
- Mock data mode will work offline
- Verify stock codes are valid (for real data mode)

### Orders Not Executing
- Ensure current stock price has reached trigger/limit price
- Check that you have sufficient cash (for buy orders) or shares (for sell orders)
- Verify order status in the orders table

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Acknowledgments

- Uses [akshare](https://github.com/akfamily/akshare) for real market data (optional)
- Built with Python, tkinter, and matplotlib

## Future Enhancements

Potential features for future versions:
- Technical indicators overlay (MA, MACD, RSI) on K-line charts
- Trade record export/import (CSV/JSON)
- Multiple account support
- Dark/light theme toggle
- Extended order types (trailing stops, OCO orders)

