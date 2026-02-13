//! Visible debug bar and console logging to diagnose blue-screen / mount issues.

use crate::app::AppLayouts;
use leptos::*;
use leptos_router::use_location;

#[cfg(target_arch = "wasm32")]
pub fn log(s: &str) {
    gloo_console::log!(s);
}

#[cfg(not(target_arch = "wasm32"))]
pub fn log(s: &str) {
    eprintln!("[nexus] {}", s);
}

/// Always-visible debug bar at top of app. Renders inside AppLayoutProvider so context is available.
#[component]
pub fn DebugBar() -> impl IntoView {
    let location = use_location();
    let path = move || location.pathname.get();
    let ctx = use_context::<AppLayouts>();
    let modules_count = move || {
        ctx.map(|l| l.symbol.get().modules.len() + l.options.get().modules.len())
            .unwrap_or(0)
    };

    view! {
        <div class="debug-bar">
            <span class="debug-label">DEBUG</span>
            <span class="debug-path">path: {path}</span>
            <span class="debug-ctx">ctx: {move || if ctx.is_some() { "ok" } else { "MISSING" } }</span>
            <span class="debug-modules">modules: {modules_count}</span>
        </div>
    }
}
