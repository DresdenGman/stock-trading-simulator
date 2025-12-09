import tkinter as tk  # Import tkinter module and rename it as tk
import random  # Import random module for generating random numbers
from tkinter import messagebox  # Import messagebox from tkinter for displaying message boxes
from tkinter import simpledialog  # Import simpledialog for user input dialogs
import datetime  # Import datetime module for date manipulation
from tkcalendar import Calendar, DateEntry  # Import Calendar and DateEntry from tkcalendar
from tkinter import ttk  # Import ttk for Combobox
import threading
import time
import json
import os
try:
    import matplotlib
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except Exception:
    matplotlib = None
    FigureCanvasTkAgg = None
    Figure = None
    MATPLOTLIB_AVAILABLE = False
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except Exception:
    ak = None
    AKSHARE_AVAILABLE = False
import pandas as pd
import numpy as np


class StockDataManager:
    def __init__(self, data_file="stock_data.json", use_mock_data=None):
        # Get the directory of the current file
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_file = os.path.join(self.base_dir, data_file)
        self.events_file = os.path.join(self.base_dir, "stock_events.json")
        self.data = self._load_data()
        self.events = self._load_events()
        self.stock_list = self._get_default_stock_list()
        self.use_mock_data = self._determine_mock_mode(use_mock_data)
        
    def _load_data(self):
        """Load stored data"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_data(self):
        """Save data to file"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _load_events(self):
        """Load stock event data (good/bad news that affect mock returns)."""
        if os.path.exists(self.events_file):
            try:
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 期望结构：list[{"code":..., "start":"YYYY-MM-DD", "days":N, "impact_pct":+/-x}]
                    if isinstance(data, list):
                        return data
            except Exception as e:
                print(f"Failed to load stock_events.json: {e}")
        return []

    def _save_events(self):
        """Save event list to file."""
        try:
            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump(self.events, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save stock_events.json: {e}")
    
    def _determine_mock_mode(self, explicit_flag):
        """Determine whether to enable mock mode"""
        if explicit_flag is not None:
            if explicit_flag:
                return True
            if not AKSHARE_AVAILABLE:
                print("akshare unavailable, forcing mock data mode.")
                return True
            return False
        env_flag = os.environ.get("STOCK_SIM_USE_MOCK", "").strip().lower()
        if env_flag in {"1", "true", "yes", "on"}:
            return True
        return not AKSHARE_AVAILABLE
    
    def _get_default_stock_list(self):
        """Return stock list (load from file if available, otherwise use built-in defaults)"""
        # Allow user to customize stock universe via stock_list.json in the same directory.
        custom_path = os.path.join(self.base_dir, "stock_list.json")
        if os.path.exists(custom_path):
            try:
                with open(custom_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Expecting a dict: {"AAPL": "Apple", ...}
                if isinstance(data, dict) and data:
                    return data
            except Exception as e:
                print(f"Failed to load custom stock_list.json, using built-in list: {e}")

        # Built-in default list
        return {
            "AAPL": "Apple",
            "MSFT": "Microsoft",
            "GOOGL": "Google",
            "AMZN": "Amazon",
            "META": "Meta",
            "TSLA": "Tesla",
            "NVDA": "NVIDIA",
            "JPM": "JPMorgan Chase",
            "JNJ": "Johnson & Johnson",
            "V": "Visa",
            "WMT": "Walmart",
            "PG": "Procter & Gamble",
            "MA": "Mastercard",
            "HD": "Home Depot",
            "BAC": "Bank of America"
        }
    
    def get_stock_list(self):
        """Get stock list"""
        return self.stock_list
    
    def get_stock_data(self, code, date):
        """Get data for specified date and stock code"""
        date_str = date.strftime("%Y-%m-%d")
        
        # Check if data for this date already exists
        if date_str in self.data and code in self.data[date_str]:
            print(f"Getting {code} data for {date_str} from local cache")
            return self.data[date_str][code]
        
        if self.use_mock_data:
            stock_data = self._generate_mock_stock_data(code, date)
            self._cache_stock_data(date_str, code, stock_data)
            return stock_data
        
        print(f"Getting {code} data for {date_str} from network")
        # If no data exists, fetch from network
        try:
            # Get historical data
            hist_data = ak.stock_us_daily(symbol=code, adjust='qfq')
            
            if hist_data.empty:
                print(f"Stock {code} has no historical data")
                return None
                
            # Ensure data is sorted by date
            hist_data = hist_data.sort_values('date')
            
            # Get target date data
            target_price_data = hist_data[hist_data['date'] <= date_str]
            if target_price_data.empty:
                print(f"Stock {code} has no data for {date_str}")
                # Try to get the latest available data
                target_price_data = hist_data.iloc[-1]
            else:
                target_price_data = target_price_data.iloc[-1]
                
            target_price = target_price_data['close']
            
            # Get previous day's closing price
            previous_date = date - datetime.timedelta(days=1)
            previous_date_str = previous_date.strftime("%Y-%m-%d")
            previous_price_data = hist_data[hist_data['date'] <= previous_date_str]
            
            if previous_price_data.empty:
                print(f"Stock {code} has no data for {previous_date_str}")
                # If no previous day data, use target date data
                previous_price = target_price
            else:
                previous_price = previous_price_data.iloc[-1]['close']
            
            # Calculate price change percentage
            change_percent = ((target_price - previous_price) / previous_price) * 100
            
            # Build return data
            stock_data = {
                "price": target_price,
                "change_percent": change_percent
            }
            
            # Save to local
            self._cache_stock_data(date_str, code, stock_data)
            
            return stock_data
            
        except Exception as e:
            print(f"Failed to get stock {code} data: {str(e)}")
            return None

    def get_stock_history(self, code, end_date, window_days=60):
        """Get historical OHLC data for k-line chart.
        Returns a pandas DataFrame with columns: date, open, high, low, close.

        Note: 为了保证在本地离线环境、以及不同日期选择下都有平滑且可重复的效果，
        这里不再强依赖 akshare 的真实历史数据，而是统一基于当前选择的日期和股票代码
        生成一个“合成但合理”的 K 线序列。这样：
        - 切换不同股票 → 形态会变化；
        - 切换不同日期 → 窗口会随日期移动，而不是一直固定在同一段历史。
        """
        # 统一使用合成 OHLC 数据，围绕每日收盘价构造。
        dates = []
        opens = []
        highs = []
        lows = []
        closes = []
        for i in range(window_days, 0, -1):
            d = end_date - datetime.timedelta(days=i)
            data = self.get_stock_data(code, d)
            if data is None:
                continue
            close_price = float(data["price"])
            # Deterministic randomness based on code+date
            seed = f"{code}-{d.strftime('%Y-%m-%d')}-ohlc"
            rng = random.Random(seed)
            # Generate open/close with small variation
            spread = close_price * 0.02  # 2% intraday range baseline
            open_price = close_price + rng.uniform(-0.5, 0.5) * spread
            high_price = max(open_price, close_price) + rng.uniform(0.1, 0.6) * spread
            low_price = min(open_price, close_price) - rng.uniform(0.1, 0.6) * spread

            dates.append(d.strftime("%Y-%m-%d"))
            opens.append(round(open_price, 2))
            highs.append(round(high_price, 2))
            lows.append(round(low_price, 2))
            closes.append(round(close_price, 2))

        if not dates:
            return None

        # 生成与价格对应的合成成交量（与波动程度、价格水平弱相关，便于展示）
        volumes = []
        for i, cp in enumerate(closes):
            # 使用与 K 线相同的 deterministic 随机源，保证同一日期/股票下重复性
            d = datetime.datetime.strptime(dates[i], "%Y-%m-%d").date()
            seed = f"{code}-{d.strftime('%Y-%m-%d')}-vol"
            rng = random.Random(seed)
            base_vol = 1_000_000 + (abs(hash(code)) % 500_000)
            # 让高波动日的成交量略高
            intraday_range = highs[i] - lows[i]
            vol_scale = 1.0 + min(intraday_range / max(cp, 1.0), 0.5)
            volume = int(base_vol * vol_scale * rng.uniform(0.7, 1.3))
            volumes.append(volume)

        df = pd.DataFrame({
            "date": dates,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes
        })
        return df

    def _generate_mock_stock_data(self, code, date):
        """Generate deterministic mock stock data"""
        date_str = date.strftime("%Y-%m-%d")
        rng = random.Random(f"{code}-{date_str}")
        base_price = 50 + (abs(hash(code)) % 250)
        change_percent = round(rng.uniform(-4.5, 4.5), 2)

        # 应用事件脚本：在事件持续期间对日涨跌幅做偏移
        if self.events:
            for ev in self.events:
                if ev.get("code") != code:
                    continue
                try:
                    start = datetime.datetime.strptime(ev.get("start", ""), "%Y-%m-%d").date()
                except Exception:
                    continue
                days = int(ev.get("days", 0))
                if days <= 0:
                    continue
                end = start + datetime.timedelta(days=days - 1)
                if start <= date <= end:
                    impact = float(ev.get("impact_pct", 0.0))
                    change_percent += impact

        price = round(base_price * (1 + change_percent / 100), 2)
        price = max(price, 5.0)
        return {
            "price": price,
            "change_percent": change_percent
        }

    def _cache_stock_data(self, date_str, code, stock_data):
        """Cache stock data locally"""
        if date_str not in self.data:
            self.data[date_str] = {}
        self.data[date_str][code] = stock_data
        self._save_data()

    def add_event(self, code, start_date, days, impact_pct):
        """Add a good/bad news event for a stock.

        impact_pct: 正数表示在原有日涨跌幅基础上增加（利好），负数表示减少（利空）。
        """
        if days <= 0:
            return
        start_str = start_date.strftime("%Y-%m-%d")
        event = {
            "code": code,
            "start": start_str,
            "days": int(days),
            "impact_pct": float(impact_pct)
        }
        self.events.append(event)
        self._save_events()

        # 为了让事件立即生效，清除该股票在事件区间内的本地价格缓存
        try:
            for i in range(days):
                d = start_date + datetime.timedelta(days=i)
                d_str = d.strftime("%Y-%m-%d")
                if d_str in self.data and code in self.data[d_str]:
                    del self.data[d_str][code]
                    if not self.data[d_str]:
                        del self.data[d_str]
            self._save_data()
        except Exception as e:
            print(f"Failed to clear cached prices for event on {code}: {e}")

class TradeManager:
    def __init__(self, initial_cash=100000.0):
        # Get the directory of the current file
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_file = os.path.join(self.base_dir, "trade_data.json")
        self.trade_records = []
        self.pending_orders = []
        # Allow customizable starting cash; this may be overridden by saved data in load_data().
        self.initial_cash = float(initial_cash)
        self.cash = float(initial_cash)
        self.portfolio = {}

        # Trading cost settings（默认值：万分之一手续费、1 美元最低、无滑点）
        self.fee_rate = 0.0001          # 比例手续费（相对于成交金额）
        self.min_fee = 1.0              # 每笔最低手续费
        self.slippage_per_share = 0.0   # 每股滑点（价格偏移）

        # Risk & auto-trading settings
        self.stop_loss_pct = 0.0        # 单只股票止损线（亏损百分比，例如 10 表示 -10% 自动卖出）
        self.scale_step_pct = 0.0       # 分批加减仓触发阈值（盈利/亏损百分比）
        self.scale_fraction_pct = 0.0   # 触发时加减仓比例（占当前持仓的百分比）

        self.load_data()

    def load_data(self):
        """Load trade data from file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.trade_records = data.get('trade_records', [])
                    self.cash = data.get('cash', self.cash)
                    self.initial_cash = data.get('initial_cash', self.initial_cash)
                    self.portfolio = data.get('portfolio', {})
                    self.pending_orders = data.get('pending_orders', [])

                    # 加载交易成本设置（若旧文件中没有，则保持默认）
                    self.fee_rate = data.get('fee_rate', self.fee_rate)
                    self.min_fee = data.get('min_fee', self.min_fee)
                    self.slippage_per_share = data.get('slippage_per_share', self.slippage_per_share)
                    # 加载风险与自动交易设置
                    self.stop_loss_pct = data.get('stop_loss_pct', self.stop_loss_pct)
                    self.scale_step_pct = data.get('scale_step_pct', self.scale_step_pct)
                    self.scale_fraction_pct = data.get('scale_fraction_pct', self.scale_fraction_pct)
            except Exception as e:
                print(f"Failed to load data: {str(e)}")
                self.trade_records = []
                self.cash = 100000.0
                self.portfolio = {}

    def save_data(self):
        """Save trade data to file"""
        try:
            data = {
                'trade_records': self.trade_records,
                'cash': self.cash,
                'initial_cash': self.initial_cash,
                'portfolio': self.portfolio,
                'pending_orders': self.pending_orders,
                'fee_rate': self.fee_rate,
                'min_fee': self.min_fee,
                'slippage_per_share': self.slippage_per_share,
                'stop_loss_pct': self.stop_loss_pct,
                'scale_step_pct': self.scale_step_pct,
                'scale_fraction_pct': self.scale_fraction_pct
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save data: {str(e)}")

    def add_trade_record(self, date, stock_code, stock_name, trade_type, shares, price, total_amount):
        """Add trade record"""
        record = {
            'date': date,
            'stock_code': stock_code,
            'stock_name': stock_name,
            'trade_type': trade_type,
            'shares': shares,
            'price': price,
            'total_amount': total_amount
        }
        self.trade_records.append(record)
        self.save_data()

    def update_portfolio(self, stock_code, shares, price, trade_type):
        """Update portfolio information"""
        if trade_type == 'Buy':
            if stock_code in self.portfolio:
                self.portfolio[stock_code]['shares'] += shares
                self.portfolio[stock_code]['total_cost'] += shares * price
            else:
                self.portfolio[stock_code] = {
                    'shares': shares,
                    'total_cost': shares * price
                }
        else:  # Sell
            if stock_code in self.portfolio:
                self.portfolio[stock_code]['shares'] -= shares
                self.portfolio[stock_code]['total_cost'] -= shares * price
                if self.portfolio[stock_code]['shares'] == 0:
                    del self.portfolio[stock_code]

    def get_trade_records(self):
        """Get all trade records"""
        return self.trade_records

    def get_portfolio(self):
        """Get current portfolio"""
        return self.portfolio

    def get_pending_orders(self):
        return self.pending_orders

    def add_pending_order(self, order):
        self.pending_orders.append(order)
        self.save_data()

    def remove_pending_order(self, order_id):
        self.pending_orders = [o for o in self.pending_orders if o.get('id') != order_id]
        self.save_data()

    def get_cash(self):
        """Get current cash"""
        return self.cash

    def update_cash(self, amount, trade_type, fee=0.0):
        """Update cash

        amount: 成交金额（价格 × 股数），不含手续费
        fee: 手续费（正数）
        """
        if trade_type == 'Buy':
            self.cash -= (amount + fee)
        else:  # Sell
            self.cash += (amount - fee)
        self.save_data()

    def calculate_trade_costs(self, price, shares, trade_type):
        """根据当前交易成本设置，计算实际成交价、成交金额和手续费。

        返回: execution_price, gross_amount, fee
        """
        # 滑点：买入价格向上偏移，卖出价格向下偏移
        if trade_type == 'Buy':
            exec_price = price + self.slippage_per_share
        else:
            exec_price = max(0.01, price - self.slippage_per_share)

        gross = exec_price * shares
        fee = max(self.min_fee, abs(gross) * self.fee_rate) if gross > 0 else 0.0
        return exec_price, gross, fee

class StockTradeSimulator:
    def __init__(self, root, use_mock_data=None):
        self.root = root  # Save root window reference
        self.root.title("Stock Trading Simulator")  # Set window title
        self.root.geometry("1200x800")  # Set window size to 1200x800
        self.bg_color = "#f0f0f0"  # Set background color
        self.root.configure(bg=self.bg_color)

        # Set theme colors（更统一的浅色现代风，类似 macOS / iOS）
        self.primary_color = '#FFFFFF'      # 纯白主背景
        self.secondary_color = '#F5F7FB'    # 整体背景（浅蓝灰）
        self.accent_color = '#2563EB'       # 主题蓝色（按钮、高亮）
        self.success_color = '#16A34A'      # 成功绿
        self.danger_color = '#DC2626'       # 卖出红
        self.text_color = '#111827'         # 深灰黑文字
        self.bg_color = self.secondary_color
        self.panel_bg = self.primary_color  # 面板背景
        self.border_color = '#E5E7EB'       # 边框浅灰
        self.header_bg = '#EFF3FB'          # 标题栏背景
        self.hover_color = '#E0ECFF'        # 悬停/选中浅蓝
        self.cell_padding = 8  # Cell padding

        # Initialize data managers
        self.data_manager = StockDataManager(use_mock_data=use_mock_data)
        self.use_mock_data = self.data_manager.use_mock_data
        if self.use_mock_data:
            print("Running in mock data mode. Set STOCK_SIM_USE_MOCK=0 to disable.")

        # Ask user for initial cash only when no existing trade data file is present
        initial_cash = 100000.0
        trade_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trade_data.json")
        if not os.path.exists(trade_data_path):
            try:
                value = simpledialog.askfloat(
                    "Initial Capital",
                    "Please enter your initial research capital (USD):",
                    minvalue=0.0,
                    initialvalue=100000.0,
                    parent=self.root
                )
                if value is not None and value >= 0:
                    initial_cash = float(value)
            except Exception as e:
                print(f"Failed to get initial cash from user, using default 100000.0: {e}")

        self.trade_manager = TradeManager(initial_cash=initial_cash)
        
        # Initialize variables
        self.cash = self.trade_manager.get_cash()
        self.portfolio = self.trade_manager.get_portfolio()
        self.pending_orders = self.trade_manager.get_pending_orders()
        self.current_date = datetime.datetime.now().date()
        
        # Initialize stock data dictionary
        self.stocks = {}
        
        # Create UI components first
        self.create_widgets()
        
        # Check if local data exists for current date
        current_date = datetime.datetime.now()
        date_str = current_date.strftime("%Y-%m-%d")
        if date_str in self.data_manager.data:
            # Load data from local
            self.stocks = {}
            stock_list = self.data_manager.get_stock_list()
            for code, name in stock_list.items():
                if code in self.data_manager.data[date_str]:
                    stock_data = self.data_manager.data[date_str][code]
                    self.stocks[code] = {
                        "name": name,
                        "price": stock_data["price"],
                        "change_percent": stock_data["change_percent"]
                    }
            self.update_stock_listbox()
            # Automatically select first stock
            self.select_first_stock()
        else:
            # If no local data, load from network
            self.show_loading(self._loading_message())
            self.load_stocks()

        # Update portfolio and asset display
        self.update_assets()

    def _loading_message(self, action="Loading", current=None, total=None):
        """Build contextual loading text"""
        source = "mock stock data" if self.use_mock_data else "stock data from network"
        message = f"{action} {source}"
        if current is not None and total is not None:
            message += f" ({current}/{total})"
        return message + "..."

    def show_loading(self, message):
        """Show loading window"""
        self.loading_window = tk.Toplevel(self.root)
        self.loading_window.title("Network Request")
        self.loading_window.geometry("300x100")
        self.loading_window.transient(self.root)  # Set as temporary window
        self.loading_window.grab_set()  # Set as modal window
        
        # Create progress bar
        self.progress = ttk.Progressbar(
            self.loading_window,
            length=200,
            mode='indeterminate'
        )
        self.progress.pack(pady=20)
        self.progress.start()
        
        # Create label
        self.loading_label = tk.Label(
            self.loading_window,
            text=message,
            font=('Arial', 12)
        )
        self.loading_label.pack()

    def hide_loading(self):
        """Hide loading window"""
        if hasattr(self, 'loading_window'):
            self.progress.stop()
            self.loading_window.destroy()

    def load_stocks(self, target_date=None):
        """Load stock data"""
        def load_data(target_date):
            try:
                # Update loading message
                self.loading_label.config(text=self._loading_message("Loading"))
                
                # Get stock list
                self.stocks = {}
                stock_list = self.data_manager.get_stock_list()
                
                # Ensure valid target date
                if target_date is None:
                    target_date = datetime.datetime.now()
                
                # Check if local data exists for this date
                date_str = target_date.strftime("%Y-%m-%d")
                if date_str in self.data_manager.data:
                    # Load data from local
                    for code, name in stock_list.items():
                        if code in self.data_manager.data[date_str]:
                            stock_data = self.data_manager.data[date_str][code]
                            self.stocks[code] = {
                                "name": name,
                                "price": stock_data["price"],
                                "change_percent": stock_data["change_percent"]
                            }
                    self.root.after(0, self.update_stock_listbox)
                    # Automatically select first stock
                    self.root.after(0, self.select_first_stock)
                    return
                
                # If no local data, fetch from network
                self.loading_label.config(text=self._loading_message("Fetching"))
                total_stocks = len(stock_list)
                for i, (code, name) in enumerate(stock_list.items()):
                    # Update loading message
                    self.loading_label.config(text=self._loading_message("Fetching", current=i+1, total=total_stocks))
                    
                    # Get stock data
                    stock_data = self.data_manager.get_stock_data(code, target_date)
                    
                    if stock_data is not None:
                        self.stocks[code] = {
                            "name": name,
                            "price": stock_data["price"],
                            "change_percent": stock_data["change_percent"]
                        }
                    else:
                        # If fetch fails, use random data
                        self.stocks[code] = {
                            "name": name,
                            "price": random.uniform(100, 500),
                            "change_percent": random.uniform(-5, 5)
                        }
                
                # Update listbox
                self.root.after(0, self.update_stock_listbox)
                # Automatically select first stock
                self.root.after(0, self.select_first_stock)
                self.root.after(0, self.process_pending_orders)
                
            except Exception as e:
                print(f"Failed to load stock data: {str(e)}")
                # If all fetches fail, use default mock data
                self.stocks = {
                    "AAPL": {"name": "Apple", "price": 185.0, "change_percent": 2.5},
                    "GOOGL": {"name": "Google", "price": 135.0, "change_percent": -1.2},
                    "TSLA": {"name": "Tesla", "price": 250.0, "change_percent": 3.8},
                    "MSFT": {"name": "Microsoft", "price": 330.0, "change_percent": 1.5},
                    "NVDA": {"name": "NVIDIA", "price": 450.0, "change_percent": -2.1}
                }
                self.root.after(0, self.update_stock_listbox)
                # Automatically select first stock
                self.root.after(0, self.select_first_stock)
                self.root.after(0, self.process_pending_orders)
            
            finally:
                # Hide loading window
                self.root.after(0, self.hide_loading)
        
        # Load data in new thread
        thread = threading.Thread(target=load_data, args=(target_date,))
        thread.start()

    def select_first_stock(self):
        """Select first stock and show its information"""
        if self.stocks:
            # Clear current selection
            self.stock_listbox.selection_clear(0, tk.END)
            # Select first stock
            self.stock_listbox.selection_set(0)
            # Show stock information
            self.show_stock_details()

    def update_stock_listbox(self):
        """Update stock listbox"""
        self.stock_listbox.delete(0, tk.END)
        for code in self.stocks:
            name = self.stocks[code]['name']
            # Use tab for alignment
            display_text = f"{code:<6} | {name}"
            self.stock_listbox.insert(tk.END, display_text)

    # ----------------------- Auto trading rules -----------------------
    def apply_auto_trading_rules(self):
        """Apply stop-loss and scale in/out rules when date changes."""
        tm = self.trade_manager
        # 如果没有开启任何规则，直接返回
        if (tm.stop_loss_pct <= 0) and (tm.scale_step_pct <= 0 or tm.scale_fraction_pct <= 0):
            return

        if not self.stocks or not self.portfolio:
            return

        actions = []
        date_str = self.current_date.strftime('%Y-%m-%d')

        for stock_code, info in list(self.portfolio.items()):
            if stock_code not in self.stocks:
                continue
            shares = info['shares']
            if shares <= 0:
                continue

            cost = info['total_cost']
            if cost <= 0:
                continue

            current_price = self.stocks[stock_code]['price']
            current_value = current_price * shares
            pnl_pct = (current_value - cost) / cost * 100.0

            # 止损规则：亏损超过阈值，直接全仓卖出
            if tm.stop_loss_pct > 0 and pnl_pct <= -tm.stop_loss_pct:
                actions.append(('Sell', stock_code, shares, current_price, 'Auto Stop-Loss'))
                # 一旦触发止损，就不再对这只股票做分批调整
                continue

            # 分批加减仓规则
            if tm.scale_step_pct > 0 and tm.scale_fraction_pct > 0:
                step = tm.scale_step_pct
                frac = tm.scale_fraction_pct / 100.0
                scale_shares = max(1, int(shares * frac))

                if pnl_pct >= step and shares - scale_shares > 0:
                    # 盈利超过阈值 → 分批减仓
                    actions.append(('Sell', stock_code, scale_shares, current_price, 'Auto Scale-Out'))
                elif pnl_pct <= -step:
                    # 亏损但尚未触发止损 → 分批加仓
                    actions.append(('Buy', stock_code, scale_shares, current_price, 'Auto Scale-In'))

        executed = 0
        for trade_type, code, shares, base_price, reason in actions:
            stock_name = self.stocks[code]['name']
            # 计算交易成本
            exec_price, gross, fee = tm.calculate_trade_costs(base_price, shares, trade_type)

            if trade_type == 'Buy':
                # 现金是否足够
                if gross + fee > self.cash:
                    continue
                # 记录
                tm.add_trade_record(
                    date_str,
                    code,
                    stock_name,
                    'Buy',
                    shares,
                    exec_price,
                    gross
                )
                tm.update_portfolio(code, shares, exec_price, 'Buy')
                tm.update_cash(gross, 'Buy', fee=fee)
            else:
                # 检查持仓是否足够
                if code not in self.portfolio or self.portfolio[code]['shares'] < shares:
                    continue
                tm.add_trade_record(
                    date_str,
                    code,
                    stock_name,
                    'Sell',
                    shares,
                    exec_price,
                    gross
                )
                tm.update_portfolio(code, shares, exec_price, 'Sell')
                tm.update_cash(gross, 'Sell', fee=fee)

            executed += 1

        if executed > 0:
            # 同步最新账户状态并刷新界面
            self.cash = self.trade_manager.get_cash()
            self.portfolio = self.trade_manager.get_portfolio()
            self.update_assets()
            self.load_trade_records()
            self.update_portfolio_table()
            messagebox.showinfo("Auto Trading", f"{executed} auto trade(s) executed on {date_str} based on your rules.")

    def manage_stock_universe(self):
        """Open a dialog window to let user customize the stock universe (portfolio universe)."""
        manager = tk.Toplevel(self.root)
        manager.title("Manage Portfolio Universe")
        manager.geometry("420x360")
        manager.transient(self.root)
        manager.grab_set()

        frame = tk.Frame(manager, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(
            frame,
            text="Configured Stocks (code | name)",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 12, 'bold')
        ).pack(anchor='w', pady=(0, 5))

        list_frame = tk.Frame(frame, bg=self.bg_color)
        list_frame.pack(fill=tk.BOTH, expand=True)

        stock_listbox = tk.Listbox(
            list_frame,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 11),
            selectbackground=self.hover_color,
            selectforeground=self.text_color,
            activestyle='none',
            highlightthickness=0,
            relief='flat',
            borderwidth=0
        )
        stock_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=stock_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        stock_listbox.config(yscrollcommand=scrollbar.set)

        # Load current stock universe from data_manager.stock_list
        def refresh_dialog_list():
            stock_listbox.delete(0, tk.END)
            for code, name in sorted(self.data_manager.stock_list.items()):
                stock_listbox.insert(tk.END, f"{code:<6} | {name}")

        refresh_dialog_list()

        # Form for adding/editing stocks
        form_frame = tk.Frame(frame, bg=self.bg_color)
        form_frame.pack(fill=tk.X, pady=(10, 5))

        tk.Label(
            form_frame,
            text="Code:",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold')
        ).grid(row=0, column=0, padx=(0, 5), pady=2, sticky='e')

        code_entry = tk.Entry(form_frame, width=10, bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 11))
        code_entry.grid(row=0, column=1, padx=(0, 10), pady=2, sticky='w')

        tk.Label(
            form_frame,
            text="Name:",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold')
        ).grid(row=1, column=0, padx=(0, 5), pady=2, sticky='e')

        name_entry = tk.Entry(form_frame, width=20, bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 11))
        name_entry.grid(row=1, column=1, padx=(0, 10), pady=2, sticky='w')

        def on_select(event=None):
            selection = stock_listbox.curselection()
            if not selection:
                return
            text = stock_listbox.get(selection[0])
            code = text.split("|")[0].strip()
            name = self.data_manager.stock_list.get(code, "")
            code_entry.delete(0, tk.END)
            code_entry.insert(0, code)
            name_entry.delete(0, tk.END)
            name_entry.insert(0, name)

        stock_listbox.bind("<<ListboxSelect>>", on_select)

        def save_universe_to_file():
            """Persist current stock_list to stock_list.json and reload stocks."""
            path = os.path.join(self.data_manager.base_dir, "stock_list.json")
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.data_manager.stock_list, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("Success", "Stock universe saved. Reloading stock data...")
                # After updating universe, reload stocks for current date
                self.show_loading(self._loading_message())
                self.load_stocks(datetime.datetime.combine(self.current_date, datetime.time()))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save stock_list.json: {e}")

        def add_or_update_stock():
            code = code_entry.get().strip().upper()
            name = name_entry.get().strip()
            if not code or not name:
                messagebox.showerror("Error", "Please enter both stock code and name.")
                return
            self.data_manager.stock_list[code] = name
            refresh_dialog_list()
            code_entry.delete(0, tk.END)
            name_entry.delete(0, tk.END)

        def delete_selected_stock():
            selection = stock_listbox.curselection()
            if not selection:
                messagebox.showerror("Error", "Please select a stock to delete.")
                return
            text = stock_listbox.get(selection[0])
            code = text.split("|")[0].strip()
            if code in self.data_manager.stock_list:
                if messagebox.askyesno("Confirm", f"Remove {code} from portfolio universe?"):
                    del self.data_manager.stock_list[code]
                    refresh_dialog_list()

        btn_frame = tk.Frame(frame, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        tk.Button(
            btn_frame,
            text="Add / Update",
            command=add_or_update_stock,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=10,
            pady=4
        ).pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(
            btn_frame,
            text="Delete Selected",
            command=delete_selected_stock,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=10,
            pady=4
        ).pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(
            btn_frame,
            text="Save & Reload",
            command=lambda: (save_universe_to_file(), manager.destroy()),
            bg=self.accent_color,
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=10,
            pady=4
        ).pack(side=tk.RIGHT, padx=(5, 0))

    def create_widgets(self):
        # Configure ttk style
        style = ttk.Style()
        style.theme_use('default')
        
        # Configure Treeview style
        style.configure("Treeview",
            background=self.panel_bg,
            foreground=self.text_color,
            fieldbackground=self.panel_bg,
            borderwidth=0,
            font=('Segoe UI', 11),
            rowheight=30
        )
        style.configure("Treeview.Heading",
            background=self.header_bg,
            foreground=self.text_color,
            borderwidth=0,
            relief='flat',
            font=('Segoe UI', 11, 'bold'),
            padding=(self.cell_padding, self.cell_padding)
        )
        style.map("Treeview",
            background=[('selected', self.hover_color)],
            foreground=[('selected', self.text_color)]
        )

        # Create left frame
        left_frame = tk.Frame(self.root, width=280, bg=self.bg_color)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # Create date selection frame
        date_frame = tk.Frame(left_frame, bg=self.bg_color)
        date_frame.pack(fill=tk.X, pady=(0, 10))

        # Display current date label
        self.date_label = tk.Label(
            date_frame,
            text=f"Current Date: {self.current_date.strftime('%Y-%m-%d')}",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 14, 'bold')
        )
        self.date_label.pack(pady=5, padx=5)

        # Create calendar widget
        self.calendar = Calendar(
            date_frame,
            selectmode='day',
            year=int(self.current_date.strftime("%Y")),
            month=int(self.current_date.strftime("%m")),
            day=int(self.current_date.strftime("%d")),
            date_pattern='yyyy-mm-dd',
            background=self.panel_bg,
            foreground=self.text_color,
            headersbackground=self.header_bg,
            normalbackground=self.panel_bg,
            weekendbackground=self.panel_bg,
            selectbackground=self.hover_color,
            selectforeground=self.text_color,
            font=('Segoe UI', 12),
            borderwidth=0,
            showweeknumbers=False,
            width=280,
            height=300
        )
        self.calendar.pack(padx=5, pady=5)

        # Update current date
        self.calendar.bind("<<CalendarSelected>>", self.update_date)

        # Create navigation button frame
        nav_frame = tk.Frame(date_frame, bg=self.bg_color)
        nav_frame.pack(pady=5)
        
        # Previous day button
        tk.Button(
            nav_frame,
            text="Previous Day",
            command=self.previous_day,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 12, 'bold'),
            width=6,
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=10,
            pady=5
        ).pack(side=tk.LEFT, padx=2)
        
        # Next day button
        tk.Button(
            nav_frame,
            text="Next Day",
            command=self.next_day,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 12, 'bold'),
            width=6,
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=10,
            pady=5
        ).pack(side=tk.LEFT, padx=2)

        # Create stock list frame
        list_frame = tk.Frame(left_frame, bg=self.bg_color)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Header row: title + manage button
        header_frame = tk.Frame(list_frame, bg=self.bg_color)
        header_frame.pack(fill=tk.X, pady=(0, 5))

        tk.Label(
            header_frame,
            text="Stock List",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 14, 'bold')
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            header_frame,
            text="Manage Portfolio Universe",
            command=self.manage_stock_universe,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=8,
            pady=2
        ).pack(side=tk.RIGHT, padx=5)

        # Create stock list
        self.stock_listbox = tk.Listbox(
            list_frame,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 12),
            selectbackground=self.hover_color,
            selectforeground=self.text_color,
            activestyle='none',
            highlightthickness=0,
            relief='flat',
            borderwidth=0,
            height=10,
            selectmode='single'
        )
        self.stock_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.stock_listbox.bind("<<ListboxSelect>>", self.show_stock_details)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.stock_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.stock_listbox.yview)

        # Create trade frame
        trade_frame = tk.Frame(left_frame, bg=self.bg_color)
        trade_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        # Trade shares label and entry
        shares_frame = tk.Frame(trade_frame, bg=self.bg_color)
        shares_frame.pack(fill=tk.X, padx=5, pady=5)

        shares_label = tk.Label(
            shares_frame,
            text="Trade Shares",
            font=('Segoe UI', 12, 'bold'),
            bg=self.bg_color,
            fg=self.text_color
        )
        shares_label.pack(side=tk.LEFT, padx=(5, 10))

        self.shares_entry = tk.Entry(
            shares_frame,
            width=10,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 12),
            relief='solid',
            borderwidth=1,
            highlightthickness=0
        )
        self.shares_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Trade button frame
        btn_frame = tk.Frame(trade_frame, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        # Buy button
        tk.Button(
            btn_frame,
            text="Buy",
            command=self.buy_stock,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 12, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            height=2,
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        # Sell button
        tk.Button(
            btn_frame,
            text="Sell",
            command=self.sell_stock,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 12, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            height=2,
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        # Trading settings & news events buttons
        settings_frame = tk.Frame(trade_frame, bg=self.bg_color)
        settings_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        tk.Button(
            settings_frame,
            text="Trading Settings",
            command=self.open_trading_settings,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=10,
            pady=4
        ).pack(side=tk.LEFT, padx=(5, 4))

        tk.Button(
            settings_frame,
            text="Add Good News",
            command=lambda: self.add_news_event(event_type='good'),
            bg=self.panel_bg,
            fg=self.success_color,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=8,
            pady=4
        ).pack(side=tk.LEFT, padx=(0, 4))

        tk.Button(
            settings_frame,
            text="Add Bad News",
            command=lambda: self.add_news_event(event_type='bad'),
            bg=self.panel_bg,
            fg=self.danger_color,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=8,
            pady=4
        ).pack(side=tk.LEFT, padx=(0, 0))

        # Performance metrics panel (left column, under Trade Shares)
        perf_panel = tk.Frame(left_frame, bg=self.panel_bg, highlightbackground=self.border_color, highlightthickness=1)
        perf_panel.pack(fill=tk.BOTH, expand=False, pady=(8, 10), padx=0)

        tk.Label(
            perf_panel,
            text="Performance Metrics",
            font=('Segoe UI', 12, 'bold'),
            bg=self.panel_bg,
            fg=self.text_color,
            anchor='w'
        ).pack(anchor='w', padx=10, pady=(8, 2))

        metrics_frame = tk.Frame(perf_panel, bg=self.panel_bg)
        metrics_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

        self.metric_total_return = tk.Label(
            metrics_frame, text="Total Return: --", font=('Segoe UI', 11),
            bg=self.panel_bg, fg=self.text_color, anchor='w'
        )
        self.metric_total_return.pack(anchor='w')

        self.metric_max_dd = tk.Label(
            metrics_frame, text="Max Drawdown: --", font=('Segoe UI', 11),
            bg=self.panel_bg, fg=self.text_color, anchor='w'
        )
        self.metric_max_dd.pack(anchor='w')

        self.metric_sharpe = tk.Label(
            metrics_frame, text="Sharpe (daily): --", font=('Segoe UI', 11),
            bg=self.panel_bg, fg=self.text_color, anchor='w'
        )
        self.metric_sharpe.pack(anchor='w')

        self.metric_win_rate = tk.Label(
            metrics_frame, text="Win Rate / PF: --", font=('Segoe UI', 11),
            bg=self.panel_bg, fg=self.text_color, anchor='w'
        )
        self.metric_win_rate.pack(anchor='w')

        # Equity curve chart (compact)
        self.equity_canvas = None
        if MATPLOTLIB_AVAILABLE:
            self.equity_fig = Figure(figsize=(3.6, 1.8), dpi=100)
            self.equity_ax = self.equity_fig.add_subplot(111)
            self.equity_ax.set_title("Equity Curve", fontsize=10)
            self.equity_ax.grid(True, linestyle='--', alpha=0.3)
            self.equity_ax.tick_params(axis='x', labelrotation=30, labelsize=8)
            self.equity_ax.tick_params(axis='y', labelsize=8)

            equity_container = tk.Frame(perf_panel, bg=self.panel_bg)
            equity_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 8))
            self.equity_canvas = FigureCanvasTkAgg(self.equity_fig, master=equity_container)
            self.equity_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            tk.Label(
                perf_panel,
                text="Install matplotlib to view equity curve.",
                font=('Segoe UI', 10),
                bg=self.panel_bg,
                fg=self.text_color,
                anchor='w'
            ).pack(anchor='w', padx=10, pady=(0, 8))

        # Create right frame
        right_frame = tk.Frame(self.root, bg=self.bg_color)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create top info frame (horizontal: left column = stock info + assets stacked; right = orders)
        top_info_frame = tk.Frame(right_frame, bg=self.bg_color)
        top_info_frame.pack(fill=tk.X, pady=(5, 10))

        left_info_column = tk.Frame(top_info_frame, bg=self.bg_color)
        left_info_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        # Stock info frame (multi-row vertical)
        stock_info_frame = tk.Frame(left_info_column, bg=self.panel_bg, highlightbackground=self.border_color, highlightthickness=1)
        stock_info_frame.pack(fill=tk.X, padx=0, pady=(0, 6))

        self.info_name_label = tk.Label(
            stock_info_frame,
            text="Select stock to view details",
            font=('Segoe UI', 13, 'bold'),
            bg=self.panel_bg,
            fg=self.text_color,
            anchor='w'
        )
        self.info_name_label.pack(fill=tk.X, padx=10, pady=(8, 2))

        self.info_price_label = tk.Label(
            stock_info_frame,
            text="Price: --",
            font=('Segoe UI', 12),
            bg=self.panel_bg,
            fg=self.text_color,
            anchor='w'
        )
        self.info_price_label.pack(fill=tk.X, padx=10, pady=2)

        self.info_change_label = tk.Label(
            stock_info_frame,
            text="Change: --",
            font=('Segoe UI', 12),
            bg=self.panel_bg,
            fg=self.text_color,
            anchor='w'
        )
        self.info_change_label.pack(fill=tk.X, padx=10, pady=(2, 8))

        # Asset info frame (below stock info, same column)
        asset_info_frame = tk.Frame(left_info_column, bg=self.panel_bg, highlightbackground=self.border_color, highlightthickness=1)
        asset_info_frame.pack(fill=tk.X, padx=0, pady=(0, 0))

        # Order entry / pending orders frame (right of stock+asset column)
        order_frame = tk.Frame(top_info_frame, bg=self.panel_bg, highlightbackground=self.border_color, highlightthickness=1)
        order_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Header
        tk.Label(
            order_frame,
            text="Orders (Limit / Stop)",
            font=('Segoe UI', 12, 'bold'),
            bg=self.panel_bg,
            fg=self.text_color,
            anchor='w'
        ).pack(anchor='w', padx=10, pady=(8, 4))

        # Inner frame: left = form, right = table
        order_content_frame = tk.Frame(order_frame, bg=self.panel_bg)
        order_content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 8))

        # Left side: order form
        order_form = tk.Frame(order_content_frame, bg=self.panel_bg)
        order_form.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 6))

        # Side selection
        side_frame = tk.Frame(order_form, bg=self.panel_bg)
        side_frame.pack(fill=tk.X, pady=(0, 4))
        tk.Label(side_frame, text="Side:", bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        self.order_side_var = tk.StringVar(value="Buy")
        tk.Radiobutton(side_frame, text="Buy", variable=self.order_side_var, value="Buy", bg=self.panel_bg, fg=self.text_color, selectcolor=self.hover_color, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(6, 8))
        tk.Radiobutton(side_frame, text="Sell", variable=self.order_side_var, value="Sell", bg=self.panel_bg, fg=self.text_color, selectcolor=self.hover_color, font=('Segoe UI', 10)).pack(side=tk.LEFT)

        # Type selection
        type_frame = tk.Frame(order_form, bg=self.panel_bg)
        type_frame.pack(fill=tk.X, pady=(0, 4))
        tk.Label(type_frame, text="Type:", bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        self.order_type_var = tk.StringVar(value="limit")
        tk.Radiobutton(type_frame, text="Limit", variable=self.order_type_var, value="limit", bg=self.panel_bg, fg=self.text_color, selectcolor=self.hover_color, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(6, 4))
        tk.Radiobutton(type_frame, text="Stop Loss", variable=self.order_type_var, value="stop_loss", bg=self.panel_bg, fg=self.text_color, selectcolor=self.hover_color, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(4, 4))
        tk.Radiobutton(type_frame, text="Take Profit", variable=self.order_type_var, value="take_profit", bg=self.panel_bg, fg=self.text_color, selectcolor=self.hover_color, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(4, 0))

        # Price and shares inputs
        order_price_frame = tk.Frame(order_form, bg=self.panel_bg)
        order_price_frame.pack(fill=tk.X, pady=(2, 2))
        tk.Label(order_price_frame, text="Price/Trigger:", bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        self.order_price_entry = tk.Entry(order_price_frame, width=12, bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 11), relief='solid', borderwidth=1)
        self.order_price_entry.pack(side=tk.LEFT, padx=(6, 10))

        order_shares_frame = tk.Frame(order_form, bg=self.panel_bg)
        order_shares_frame.pack(fill=tk.X, pady=(0, 4))
        tk.Label(order_shares_frame, text="Shares:", bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        self.order_shares_entry = tk.Entry(order_shares_frame, width=10, bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 11), relief='solid', borderwidth=1)
        self.order_shares_entry.pack(side=tk.LEFT, padx=(6, 0))

        # Order buttons
        order_btns = tk.Frame(order_form, bg=self.panel_bg)
        order_btns.pack(fill=tk.X, pady=(2, 6))
        tk.Button(
            order_btns,
            text="Place Order",
            command=self.place_pending_order,
            bg=self.accent_color,
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=10,
            pady=4
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            order_btns,
            text="Cancel Selected",
            command=self.cancel_selected_order,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=10,
            pady=4
        ).pack(side=tk.LEFT, padx=(0, 0))

        # Right side: pending orders table
        order_table_frame = tk.Frame(order_content_frame, bg=self.panel_bg)
        order_table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0))

        columns_orders = ("code", "side", "otype", "price", "shares", "status")
        self.order_tree = ttk.Treeview(order_table_frame, columns=columns_orders, show='headings', style="Treeview", height=5)
        self.order_tree.heading("code", text="Code")
        self.order_tree.heading("side", text="Side")
        self.order_tree.heading("otype", text="Type")
        self.order_tree.heading("price", text="Price")
        self.order_tree.heading("shares", text="Shares")
        self.order_tree.heading("status", text="Status")
        for c, w in zip(columns_orders, (80, 60, 90, 80, 70, 80)):
            self.order_tree.column(c, width=w, anchor='center')

        order_scroll = ttk.Scrollbar(order_table_frame, orient=tk.VERTICAL, command=self.order_tree.yview)
        self.order_tree.configure(yscrollcommand=order_scroll.set)
        self.order_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        order_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        # Load existing pending orders into table
        self.refresh_pending_orders_table()

        # Asset title
        self.asset_label = tk.Label(
            asset_info_frame,
            text="Account Assets",
            font=('Segoe UI', 14, 'bold'),
            bg=self.panel_bg,
            fg=self.text_color,
            anchor='w'
        )
        self.asset_label.pack(anchor='w', padx=10, pady=5)

        # Cash balance
        self.cash_label = tk.Label(
            asset_info_frame,
            text=f"Cash: ${self.cash:.2f}",
            font=('Segoe UI', 12),
            bg=self.panel_bg,
            fg=self.text_color,
            anchor='w'
        )
        self.cash_label.pack(anchor='w', padx=10, pady=2)

        # Button to reset account and set a new initial cash amount
        self.reset_button = tk.Button(
            asset_info_frame,
            text="Reset Account / Set Initial Cash",
            command=self.reset_account,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 11, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=10,
            pady=5
        )
        self.reset_button.pack(anchor='w', padx=10, pady=(4, 8))

        # Performance metrics moved to left column under Trade Shares

        # K-line (candlestick) chart frame
        chart_frame = tk.Frame(right_frame, bg=self.panel_bg, highlightbackground=self.border_color, highlightthickness=1)
        # 让 K 线区域尽量占据更多垂直空间
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        tk.Label(
            chart_frame,
            text="Price K-line (Candlestick) Chart",
            font=('Segoe UI', 12, 'bold'),
            bg=self.panel_bg,
            fg=self.text_color,
            anchor='w'
        ).pack(anchor='w', padx=10, pady=5)

        self.chart_container = tk.Frame(chart_frame, bg=self.panel_bg)
        self.chart_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.kline_canvas = None

        if MATPLOTLIB_AVAILABLE:
            # Initialize a figure with two subplots: upper for price K-line (higher), lower for volume bars (lower)
            self.kline_figure = Figure(figsize=(6, 4), dpi=100)
            # 使用 GridSpec 控制高度比例：价格图 : 成交量图 = 3 : 1
            gs = self.kline_figure.add_gridspec(4, 1, hspace=0.05)
            self.kline_ax = self.kline_figure.add_subplot(gs[:3, 0])
            self.volume_ax = self.kline_figure.add_subplot(gs[3, 0], sharex=self.kline_ax)

            self.kline_ax.set_ylabel("Price")
            self.kline_ax.grid(True, linestyle='--', alpha=0.3)
            # 只在底部子图显示日期刻度
            self.kline_ax.tick_params(labelbottom=False)

            self.volume_ax.set_ylabel("Volume")
            self.volume_ax.grid(True, linestyle='--', alpha=0.3)

            self.kline_canvas = FigureCanvasTkAgg(self.kline_figure, master=self.chart_container)
            self.kline_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            tk.Label(
                self.chart_container,
                text="matplotlib not installed. Install it to enable K-line chart.",
                font=('Segoe UI', 11),
                bg=self.bg_color,
                fg=self.text_color
            ).pack(expand=True)

        # Bottom frame for portfolio and trade records side by side
        bottom_frame = tk.Frame(right_frame, bg=self.bg_color)
        # 不再让底部区域参与“扩展”，这样 K 线图可以更高
        bottom_frame.pack(fill=tk.X, expand=False)

        # Portfolio details table（不再在垂直方向扩展，以给上方图形留更多高度）
        portfolio_frame = tk.Frame(bottom_frame, bg=self.panel_bg, highlightbackground=self.border_color, highlightthickness=1)
        portfolio_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, pady=(0, 0), padx=(0, 5))

        tk.Label(
            portfolio_frame,
            text="Portfolio Details",
            font=('Segoe UI', 12, 'bold'),
            bg=self.panel_bg,
            fg=self.text_color
        ).pack(pady=5)
        
        # Create portfolio table
        columns = ('stock_code', 'stock_name', 'shares', 'cost', 'current_value', 'profit')
        self.portfolio_tree = ttk.Treeview(portfolio_frame, columns=columns, show='headings', style="Treeview")
        
        # Set column headings
        self.portfolio_tree.heading('stock_code', text='Stock Code')
        self.portfolio_tree.heading('stock_name', text='Stock Name')
        self.portfolio_tree.heading('shares', text='Shares')
        self.portfolio_tree.heading('cost', text='Cost')
        self.portfolio_tree.heading('current_value', text='Current Value')
        self.portfolio_tree.heading('profit', text='Profit/Loss')
        
        # Set column widths
        self.portfolio_tree.column('stock_code', width=100)
        self.portfolio_tree.column('stock_name', width=100)
        self.portfolio_tree.column('shares', width=80)
        self.portfolio_tree.column('cost', width=100)
        self.portfolio_tree.column('current_value', width=100)
        self.portfolio_tree.column('profit', width=120)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(portfolio_frame, orient=tk.VERTICAL, command=self.portfolio_tree.yview)
        self.portfolio_tree.configure(yscrollcommand=scrollbar.set)
        
        # Layout
        self.portfolio_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        # Trade records table（同样不扩展）
        records_frame = tk.Frame(bottom_frame, bg=self.panel_bg, highlightbackground=self.border_color, highlightthickness=1)
        records_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, pady=(0, 0), padx=(5, 0))
        
        tk.Label(
            records_frame,
            text="Trade Records",
            font=('Segoe UI', 12, 'bold'),
            bg=self.panel_bg,
            fg=self.text_color
        ).pack(pady=5)
        
        # Create table
        columns = ('date', 'stock_code', 'stock_name', 'trade_type', 'shares', 'price', 'total_amount')
        self.records_tree = ttk.Treeview(records_frame, columns=columns, show='headings', style="Treeview")
        
        # Set column headings
        self.records_tree.heading('date', text='Date')
        self.records_tree.heading('stock_code', text='Stock Code')
        self.records_tree.heading('stock_name', text='Stock Name')
        self.records_tree.heading('trade_type', text='Trade Type')
        self.records_tree.heading('shares', text='Shares')
        self.records_tree.heading('price', text='Price')
        self.records_tree.heading('total_amount', text='Total Amount')
        
        # Set column widths
        self.records_tree.column('date', width=100)
        self.records_tree.column('stock_code', width=100)
        self.records_tree.column('stock_name', width=100)
        self.records_tree.column('trade_type', width=80)
        self.records_tree.column('shares', width=80)
        self.records_tree.column('price', width=100)
        self.records_tree.column('total_amount', width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(records_frame, orient=tk.VERTICAL, command=self.records_tree.yview)
        self.records_tree.configure(yscrollcommand=scrollbar.set)
        
        # Layout
        self.records_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Load trade records
        self.load_trade_records()
        self.update_portfolio_table()

    def update_portfolio_table(self):
        """Update portfolio table"""
        # Clear existing records
        for item in self.portfolio_tree.get_children():
            self.portfolio_tree.delete(item)
        
        # Add new records
        for stock_code, info in self.portfolio.items():
            if stock_code in self.stocks:
                stock = self.stocks[stock_code]
                shares = info['shares']
                cost = info['total_cost']
                current_price = stock['price']
                current_value = current_price * shares
                profit = current_value - cost
                profit_percent = (profit / cost * 100) if cost > 0 else 0
                
                self.portfolio_tree.insert('', 'end', values=(
                    stock_code,
                    stock['name'],
                    shares,
                    f"${cost:.2f}",
                    f"${current_value:.2f}",
                    f"${profit:.2f} ({profit_percent:.2f}%)"
                ))

    def show_stock_details(self, event=None):
        """Show selected stock details"""
        selection = self.stock_listbox.curselection()
        if selection:
            index = selection[0]
            code = self.stock_listbox.get(index).split()[0]
            stock = self.stocks[code]

            # Update stock info labels
            change_percent = stock['change_percent']
            color = self.danger_color if change_percent >= 0 else self.success_color
            self.info_name_label.config(text=f"{stock['name']} ({code})")
            self.info_price_label.config(text=f"Price: ${stock['price']:.2f}")
            self.info_change_label.config(text=f"Change: {change_percent:+.2f}%", fg=color)
            
            # Update portfolio table
            self.update_portfolio_table()

            # Update K-line chart
            self.update_kline_chart(code)

    # ----------------------- Pending orders (limit / stop) -----------------------
    def refresh_pending_orders_table(self):
        if not hasattr(self, "order_tree"):
            return
        for item in self.order_tree.get_children():
            self.order_tree.delete(item)
        for order in self.pending_orders:
            oid = order.get("id", "")
            self.order_tree.insert(
                '',
                'end',
                iid=oid,
                values=(
                    order.get("code", ""),
                    order.get("side", ""),
                    order.get("type", ""),
                    f"${order.get('price', 0):.2f}",
                    order.get("shares", 0),
                    order.get("status", "open")
                )
            )

    def place_pending_order(self):
        try:
            selection = self.stock_listbox.curselection()
            if not selection:
                messagebox.showerror("Error", "Please select a stock first.")
                return
            code = self.stock_listbox.get(selection[0]).split()[0]
            stock = self.stocks.get(code)
            if not stock:
                messagebox.showerror("Error", "Stock data not available.")
                return

            side = self.order_side_var.get()
            otype = self.order_type_var.get()
            price_str = self.order_price_entry.get().strip()
            shares_str = self.order_shares_entry.get().strip()
            if not price_str or not shares_str:
                messagebox.showerror("Error", "Please input price and shares for the order.")
                return
            try:
                price = float(price_str)
                shares = int(shares_str)
            except Exception:
                messagebox.showerror("Error", "Invalid price or shares.")
                return
            if price <= 0 or shares <= 0:
                messagebox.showerror("Error", "Price and shares must be positive.")
                return

            # Restrict stop-loss / take-profit to Sell side to keep logic simple
            if otype in {"stop_loss", "take_profit"} and side != "Sell":
                messagebox.showerror("Error", "Stop Loss / Take Profit currently support Sell side only.")
                return

            order = {
                "id": f"{int(time.time()*1000)}",
                "code": code,
                "name": stock.get("name", ""),
                "side": side,
                "type": otype,
                "price": price,
                "shares": shares,
                "status": "open",
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.pending_orders.append(order)
            self.trade_manager.pending_orders = self.pending_orders
            self.trade_manager.save_data()
            self.refresh_pending_orders_table()
            messagebox.showinfo("Order Placed", f"{otype.replace('_', ' ').title()} {side} order placed for {code}.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to place order: {e}")

    def cancel_selected_order(self):
        try:
            selection = self.order_tree.selection()
            if not selection:
                return
            oid = selection[0]
            self.pending_orders = [o for o in self.pending_orders if o.get("id") != oid]
            self.trade_manager.pending_orders = self.pending_orders
            self.trade_manager.save_data()
            self.refresh_pending_orders_table()
        except Exception as e:
            print(f"Failed to cancel order: {e}")

    def process_pending_orders(self):
        """Process open limit/stop orders based on current prices."""
        if not self.pending_orders or not self.stocks:
            return
        updated = False
        executed = 0
        remaining = []
        for order in list(self.pending_orders):
            code = order.get("code")
            if code not in self.stocks:
                remaining.append(order)
                continue
            current_price = self.stocks[code]["price"]
            trigger_price = float(order.get("price", 0))
            shares = int(order.get("shares", 0))
            side = order.get("side", "Buy")
            otype = order.get("type", "limit")

            should_exec = False
            if otype == "limit":
                if side == "Buy" and current_price <= trigger_price:
                    should_exec = True
                if side == "Sell" and current_price >= trigger_price:
                    should_exec = True
            elif otype == "stop_loss":
                if side == "Sell" and current_price <= trigger_price:
                    should_exec = True
            elif otype == "take_profit":
                if side == "Sell" and current_price >= trigger_price:
                    should_exec = True

            if not should_exec:
                remaining.append(order)
                continue

            # Execute
            try:
                exec_price, gross, fee = self.trade_manager.calculate_trade_costs(current_price, shares, side)
                if side == "Buy":
                    if gross + fee > self.cash:
                        remaining.append(order)  # keep pending if insufficient cash
                        continue
                    self.trade_manager.add_trade_record(
                        self.current_date.strftime('%Y-%m-%d'),
                        code,
                        order.get("name", code),
                        'Buy',
                        shares,
                        exec_price,
                        gross
                    )
                    self.trade_manager.update_portfolio(code, shares, exec_price, 'Buy')
                    self.trade_manager.update_cash(gross, 'Buy', fee=fee)
                else:  # Sell
                    if code not in self.portfolio or self.portfolio[code]['shares'] < shares:
                        remaining.append(order)  # keep pending if not enough shares
                        continue
                    self.trade_manager.add_trade_record(
                        self.current_date.strftime('%Y-%m-%d'),
                        code,
                        order.get("name", code),
                        'Sell',
                        shares,
                        exec_price,
                        gross
                    )
                    self.trade_manager.update_portfolio(code, shares, exec_price, 'Sell')
                    self.trade_manager.update_cash(gross, 'Sell', fee=fee)

                executed += 1
                updated = True
            except Exception as e:
                print(f"Failed to execute order {order.get('id')}: {e}")
                remaining.append(order)

        if updated:
            self.pending_orders = remaining
            self.trade_manager.pending_orders = self.pending_orders
            self.trade_manager.save_data()
            self.cash = self.trade_manager.get_cash()
            self.portfolio = self.trade_manager.get_portfolio()
            self.update_assets()
            self.load_trade_records()
            self.update_portfolio_table()
            self.refresh_pending_orders_table()
            if executed > 0:
                messagebox.showinfo("Orders Executed", f"{executed} order(s) executed based on current prices.")

    def open_trading_settings(self):
        """Open a dialog to configure trading cost settings (fee rate, min fee, slippage)."""
        manager = tk.Toplevel(self.root)
        manager.title("Trading Settings")
        manager.geometry("360x220")
        manager.transient(self.root)
        manager.grab_set()

        frame = tk.Frame(manager, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(
            frame,
            text="Fee rate (as a fraction of trade value, e.g., 0.001 = 0.1%)",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 10)
        ).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 2))

        tk.Label(
            frame,
            text="Fee rate:",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold')
        ).grid(row=1, column=0, sticky='e', pady=2, padx=(0, 5))

        fee_rate_var = tk.StringVar(value=f"{self.trade_manager.fee_rate:.6f}")
        fee_rate_entry = tk.Entry(frame, textvariable=fee_rate_var, width=12, bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 11))
        fee_rate_entry.grid(row=1, column=1, sticky='w', pady=2)

        tk.Label(
            frame,
            text="Minimum fee (USD):",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold')
        ).grid(row=2, column=0, sticky='e', pady=2, padx=(0, 5))

        min_fee_var = tk.StringVar(value=f"{self.trade_manager.min_fee:.2f}")
        min_fee_entry = tk.Entry(frame, textvariable=min_fee_var, width=12, bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 11))
        min_fee_entry.grid(row=2, column=1, sticky='w', pady=2)

        tk.Label(
            frame,
            text="Slippage per share (USD):",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold')
        ).grid(row=3, column=0, sticky='e', pady=2, padx=(0, 5))

        slippage_var = tk.StringVar(value=f"{self.trade_manager.slippage_per_share:.4f}")
        slippage_entry = tk.Entry(frame, textvariable=slippage_var, width=12, bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 11))
        slippage_entry.grid(row=3, column=1, sticky='w', pady=2)

        # Risk & auto-trading settings
        tk.Label(
            frame,
            text="Stop-loss threshold (% loss, e.g., 10 means -10%):",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 10)
        ).grid(row=4, column=0, columnspan=2, sticky='w', pady=(8, 2))

        tk.Label(
            frame,
            text="Stop-loss %:",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold')
        ).grid(row=5, column=0, sticky='e', pady=2, padx=(0, 5))

        stop_loss_var = tk.StringVar(value=f"{self.trade_manager.stop_loss_pct:.2f}")
        stop_loss_entry = tk.Entry(frame, textvariable=stop_loss_var, width=12, bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 11))
        stop_loss_entry.grid(row=5, column=1, sticky='w', pady=2)

        tk.Label(
            frame,
            text="Scale step % (gain/loss to trigger scale in/out):",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 10)
        ).grid(row=6, column=0, columnspan=2, sticky='w', pady=(8, 2))

        tk.Label(
            frame,
            text="Scale step %:",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold')
        ).grid(row=7, column=0, sticky='e', pady=2, padx=(0, 5))

        scale_step_var = tk.StringVar(value=f"{self.trade_manager.scale_step_pct:.2f}")
        scale_step_entry = tk.Entry(frame, textvariable=scale_step_var, width=12, bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 11))
        scale_step_entry.grid(row=7, column=1, sticky='w', pady=2)

        tk.Label(
            frame,
            text="Scale fraction % (portion of current position to adjust):",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 10)
        ).grid(row=8, column=0, columnspan=2, sticky='w', pady=(2, 2))

        tk.Label(
            frame,
            text="Scale fraction %:",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold')
        ).grid(row=9, column=0, sticky='e', pady=2, padx=(0, 5))

        scale_fraction_var = tk.StringVar(value=f"{self.trade_manager.scale_fraction_pct:.2f}")
        scale_fraction_entry = tk.Entry(frame, textvariable=scale_fraction_var, width=12, bg=self.panel_bg, fg=self.text_color, font=('Segoe UI', 11))
        scale_fraction_entry.grid(row=9, column=1, sticky='w', pady=2)

        def save_settings():
            try:
                fee_rate = float(fee_rate_var.get())
                min_fee = float(min_fee_var.get())
                slippage = float(slippage_var.get())
                stop_loss = float(stop_loss_var.get())
                scale_step = float(scale_step_var.get())
                scale_fraction = float(scale_fraction_var.get())

                if fee_rate < 0 or min_fee < 0 or slippage < 0 or stop_loss < 0 or scale_step < 0 or scale_fraction < 0:
                    messagebox.showerror("Error", "All values must be non-negative.")
                    return

                self.trade_manager.fee_rate = fee_rate
                self.trade_manager.min_fee = min_fee
                self.trade_manager.slippage_per_share = slippage
                self.trade_manager.stop_loss_pct = stop_loss
                self.trade_manager.scale_step_pct = scale_step
                self.trade_manager.scale_fraction_pct = scale_fraction
                self.trade_manager.save_data()

                messagebox.showinfo("Success", "Trading settings updated successfully.")
                manager.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numeric values.")

        btn_frame = tk.Frame(frame, bg=self.bg_color)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(12, 0))

        tk.Button(
            btn_frame,
            text="Save",
            command=save_settings,
            bg=self.accent_color,
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=16,
            pady=4
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_frame,
            text="Cancel",
            command=manager.destroy,
            bg=self.panel_bg,
            fg=self.text_color,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            padx=16,
            pady=4
        ).pack(side=tk.LEFT)

    # ----------------------- News / sentiment events -----------------------
    def add_news_event(self, event_type='good'):
        """Add a good/bad news event for the currently selected stock starting from current date."""
        selection = self.stock_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a stock in the list first.")
            return

        index = selection[0]
        stock_code = self.stock_listbox.get(index).split()[0]
        stock_name = self.stocks[stock_code]['name']

        # Default settings: good news +3%, bad news -3%, duration 5 days
        default_impact = 3.0 if event_type == 'good' else -3.0
        title = "Add Good News Event" if event_type == 'good' else "Add Bad News Event"

        # Ask user for impact and duration
        impact = simpledialog.askfloat(
            title,
            f"Set daily impact percentage for {stock_name} ({stock_code}).\n"
            f"Positive for good news, negative for bad news.\n\n"
            f"Example: 3 means +3% extra per day.",
            initialvalue=default_impact,
            parent=self.root
        )
        if impact is None:
            return

        days = simpledialog.askinteger(
            title,
            "How many days should this event last?",
            initialvalue=5,
            minvalue=1,
            maxvalue=365,
            parent=self.root
        )
        if days is None or days <= 0:
            return

        # Add event to data manager
        self.data_manager.add_event(stock_code, self.current_date, days, impact)

        # Reload current date prices so effect is visible immediately
        self.show_loading(self._loading_message("Loading"))
        self.load_stocks(datetime.datetime.combine(self.current_date, datetime.time()))

        messagebox.showinfo(
            "News Event Added",
            f"{'Good' if impact >= 0 else 'Bad'} news event added for {stock_name} ({stock_code}) "
            f"from {self.current_date.strftime('%Y-%m-%d')} for {days} day(s), "
            f"impact {impact:+.2f}% per day."
        )

    def load_trade_records(self):
        """Load trade records to table"""
        # Clear existing records
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)
        
        # Add new records
        records = self.trade_manager.get_trade_records()
        for record in records:
            self.records_tree.insert('', 'end', values=(
                record['date'],
                record['stock_code'],
                record['stock_name'],
                record['trade_type'],
                record['shares'],
                f"${record['price']:.2f}",
                f"${record['total_amount']:.2f}"
            ))

    def update_assets(self):
        """Update asset display"""
        total_value = self.cash
        portfolio_text = "Portfolio Details:\n"
        
        for stock_code, info in self.portfolio.items():
            if stock_code in self.stocks:
                current_price = self.stocks[stock_code]['price']
                shares = info['shares']
                cost = info['total_cost']
                profit = (current_price * shares - cost)
                profit_percent = (profit / cost * 100) if cost > 0 else 0
                
                portfolio_text += f"{self.stocks[stock_code]['name']} ({stock_code}): {shares} shares\n"
                portfolio_text += f"  Cost: ${cost:.2f}\n"
                portfolio_text += f"  Current Value: ${current_price * shares:.2f}\n"
                portfolio_text += f"  Profit/Loss: ${profit:.2f} ({profit_percent:.2f}%)\n\n"
                
                total_value += current_price * shares
        # Update portfolio details and total asset display
        self.asset_label.config(text=f"Total Assets: ${total_value:.2f}")
        self.cash_label.config(text=f"Cash: ${self.cash:.2f}")

        # Update performance metrics & equity curve
        self.update_equity_metrics(total_value)

    def _build_equity_curve(self, include_current=True):
        """Replay trade records to build equity curve (date, equity)."""
        records = self.trade_manager.get_trade_records()
        if not records:
            current_equity = self.cash
            for code, info in self.portfolio.items():
                price = self.stocks.get(code, {}).get('price', 0)
                current_equity += price * info['shares']
            return [(self.current_date, current_equity)]

        # Sort by date then insertion order
        def _parse_date(rec):
            try:
                return datetime.datetime.strptime(rec['date'], "%Y-%m-%d").date()
            except Exception:
                return self.current_date

        sorted_records = sorted(enumerate(records), key=lambda x: (_parse_date(x[1]), x[0]))

        cash = float(self.trade_manager.initial_cash)
        holdings = {}
        last_price = {}
        curve = []

        for _, rec in sorted_records:
            date = _parse_date(rec)
            code = rec['stock_code']
            price = float(rec['price'])
            shares = int(rec['shares'])
            trade_type = rec['trade_type']

            if trade_type == 'Buy':
                cash -= float(rec['total_amount'])
                holdings[code] = holdings.get(code, 0) + shares
            else:  # Sell
                cash += float(rec['total_amount'])
                holdings[code] = holdings.get(code, 0) - shares
                if holdings.get(code, 0) <= 0:
                    holdings.pop(code, None)

            last_price[code] = price
            equity = cash + sum(holdings[c] * last_price.get(c, 0) for c in holdings)
            curve.append((date, equity))

        if include_current:
            current_equity = self.cash
            for code, info in self.portfolio.items():
                px = self.stocks.get(code, {}).get('price', last_price.get(code, 0))
                current_equity += px * info['shares']
            curve.append((self.current_date, current_equity))

        return curve

    def _compute_performance_stats(self, curve):
        """Compute basic performance stats from equity curve."""
        if not curve:
            return {}
        # Sort by date
        curve = sorted(curve, key=lambda x: x[0])
        dates = [c[0] for c in curve]
        values = np.array([c[1] for c in curve], dtype=float)
        if len(values) == 0:
            return {}

        total_return = values[-1] / values[0] - 1 if values[0] != 0 else 0.0

        # Daily returns
        if len(values) > 1 and np.all(values[:-1] > 0):
            rets = np.diff(values) / values[:-1]
            avg_ret = rets.mean()
            vol = rets.std(ddof=1) if len(rets) > 1 else 0.0
            sharpe = (avg_ret / vol * np.sqrt(252)) if vol > 1e-9 else 0.0
        else:
            sharpe = 0.0

        cum_max = np.maximum.accumulate(values)
        drawdowns = (cum_max - values) / cum_max
        max_dd = drawdowns.max() if len(drawdowns) else 0.0

        # CAGR based on days
        span_days = max(1, (dates[-1] - dates[0]).days or 1)
        cagr = (values[-1] / values[0]) ** (365 / span_days) - 1 if values[0] > 0 else 0.0

        # Win rate / profit factor from realized trades
        win_count = 0
        loss_count = 0
        profit_sum = 0.0
        loss_sum = 0.0
        holdings = {}
        avg_cost = {}
        records = self.trade_manager.get_trade_records()
        for rec in records:
            code = rec['stock_code']
            shares = int(rec['shares'])
            price = float(rec['price'])
            if rec['trade_type'] == 'Buy':
                prev_shares = holdings.get(code, 0)
                prev_cost = avg_cost.get(code, 0.0) * prev_shares
                new_total_shares = prev_shares + shares
                new_total_cost = prev_cost + shares * price
                holdings[code] = new_total_shares
                avg_cost[code] = new_total_cost / new_total_shares if new_total_shares > 0 else 0.0
            else:
                if holdings.get(code, 0) <= 0:
                    continue
                cost_basis = avg_cost.get(code, 0.0)
                pnl = (price - cost_basis) * shares
                if pnl >= 0:
                    win_count += 1
                    profit_sum += pnl
                else:
                    loss_count += 1
                    loss_sum += pnl
                holdings[code] = holdings.get(code, 0) - shares
                if holdings[code] <= 0:
                    holdings.pop(code, None)
                    avg_cost.pop(code, None)

        total_trades = win_count + loss_count
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0
        profit_factor = (profit_sum / abs(loss_sum)) if loss_sum < 0 else (profit_sum if profit_sum > 0 else 0.0)

        return {
            "total_return": total_return,
            "cagr": cagr,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "curve": curve
        }

    def update_equity_metrics(self, latest_total_value):
        """Update equity metrics labels and plot."""
        try:
            curve = self._build_equity_curve(include_current=True)
            stats = self._compute_performance_stats(curve)
            if not stats:
                msg = "Total Return: --"
                self.metric_total_return.config(text=msg)
                self.metric_max_dd.config(text="Max Drawdown: --")
                self.metric_sharpe.config(text="Sharpe (daily): --")
                self.metric_win_rate.config(text="Win Rate / PF: --")
                return

            self.metric_total_return.config(
                text=f"Total Return: {stats['total_return']*100:.2f}% | CAGR: {stats['cagr']*100:.2f}%"
            )
            self.metric_max_dd.config(text=f"Max Drawdown: {stats['max_dd']*100:.2f}%")
            self.metric_sharpe.config(text=f"Sharpe (daily): {stats['sharpe']:.2f}")
            self.metric_win_rate.config(
                text=f"Win Rate: {stats['win_rate']:.1f}% | PF: {stats['profit_factor']:.2f}"
            )

            if MATPLOTLIB_AVAILABLE and self.equity_canvas is not None:
                self.equity_ax.clear()
                self.equity_ax.grid(True, linestyle='--', alpha=0.3)
                dates = [d for d, _ in stats['curve']]
                values = [v for _, v in stats['curve']]
                self.equity_ax.plot(dates, values, color=self.accent_color, linewidth=1.6)
                self.equity_ax.set_title("Equity Curve", fontsize=10)
                self.equity_ax.tick_params(axis='x', labelrotation=30, labelsize=8)
                self.equity_ax.tick_params(axis='y', labelsize=8)
                self.equity_ax.set_ylabel("USD", fontsize=8)
                self.equity_fig.tight_layout()
                self.equity_canvas.draw()
        except Exception as e:
            print(f"Failed to update equity metrics: {e}")

    def update_kline_chart(self, stock_code):
        """Update K-line chart for the selected stock."""
        if not MATPLOTLIB_AVAILABLE or self.kline_canvas is None:
            return
        try:
            end_date = datetime.datetime.combine(self.current_date, datetime.time())
            history = self.data_manager.get_stock_history(stock_code, end_date, window_days=60)
            if history is None or history.empty:
                self.kline_ax.clear()
                self.volume_ax.clear()
                self.kline_ax.set_title(f"{stock_code} - No historical data")
                self.kline_ax.set_ylabel("Price")
                self.kline_ax.grid(True, linestyle='--', alpha=0.3)
                self.volume_ax.set_ylabel("Volume")
                self.volume_ax.grid(True, linestyle='--', alpha=0.3)
                self.kline_canvas.draw()
                return

            # Prepare data
            dates = pd.to_datetime(history['date'])
            opens = history['open'].astype(float).values
            highs = history['high'].astype(float).values
            lows = history['low'].astype(float).values
            closes = history['close'].astype(float).values
            volumes = history['volume'].astype(float).values

            self.kline_ax.clear()
            self.volume_ax.clear()
            self.kline_ax.grid(True, linestyle='--', alpha=0.3)
            self.kline_ax.set_title(f"{stock_code} - Recent 60-Day K-line")
            self.kline_ax.set_ylabel("Price")
            self.volume_ax.set_ylabel("Volume")
            self.volume_ax.grid(True, linestyle='--', alpha=0.3)

            # X positions for candles
            x = range(len(dates))
            width = 0.6

            for i in x:
                o = opens[i]
                h = highs[i]
                l = lows[i]
                c = closes[i]
                color = '#DC3545' if c >= o else '#198754'  # red for up, green for down
                # High-low line
                self.kline_ax.vlines(i, l, h, color=color, linewidth=1)
                # Open-close box
                lower = min(o, c)
                height = abs(c - o) if abs(c - o) > 1e-6 else (h - l) * 0.1
                self.kline_ax.add_patch(
                    matplotlib.patches.Rectangle(
                        (i - width / 2, lower),
                        width,
                        height,
                        edgecolor=color,
                        facecolor=color,
                        linewidth=0.8
                    )
                )

                # Volume bars（使用同色系表示涨跌）
                self.volume_ax.bar(i, volumes[i], color=color, width=width, alpha=0.7)

            # X-axis labels: show sparse date ticks
            xticks = list(x)[::max(1, len(x)//8)]
            self.kline_ax.set_xticks(xticks)
            # 只在底部成交量图上显示日期标签，顶部价格图隐藏 x 轴标签
            self.volume_ax.set_xticks(xticks)
            self.volume_ax.set_xticklabels(
                [dates[i].strftime("%m-%d") for i in range(0, len(dates), max(1, len(dates)//8))],
                rotation=45, ha='right', fontsize=8
            )

            self.kline_canvas.draw()
        except Exception as e:
            print(f"Failed to update K-line chart for {stock_code}: {e}")

    def reset_account(self):
        """Reset account: set a new initial cash amount and clear portfolio & trade records"""
        try:
            value = simpledialog.askfloat(
                "Reset Account",
                "Enter new initial cash amount (USD):",
                minvalue=0.0,
                initialvalue=self.cash,
                parent=self.root
            )
            if value is None:
                return
            if value < 0:
                messagebox.showerror("Error", "Initial cash must be non-negative.")
                return

            # Reset trade data
            self.trade_manager.trade_records = []
            self.trade_manager.portfolio = {}
            self.trade_manager.initial_cash = float(value)
            self.trade_manager.cash = float(value)
            self.trade_manager.save_data()

            # Sync UI state
            self.cash = self.trade_manager.get_cash()
            self.portfolio = self.trade_manager.get_portfolio()
            self.load_trade_records()
            self.update_portfolio_table()
            self.update_assets()

            messagebox.showinfo("Success", f"Account has been reset with initial cash ${self.cash:.2f}.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset account: {e}")

    def buy_stock(self):
        """Buy stock"""
        try:
            shares = int(self.shares_entry.get())
            if shares <= 0:
                messagebox.showerror("Error", "Please enter a valid number of shares")
                return

            selected_index = self.stock_listbox.curselection()
            if not selected_index:
                messagebox.showerror("Error", "Please select a stock to buy")
                return

            stock_code = self.stock_listbox.get(selected_index).split()[0]
            stock_name = self.stocks[stock_code]['name']
            price = self.stocks[stock_code]['price']

            # 计算实际成交价、成交金额和手续费
            exec_price, total_amount, fee = self.trade_manager.calculate_trade_costs(price, shares, 'Buy')
            
            if total_amount + fee > self.cash:
                messagebox.showerror("Error", "Insufficient cash (including fees)")
                return

            # Update trade record
            self.trade_manager.add_trade_record(
                self.current_date.strftime('%Y-%m-%d'),
                stock_code,
                stock_name,
                'Buy',
                shares,
                exec_price,
                total_amount
            )
            
            # Update portfolio
            self.trade_manager.update_portfolio(stock_code, shares, price, 'Buy')
            
            # Update cash
            self.trade_manager.update_cash(total_amount, 'Buy', fee=fee)
            
            # Update display
            self.cash = self.trade_manager.get_cash()
            self.portfolio = self.trade_manager.get_portfolio()
            self.update_assets()
            self.load_trade_records()
            self.update_portfolio_table()
            
            messagebox.showinfo("Success", f"Successfully bought {shares} shares of {stock_name}")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number of shares")

    def sell_stock(self):
        """Sell stock"""
        try:
            shares = int(self.shares_entry.get())
            if shares <= 0:
                messagebox.showerror("Error", "Please enter a valid number of shares")
                return

            selected_index = self.stock_listbox.curselection()
            if not selected_index:
                messagebox.showerror("Error", "Please select a stock to sell")
                return

            stock_code = self.stock_listbox.get(selected_index).split()[0]
            stock_name = self.stocks[stock_code]['name']

            if stock_code not in self.portfolio:
                messagebox.showerror("Error", "You don't have this stock in your portfolio")
                return

            if shares > self.portfolio[stock_code]['shares']:
                messagebox.showerror("Error", "Sell quantity exceeds portfolio quantity")
                return

            price = self.stocks[stock_code]['price']

            # 计算实际成交价、成交金额和手续费
            exec_price, total_amount, fee = self.trade_manager.calculate_trade_costs(price, shares, 'Sell')
            
            # Update trade record
            self.trade_manager.add_trade_record(
                self.current_date.strftime('%Y-%m-%d'),
                stock_code,
                stock_name,
                'Sell',
                shares,
                exec_price,
                total_amount
            )
            
            # Update portfolio
            self.trade_manager.update_portfolio(stock_code, shares, price, 'Sell')
            
            # Update cash
            self.trade_manager.update_cash(total_amount, 'Sell', fee=fee)
            
            # Update display
            self.cash = self.trade_manager.get_cash()
            self.portfolio = self.trade_manager.get_portfolio()
            self.update_assets()
            self.load_trade_records()
            self.update_portfolio_table()
            
            messagebox.showinfo("Success", f"Successfully sold {shares} shares of {stock_name}")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number of shares")

    def update_date(self, event):
        """Update date and reload data"""
        # Save current selected stock index
        current_selection = self.stock_listbox.curselection()
        selected_index = current_selection[0] if current_selection else 0

        selected_date = datetime.datetime.strptime(self.calendar.get_date(), "%Y-%m-%d")
        self.current_date = selected_date.date()
        self.date_label.config(text=f"Current Date: {self.current_date}")
        self.show_loading(self._loading_message())
        
        def after_load():
            # Restore previous selection or select first item
            self.stock_listbox.selection_clear(0, tk.END)
            if selected_index < self.stock_listbox.size():
                self.stock_listbox.selection_set(selected_index)
                self.stock_listbox.see(selected_index)
            else:
                self.stock_listbox.selection_set(0)
                self.stock_listbox.see(0)
            self.show_stock_details()
            # 应用自动交易规则
            self.apply_auto_trading_rules()

        self.load_stocks(selected_date)
        self.root.after(100, after_load)  # Wait for data loading to complete before restoring selection

    def previous_day(self):
        """Navigate to previous day and reload data"""
        # Save current selected stock index
        current_selection = self.stock_listbox.curselection()
        selected_index = current_selection[0] if current_selection else 0

        current_date = datetime.datetime.strptime(self.calendar.get_date(), "%Y-%m-%d")
        previous_date = current_date - datetime.timedelta(days=1)
        self.calendar.selection_set(previous_date.date())
        self.date_label.config(text=f"Current Date: {self.calendar.get_date()}")
        self.show_loading(self._loading_message())
        
        def after_load():
            # Restore previous selection or select first item
            self.stock_listbox.selection_clear(0, tk.END)
            if selected_index < self.stock_listbox.size():
                self.stock_listbox.selection_set(selected_index)
                self.stock_listbox.see(selected_index)
            else:
                self.stock_listbox.selection_set(0)
                self.stock_listbox.see(0)
            self.show_stock_details()
            # 应用自动交易规则
            self.apply_auto_trading_rules()

        self.load_stocks(previous_date)
        self.root.after(100, after_load)  # Wait for data loading to complete before restoring selection

    def next_day(self):
        """Navigate to next day and reload data"""
        # Save current selected stock index
        current_selection = self.stock_listbox.curselection()
        selected_index = current_selection[0] if current_selection else 0

        current_date = datetime.datetime.strptime(self.calendar.get_date(), "%Y-%m-%d")
        next_date = current_date + datetime.timedelta(days=1)
        self.calendar.selection_set(next_date.date())
        self.date_label.config(text=f"Current Date: {self.calendar.get_date()}")
        self.show_loading(self._loading_message())
        
        def after_load():
            # Restore previous selection or select first item
            self.stock_listbox.selection_clear(0, tk.END)
            if selected_index < self.stock_listbox.size():
                self.stock_listbox.selection_set(selected_index)
                self.stock_listbox.see(selected_index)
            else:
                self.stock_listbox.selection_set(0)
                self.stock_listbox.see(0)
            self.show_stock_details()
            # 应用自动交易规则
            self.apply_auto_trading_rules()

        self.load_stocks(next_date)
        self.root.after(100, after_load)  # Wait for data loading to complete before restoring selection


if __name__ == "__main__":
    root = tk.Tk()  # Create main window
    app = StockTradeSimulator(root)  # Instantiate stock trading simulator
    root.mainloop()  # Enter main event loop