use crate::app::AppLayouts;
use crate::layout::{ModuleLibrary, Workspace};
use crate::modules::RenderModule;
use leptos::*;

#[component]
pub fn BacktestWorkspace() -> impl IntoView {
    let layouts = use_context::<AppLayouts>().expect("AppLayouts provided");
    let edit_mode = use_context::<RwSignal<bool>>().expect("edit_mode provided");
    let layout = layouts.backtest;
    view! {
        <div class="app-shell">
            {move || edit_mode.get().then(|| view! { <ModuleLibrary layout=layout /> })}
            <main class="app-main">
                <Workspace layout=layout>
                    {move || {
                        layout.get().modules.iter().map(|placed| {
                            view! {
                                <RenderModule
                                    placed=placed.clone()
                                    layout=layout
                                />
                            }
                        }).collect_view()
                    }}
                </Workspace>
            </main>
        </div>
    }
}
