use leptos::*;
use nexus_workspace::app::App;
use nexus_workspace::debug;

fn main() {
    debug::log("main: mounting to body");
    // Clear static "Loading Nexus..." so the Leptos app is visible (mount_to_body appends, it doesn't replace)
    if let Some(body) = web_sys::window()
        .and_then(|w| w.document())
        .and_then(|d| d.body())
    {
        let _ = body.set_inner_html("");
    }
    mount_to_body(|| {
        debug::log("main: App view closure running");
        view! { <App /> }
    });
    debug::log("main: mount_to_body returned");
}
