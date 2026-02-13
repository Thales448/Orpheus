//! App shell: top bar (logo + name), left nav tree, main content.

use crate::pages::*;
use crate::state::AppState;
use leptos::*;
use leptos_router::*;

#[component]
pub fn App() -> impl IntoView {
    let state = RwSignal::new(AppState::default());
    provide_context(state);

    view! {
        <Router>
            <div class="app-root">
                <header class="top-bar">
                    <img src="/public/logo.png" alt="SYNTX" class="top-bar-logo"/>
                    <h1 class="top-bar-title">SYNTX Quant Dashboard</h1>
                </header>
                <div class="app-body">
                    <nav class="side-nav">
                        <NavTree />
                    </nav>
                    <main class="main-content">
                        <Routes>
                            <Route path="/" view=DashboardPage/>
                            <Route path="/symbol" view=SymbolResearchPage/>
                            <Route path="/options" view=OptionsAnalysisPage/>
                            <Route path="/portfolio" view=PortfolioMetricsPage/>
                            <Route path="/backtest" view=BacktestingLabPage/>
                            <Route path="/settings" view=SettingsPage/>
                        </Routes>
                    </main>
                </div>
            </div>
        </Router>
    }
}

/// Left-side navigation tree. Structure supports adding children under each main tab later.
#[component]
fn NavTree() -> impl IntoView {
    view! {
        <ul class="nav-tree">
            <li class="nav-tree-item">
                <A href="/" exact=true class="nav-tree-link" active_class="active">Dashboard</A>
            </li>
            <li class="nav-tree-item">
                <A href="/symbol" class="nav-tree-link" active_class="active">Symbol Research</A>
            </li>
            <li class="nav-tree-item">
                <A href="/options" class="nav-tree-link" active_class="active">Options Analysis</A>
            </li>
            <li class="nav-tree-item">
                <A href="/portfolio" class="nav-tree-link" active_class="active">Portfolio Metrics</A>
            </li>
            <li class="nav-tree-item">
                <A href="/backtest" class="nav-tree-link" active_class="active">Backtesting Lab</A>
            </li>
            <li class="nav-tree-item">
                <A href="/settings" class="nav-tree-link" active_class="active">Settings</A>
            </li>
        </ul>
    }
}
