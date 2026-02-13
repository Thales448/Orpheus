mod backtest_editor;
mod earnings_history;
mod greeks_summary;
mod iv_metrics;
mod options_chain;
mod payoff_diagram;
mod portfolio_exposure;
mod price_chart;

use crate::layout::workspace::WorkspaceLayoutState;
use crate::models::PlacedModule;
use leptos::*;

pub use backtest_editor::BacktestEditor;
pub use earnings_history::EarningsHistory;
pub use greeks_summary::GreeksSummary;
pub use iv_metrics::IvMetrics;
pub use options_chain::OptionsChain;
pub use payoff_diagram::PayoffDiagram;
pub use portfolio_exposure::PortfolioExposure;
pub use price_chart::PriceChart;

use crate::layout::ModuleContainer;

/// Renders a placed module by kind (registry). Used by workspace pages.
#[component]
pub fn RenderModule(
    placed: PlacedModule,
    layout: RwSignal<WorkspaceLayoutState>,
) -> impl IntoView {
    let kind = placed.kind.clone();
    view! {
        <ModuleContainer placed=placed layout=layout>
            {match kind.as_str() {
                crate::models::modules::kind::PRICE_CHART => view! { <PriceChart /> }.into_view(),
                crate::models::modules::kind::IV_METRICS => view! { <IvMetrics /> }.into_view(),
                crate::models::modules::kind::OPTIONS_CHAIN => view! { <OptionsChain /> }.into_view(),
                crate::models::modules::kind::GREEKS_SUMMARY => view! { <GreeksSummary /> }.into_view(),
                crate::models::modules::kind::EARNINGS_HISTORY => view! { <EarningsHistory /> }.into_view(),
                crate::models::modules::kind::PORTFOLIO_EXPOSURE => view! { <PortfolioExposure /> }.into_view(),
                crate::models::modules::kind::PAYOFF_DIAGRAM => view! { <PayoffDiagram /> }.into_view(),
                crate::models::modules::kind::BACKTEST_EDITOR => view! { <BacktestEditor /> }.into_view(),
                _ => view! { <span>Unknown module: {kind}</span> }.into_view(),
            }}
        </ModuleContainer>
    }
}
