//! Stock (Symbol) dashboard: selected stock, main price chart, historical metrics,
//! momentum gauges (Sell/Hold/Buy), and trends.

use crate::charts::{PriceChart, PricePoint, SignalGauge};
use leptos::*;

const SELECTED_SYMBOL: &str = "AAPL";

struct HistoricalMetrics {
    price_now: f64,
    change_1d: f64,
    change_1d_pct: f64,
    high_52w: f64,
    low_52w: f64,
    return_1y_pct: f64,
    volatility_30d: f64,
    avg_volume: u64,
    market_cap_b: f64,
}

fn mock_historical_metrics() -> HistoricalMetrics {
    HistoricalMetrics {
        price_now: 228.45,
        change_1d: 2.31,
        change_1d_pct: 1.02,
        high_52w: 237.23,
        low_52w: 164.08,
        return_1y_pct: 28.5,
        volatility_30d: 0.22,
        avg_volume: 52_000_000,
        market_cap_b: 3520.0,
    }
}

/// Main price series for the chart (customizable later: add overlays for support, GEX, channels).
fn mock_chart_series() -> Vec<PricePoint> {
    let raw = [
        ("Jan", 185.2),
        ("Feb", 188.1),
        ("Mar", 175.5),
        ("Apr", 169.0),
        ("May", 189.2),
        ("Jun", 214.2),
        ("Jul", 218.5),
        ("Aug", 225.1),
        ("Sep", 222.0),
        ("Oct", 228.45),
    ];
    raw.iter()
        .map(|(label, value)| PricePoint {
            label: label.to_string(),
            value: *value,
        })
        .collect()
}

/// Mock trend summary.
struct TrendSummary {
    short_term: &'static str,
    short_strength: u8,
    medium_term: &'static str,
    medium_strength: u8,
    long_term: &'static str,
}

fn mock_trends() -> TrendSummary {
    TrendSummary {
        short_term: "Bullish",
        short_strength: 72,
        medium_term: "Bullish",
        medium_strength: 65,
        long_term: "Bullish",
    }
}

/// Momentum gauge config: title and value in [-1, 1]. You can wire your indicators here later.
struct GaugeConfig {
    title: &'static str,
    value: f64,
}

fn mock_gauges() -> Vec<GaugeConfig> {
    vec![
        GaugeConfig { title: "RSI", value: 0.24 },       // map RSI 62 -> ~0.24
        GaugeConfig { title: "MACD", value: 0.5 },
        GaugeConfig { title: "Stochastic", value: -0.2 },
        GaugeConfig { title: "ADX", value: 0.6 },
        GaugeConfig { title: "Williams %R", value: 0.1 },
    ]
}

#[component]
pub fn StockPage() -> impl IntoView {
    let metrics = mock_historical_metrics();
    let chart_series = mock_chart_series();
    let trends = mock_trends();
    let gauges = mock_gauges();

    // Empty overlays for now; add support levels, GEX, trend channels later.
    let overlays: Vec<crate::charts::ChartOverlay> = vec![];

    view! {
        <div class="stock-page">
            <header class="stock-header">
                <h1 class="stock-symbol">{SELECTED_SYMBOL}</h1>
                <p class="stock-name">Apple Inc.</p>
                <div class="stock-price-block">
                    <span class="stock-price">{format!("${:.2}", metrics.price_now)}</span>
                    <span class=move || { if metrics.change_1d >= 0.0 { "stock-change up" } else { "stock-change down" } }>
                        {if metrics.change_1d >= 0.0 { "+" } else { "" }}{format!("${:.2}", metrics.change_1d)} ({format!("{:.2}%", metrics.change_1d_pct)})
                    </span>
                </div>
            </header>

            <section class="stock-main-chart panel">
                <h2 class="panel-title">Price</h2>
                <p class="panel-hint">Chart is customizable: add support levels, GEX levels, trend channels via overlays later.</p>
                <PriceChart series=chart_series overlays=overlays />
            </section>

            <section class="stock-gauges panel">
                <h2 class="panel-title">Momentum signals (Sell / Hold / Buy)</h2>
                <p class="panel-hint">Indicators to be defined later; values in [-1, 1] map to needle position.</p>
                <div class="gauges-grid">
                    {gauges.into_iter().map(|g| {
                        view! {
                            <SignalGauge title=g.title.to_string() value=g.value />
                        }
                    }).collect_view()}
                </div>
            </section>

            <section class="stock-metrics panel">
                <h2 class="panel-title">Historical metrics</h2>
                <div class="metrics-grid">
                    <div class="metric">
                        <span class="metric-label">52W high</span>
                        <span class="metric-value">{format!("${:.2}", metrics.high_52w)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">52W low</span>
                        <span class="metric-value">{format!("${:.2}", metrics.low_52w)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">1Y return</span>
                        <span class="metric-value up">{format!("{:.1}%", metrics.return_1y_pct)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">30D vol (ann.)</span>
                        <span class="metric-value">{format!("{:.0}%", metrics.volatility_30d * 100.0)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Avg volume</span>
                        <span class="metric-value">{format!("{:.1}M", metrics.avg_volume as f64 / 1e6)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Market cap</span>
                        <span class="metric-value">{format!("${:.1}B", metrics.market_cap_b)}</span>
                    </div>
                </div>
            </section>

            <section class="stock-trends panel">
                <h2 class="panel-title">Trends</h2>
                <div class="trends-list">
                    <div class="trend-row">
                        <span class="trend-label">Short-term (2W)</span>
                        <span class="trend-value">{trends.short_term}</span>
                        <div class="trend-bar-wrap">
                            <div class="trend-bar" style=format!("width: {}%", trends.short_strength)></div>
                        </div>
                        <span class="trend-pct">{trends.short_strength}%</span>
                    </div>
                    <div class="trend-row">
                        <span class="trend-label">Medium-term (3M)</span>
                        <span class="trend-value">{trends.medium_term}</span>
                        <div class="trend-bar-wrap">
                            <div class="trend-bar" style=format!("width: {}%", trends.medium_strength)></div>
                        </div>
                        <span class="trend-pct">{trends.medium_strength}%</span>
                    </div>
                    <div class="trend-row">
                        <span class="trend-label">Long-term (1Y)</span>
                        <span class="trend-value">{trends.long_term}</span>
                        <div class="trend-bar-wrap">
                            <div class="trend-bar" style="width: 100%"></div>
                        </div>
                        <span class="trend-pct">100%</span>
                    </div>
                </div>
            </section>
        </div>
    }
}
