use leptos::*;

#[derive(Clone)]
struct ExposureRow {
    symbol: &'static str,
    delta: f64,
    notional: f64,
    pct: f64,
}

#[component]
pub fn PortfolioExposure() -> impl IntoView {
    let rows = vec![
        ExposureRow { symbol: "AAPL", delta: 120.5, notional: 18_500.0, pct: 42.0 },
        ExposureRow { symbol: "MSFT", delta: 85.0, notional: 32_100.0, pct: 28.0 },
        ExposureRow { symbol: "GOOGL", delta: -15.2, notional: -2_200.0, pct: -5.0 },
    ];
    let total_delta: f64 = rows.iter().map(|r| r.delta).sum();
    let total_notional: f64 = rows.iter().map(|r| r.notional).sum();

    view! {
        <div class="portfolio-exposure-module">
            <div class="exposure-summary">
                <div class="exposure-total">
                    <span class="exposure-label">Net Delta</span>
                    <span class="exposure-value">{format!("{:.1}", total_delta)}</span>
                </div>
                <div class="exposure-total">
                    <span class="exposure-label">Notional</span>
                    <span class="exposure-value">{format!("${:.0}", total_notional)}</span>
                </div>
            </div>
            <div class="exposure-list">
                {rows.into_iter().map(|r| {
                    view! {
                        <div class="exposure-row">
                            <span class="exposure-symbol">{r.symbol}</span>
                            <span class="exposure-delta">{format!("{:.1}", r.delta)}</span>
                            <span class="exposure-pct">{format!("{:.0}%", r.pct)}</span>
                        </div>
                    }
                }).collect_view()}
            </div>
        </div>
    }
}
