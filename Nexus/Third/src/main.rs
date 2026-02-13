use leptos::*;
use nexus_third::app::App;

fn main() {
    if let Some(body) = web_sys::window()
        .and_then(|w| w.document())
        .and_then(|d| d.body())
    {
        let _ = body.set_inner_html("");
    }
    mount_to_body(|| view! { <App /> });
}
