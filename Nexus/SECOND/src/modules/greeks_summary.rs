use leptos::*;

#[component]
pub fn GreeksSummary() -> impl IntoView {
    let greeks = vec![
        ("Delta", 0.52, ""),
        ("Gamma", 0.03, ""),
        ("Theta", -0.08, "/day"),
        ("Vega", 0.12, "/1%"),
    ];

    view! {
        <div class="greeks-summary-module">
            {greeks.into_iter().map(|(name, value, unit)| {
                view! {
                    <div class="greek-row">
                        <span class="greek-name">{name}</span>
                        <span class="greek-value">{format!("{:.2}{}", value, unit)}</span>
                    </div>
                }
            }).collect_view()}
        </div>
    }
}
