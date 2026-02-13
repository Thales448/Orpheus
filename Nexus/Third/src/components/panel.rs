//! Reusable panel: dark slate background, glow border, title, body.

use leptos::*;

#[component]
pub fn Panel(title: &'static str, children: Children) -> impl IntoView {
    view! {
        <div class="panel">
            <div class="panel-header">
                <span class="panel-title">{title}</span>
            </div>
            <div class="panel-body">
                {children()}
            </div>
        </div>
    }
}
