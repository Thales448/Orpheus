/// Known module type identifiers (must match registry).
pub mod kind {
    pub const PRICE_CHART: &str = "price_chart";
    pub const IV_METRICS: &str = "iv_metrics";
    pub const OPTIONS_CHAIN: &str = "options_chain";
    pub const GREEKS_SUMMARY: &str = "greeks_summary";
    pub const EARNINGS_HISTORY: &str = "earnings_history";
    pub const PORTFOLIO_EXPOSURE: &str = "portfolio_exposure";
    pub const PAYOFF_DIAGRAM: &str = "payoff_diagram";
    pub const BACKTEST_EDITOR: &str = "backtest_editor";
}

/// Metadata for a module type (shown in Module Library).
#[derive(Clone, Debug)]
pub struct ModuleMeta {
    pub id: &'static str,
    pub name: &'static str,
    pub description: &'static str,
    pub default_width: u32,
    pub default_height: u32,
}

pub fn all_module_meta() -> Vec<ModuleMeta> {
    vec![
        ModuleMeta {
            id: kind::PRICE_CHART,
            name: "Price & Trend Chart",
            description: "Candlestick or line chart for symbol price",
            default_width: 4,
            default_height: 2,
        },
        ModuleMeta {
            id: kind::IV_METRICS,
            name: "IV Metrics",
            description: "Implied volatility surface and metrics",
            default_width: 2,
            default_height: 2,
        },
        ModuleMeta {
            id: kind::OPTIONS_CHAIN,
            name: "Options Chain",
            description: "Calls and puts table",
            default_width: 4,
            default_height: 3,
        },
        ModuleMeta {
            id: kind::GREEKS_SUMMARY,
            name: "Greeks Summary",
            description: "Delta, Gamma, Theta, Vega summary",
            default_width: 2,
            default_height: 2,
        },
        ModuleMeta {
            id: kind::EARNINGS_HISTORY,
            name: "Earnings History",
            description: "Historical earnings dates and surprise",
            default_width: 3,
            default_height: 2,
        },
        ModuleMeta {
            id: kind::PORTFOLIO_EXPOSURE,
            name: "Portfolio Exposure",
            description: "Exposure by underlying and delta",
            default_width: 3,
            default_height: 2,
        },
        ModuleMeta {
            id: kind::PAYOFF_DIAGRAM,
            name: "Payoff Diagram",
            description: "Option strategy payoff at expiry",
            default_width: 3,
            default_height: 2,
        },
        ModuleMeta {
            id: kind::BACKTEST_EDITOR,
            name: "Backtest Script Editor",
            description: "Write and run backtest scripts",
            default_width: 4,
            default_height: 3,
        },
    ]
}
