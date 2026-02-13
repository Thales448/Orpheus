use crate::debug::{self, DebugBar};
use crate::layout::workspace::WorkspaceLayoutState;
use crate::pages::{BacktestWorkspace, OptionsWorkspace, PortfolioWorkspace, StockPage};
use leptos::*;
use leptos_router::*;

/// Layout state for each workspace tab; provided via context so Route can use zero-arg components.
#[derive(Clone, Copy)]
pub struct AppLayouts {
    pub symbol: RwSignal<WorkspaceLayoutState>,
    pub options: RwSignal<WorkspaceLayoutState>,
    pub portfolio: RwSignal<WorkspaceLayoutState>,
    pub backtest: RwSignal<WorkspaceLayoutState>,
}

#[component]
pub fn App() -> impl IntoView {
    let symbol_layout = RwSignal::new(WorkspaceLayoutState::new());
    let options_layout = RwSignal::new(WorkspaceLayoutState::new());
    let portfolio_layout = RwSignal::new(WorkspaceLayoutState::new());
    let backtest_layout = RwSignal::new(WorkspaceLayoutState::new());

    let layouts = AppLayouts {
        symbol: symbol_layout,
        options: options_layout,
        portfolio: portfolio_layout,
        backtest: backtest_layout,
    };

    let edit_mode = RwSignal::new(false);

    debug::log("App: rendering");

    view! {
        <Router>
            <AppLayoutProvider layouts=layouts edit_mode=edit_mode>
                <DebugBar />
                <div class="app-root">
                    <nav class="nav-tabs">
                        <A href="/" exact=true class="nav-tab" active_class="active">Symbol</A>
                        <A href="/options" class="nav-tab" active_class="active">Options</A>
                        <A href="/portfolio" class="nav-tab" active_class="active">Portfolio</A>
                        <A href="/backtest" class="nav-tab" active_class="active">Backtest</A>
                        <button
                            type="button"
                            class="nav-tab edit-mode-toggle"
                            class:active=move || edit_mode.get()
                            on:click=move |_| edit_mode.update(|v| *v = !*v)
                            title="Show/hide module library"
                        >
                            {move || if edit_mode.get() { "Edit ✓" } else { "Edit" } }
                        </button>
                    </nav>
                    <div class="app-content">
                        <Routes>
                            <Route path="/" view=StockPage/>
                            <Route path="/options" view=OptionsWorkspace/>
                            <Route path="/portfolio" view=PortfolioWorkspace/>
                            <Route path="/backtest" view=BacktestWorkspace/>
                        </Routes>
                    </div>
                </div>
            </AppLayoutProvider>
        </Router>
    }
}

#[component]
fn AppLayoutProvider(layouts: AppLayouts, edit_mode: RwSignal<bool>, children: Children) -> impl IntoView {
    debug::log("AppLayoutProvider: providing context");
    provide_context(layouts);
    provide_context(edit_mode);
    children()
}
