use leptos::*;

/// Mock OHLC data point.
#[derive(Clone)]
struct Candle {
    date: &'static str,
    open: f64,
    high: f64,
    low: f64,
    close: f64,
}

#[component]
pub fn PriceChart() -> impl IntoView {
    let candles = vec![
        Candle { date: "Mon", open: 148.2, high: 151.0, low: 147.5, close: 150.3 },
        Candle { date: "Tue", open: 150.3, high: 152.1, low: 149.0, close: 151.2 },
        Candle { date: "Wed", open: 151.2, high: 153.5, low: 150.1, close: 152.8 },
        Candle { date: "Thu", open: 152.8, high: 154.0, low: 151.5, close: 152.0 },
        Candle { date: "Fri", open: 152.0, high: 153.2, low: 150.8, close: 152.5 },
    ];
    let last = candles.last().map(|c| c.close).unwrap_or(0.0);
    let change = candles.first().map(|c| last - c.open).unwrap_or(0.0);
    #[allow(unused_variables)]
    let pct = candles.first().map(|c| (change / c.open) * 100.0).unwrap_or(0.0);

    view! {
        <div class="price-chart-module">
            <div class="price-chart-header">
                <span class="price-chart-symbol">AAPL</span>
                <span class="price-chart-price">{format!("{:.2}", last)}</span>
                <span class=move || { if change >= 0.0 { "price-chart-change up" } else { "price-chart-change down" } }>
                    {if change >= 0.0 { "+" } else { "" }}{format!("{:.2}", change)} ({format!("{:.2}%", pct)})
                </span>
            </div>
            <div class="price-chart-placeholder">
                <div class="price-chart-bars">
                    {candles.iter().enumerate().map(|(i, c)| {
                        let height_pct = ((c.close - 147.0) / 7.0 * 60.0 + 20.0).min(95.0).max(5.0);
                        let series_class = format!("price-bar series-{}", i % 5);
                        view! {
                            <div class="price-bar-wrap" key=i>
                                <div
                                    class=series_class
                                    style=format!("height: {}%;", height_pct)
                                    title=format!("O:{} H:{} L:{} C:{}", c.open, c.high, c.low, c.close)
                                ></div>
                            </div>
                        }
                    }).collect_view()}
                </div>
                <div class="price-chart-labels">
                    {candles.iter().map(|c| view! { <span>{c.date}</span> }).collect_view()}
                </div>
            </div>
        </div>
    }
}
