//! Central app state with mocked data models for quant research.

use serde::{Deserialize, Serialize};

// ---------- Core models ----------

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct SymbolMetrics {
    pub symbol: String,
    pub name: String,
    pub price: f64,
    pub change: f64,
    pub change_pct: f64,
    pub high_52w: f64,
    pub low_52w: f64,
    pub volatility_30d: f64,
    pub volume: u64,
    pub market_cap_b: f64,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct Greeks {
    pub delta: f64,
    pub gamma: f64,
    pub theta: f64,
    pub vega: f64,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct OptionContract {
    pub symbol: String,
    pub strike: f64,
    pub expiry: String,
    pub kind: OptionKind,
    pub bid: f64,
    pub ask: f64,
    pub last: f64,
    pub iv: f64,
    pub volume: u32,
    pub open_interest: u32,
    pub greeks: Greeks,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub enum OptionKind {
    Call,
    #[default]
    Put,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct PortfolioPosition {
    pub symbol: String,
    pub quantity: i32,
    pub avg_cost: f64,
    pub market_value: f64,
    pub pnl: f64,
    pub pnl_pct: f64,
    pub greeks: Greeks,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct EarningsHistory {
    pub date: String,
    pub eps_est: f64,
    pub eps_act: f64,
    pub surprise_pct: f64,
    pub revenue_est_m: f64,
    pub revenue_act_m: f64,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct BacktestResult {
    pub total_return_pct: f64,
    pub sharpe: f64,
    pub max_drawdown_pct: f64,
    pub win_rate_pct: f64,
    pub trades: u32,
    pub equity_curve: Vec<f64>,
}

// ---------- App state (mocked) ----------

#[derive(Clone)]
pub struct AppState {
    pub symbol_metrics: Vec<SymbolMetrics>,
    pub options_chain: Vec<OptionContract>,
    pub portfolio_positions: Vec<PortfolioPosition>,
    pub net_greeks: Greeks,
    pub earnings: Vec<EarningsHistory>,
    pub backtest_result: BacktestResult,
    pub pnl_total: f64,
    pub pnl_daily: f64,
    pub pnl_monthly: f64,
    pub pnl_yearly: f64,
    pub watchlist: Vec<String>,
    pub top_plays: Vec<(String, String)>, // symbol, reason
    pub recent_signals: Vec<(String, String)>, // title, description
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            symbol_metrics: mock_symbol_metrics(),
            options_chain: mock_options_chain(),
            portfolio_positions: mock_portfolio_positions(),
            net_greeks: mock_net_greeks(),
            earnings: mock_earnings(),
            backtest_result: mock_backtest_result(),
            pnl_total: 124_500.0,
            pnl_daily: 2_340.0,
            pnl_monthly: 18_200.0,
            pnl_yearly: 124_500.0,
            watchlist: vec![
                "AAPL".into(),
                "MSFT".into(),
                "NVDA".into(),
                "GOOGL".into(),
                "META".into(),
            ],
            top_plays: vec![
                ("AAPL".into(), "Earnings strangle, 7 DTE".into()),
                ("NVDA".into(), "IV crush play post-event".into()),
                ("SPY".into(), "Weekly put spread".into()),
            ],
            recent_signals: vec![
                ("IV rank spike".into(), "AAPL 30d IV rank > 60".into()),
                ("Earnings soon".into(), "META ER in 5 days".into()),
                ("Theta decay".into(), "Sold 15 delta put, 45 DTE".into()),
            ],
        }
    }
}

fn mock_symbol_metrics() -> Vec<SymbolMetrics> {
    vec![
        SymbolMetrics {
            symbol: "AAPL".into(),
            name: "Apple Inc.".into(),
            price: 228.45,
            change: 2.31,
            change_pct: 1.02,
            high_52w: 237.23,
            low_52w: 164.08,
            volatility_30d: 0.22,
            volume: 52_000_000,
            market_cap_b: 3520.0,
        },
        SymbolMetrics {
            symbol: "NVDA".into(),
            name: "NVIDIA Corporation".into(),
            price: 495.22,
            change: -5.18,
            change_pct: -1.03,
            high_52w: 505.0,
            low_52w: 138.0,
            volatility_30d: 0.45,
            volume: 38_000_000,
            market_cap_b: 1220.0,
        },
    ]
}

fn mock_options_chain() -> Vec<OptionContract> {
    vec![
        OptionContract {
            symbol: "AAPL".into(),
            strike: 225.0,
            expiry: "2025-03-21".into(),
            kind: OptionKind::Call,
            bid: 12.40,
            ask: 12.80,
            last: 12.60,
            iv: 0.28,
            volume: 1200,
            open_interest: 5400,
            greeks: Greeks {
                delta: 0.52,
                gamma: 0.032,
                theta: -0.08,
                vega: 0.42,
            },
        },
        OptionContract {
            symbol: "AAPL".into(),
            strike: 225.0,
            expiry: "2025-03-21".into(),
            kind: OptionKind::Put,
            bid: 8.20,
            ask: 8.50,
            last: 8.35,
            iv: 0.26,
            volume: 800,
            open_interest: 3200,
            greeks: Greeks {
                delta: -0.48,
                gamma: 0.032,
                theta: -0.06,
                vega: 0.40,
            },
        },
        OptionContract {
            symbol: "AAPL".into(),
            strike: 230.0,
            expiry: "2025-03-21".into(),
            kind: OptionKind::Call,
            bid: 9.10,
            ask: 9.50,
            last: 9.30,
            iv: 0.27,
            volume: 900,
            open_interest: 4100,
            greeks: Greeks {
                delta: 0.42,
                gamma: 0.030,
                theta: -0.07,
                vega: 0.38,
            },
        },
    ]
}

fn mock_portfolio_positions() -> Vec<PortfolioPosition> {
    vec![
        PortfolioPosition {
            symbol: "AAPL".into(),
            quantity: 100,
            avg_cost: 215.0,
            market_value: 22_845.0,
            pnl: 1_345.0,
            pnl_pct: 6.26,
            greeks: Greeks {
                delta: 52.0,
                gamma: 3.2,
                theta: -8.0,
                vega: 42.0,
            },
        },
        PortfolioPosition {
            symbol: "NVDA".into(),
            quantity: -20,
            avg_cost: 480.0,
            market_value: -9_904.4,
            pnl: -304.4,
            pnl_pct: -3.17,
            greeks: Greeks {
                delta: -8.4,
                gamma: 0.6,
                theta: 2.2,
                vega: -18.0,
            },
        },
    ]
}

fn mock_net_greeks() -> Greeks {
    Greeks {
        delta: 43.6,
        gamma: 3.8,
        theta: -5.8,
        vega: 24.0,
    }
}

fn mock_earnings() -> Vec<EarningsHistory> {
    vec![
        EarningsHistory {
            date: "2024-10-31".into(),
            eps_est: 1.39,
            eps_act: 1.64,
            surprise_pct: 18.0,
            revenue_est_m: 94_000.0,
            revenue_act_m: 94_852.0,
        },
        EarningsHistory {
            date: "2024-07-31".into(),
            eps_est: 1.21,
            eps_act: 1.40,
            surprise_pct: 15.7,
            revenue_est_m: 84_500.0,
            revenue_act_m: 85_800.0,
        },
    ]
}

fn mock_backtest_result() -> BacktestResult {
    BacktestResult {
        total_return_pct: 12.4,
        sharpe: 1.35,
        max_drawdown_pct: -4.2,
        win_rate_pct: 58.0,
        trades: 142,
        equity_curve: vec![
            100.0, 100.5, 101.2, 99.8, 102.1, 103.5, 102.0, 104.2, 105.0, 106.2, 107.0, 108.5,
            109.0, 110.2, 112.4,
        ],
    }
}
