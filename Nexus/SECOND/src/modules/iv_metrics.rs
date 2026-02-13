use leptos::*;

#[component]
pub fn IvMetrics() -> impl IntoView {
    let iv_current = 0.28;
    let iv_rank = 42;
    let iv_percentile = 55;
    let term_structure = vec![
        ("1W", 0.32),
        ("2W", 0.30),
        ("1M", 0.28),
        ("2M", 0.26),
        ("3M", 0.25),
    ];

    view! {
        <div class="iv-metrics-module">
            <div class="iv-metric-row">
                <span class="iv-label">IV (30d)</span>
                <span class="iv-value">{format!("{:.1}%", iv_current * 100.0)}</span>
            </div>
            <div class="iv-metric-row">
                <span class="iv-label">IV Rank</span>
                <span class="iv-value">{iv_rank}%</span>
            </div>
            <div class="iv-metric-row">
                <span class="iv-label">IV Percentile</span>
                <span class="iv-value">{iv_percentile}%</span>
            </div>
            <div class="iv-term-structure">
                <div class="iv-term-title">Term structure</div>
                {term_structure.into_iter().map(|(term, val)| {
                    view! {
                        <div class="iv-term-row">
                            <span>{term}</span>
                            <span>{format!("{:.1}%", val * 100.0)}</span>
                        </div>
                    }
                }).collect_view()}
            </div>
        </div>
    }
}
