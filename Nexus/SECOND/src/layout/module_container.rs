use crate::layout::workspace::WorkspaceLayoutState;
use crate::models::{GridSize, PlacedModule};
use leptos::*;
use std::cell::RefCell;
use std::rc::Rc;
use wasm_bindgen::closure::Closure;
use wasm_bindgen::JsCast;
use web_sys::MouseEvent;

/// Approximate px per grid unit for resize delta.
const PX_PER_COL: f64 = 56.0;
const PX_PER_ROW: f64 = 48.0;

#[component]
pub fn ModuleContainer(
    placed: PlacedModule,
    layout: RwSignal<WorkspaceLayoutState>,
    children: Children,
) -> impl IntoView {
    let id = placed.id;
    let resize_handle_ref = NodeRef::<html::Div>::new();

    let (resize_session, set_resize_session) = create_signal(None::<ResizeSession>);

    let on_remove = move |_| {
        layout.update(|s| {
            s.modules.retain(|m| m.id != id);
        });
    };

    // Attach native mousedown to the resize handle when it mounts (guarantees real MouseEvent)
    let layout_for_load = layout;
    let id_for_load = id;
    let set_resize_session_load = set_resize_session;
    let resize_session_load = resize_session;
    resize_handle_ref.on_load(move |el| {
        let layout = layout_for_load;
        let id = id_for_load;
        let set_resize_session = set_resize_session_load;
        let resize_session = resize_session_load;

        let closure = Closure::wrap(Box::new(move |ev: MouseEvent| {
            ev.prevent_default();
            ev.stop_propagation();
            let (w, h) = layout
                .get()
                .modules
                .iter()
                .find(|m| m.id == id)
                .map(|m| (m.size.w, m.size.h))
                .unwrap_or((2, 2));
            set_resize_session.set(Some(ResizeSession {
                start_x: ev.client_x() as f64,
                start_y: ev.client_y() as f64,
                start_w: w,
                start_h: h,
            }));

            let layout = layout;
            let resize_session = resize_session;
            let set_resize_session = set_resize_session;
            let holder: Rc<RefCell<Option<(Closure<dyn FnMut(MouseEvent)>, Closure<dyn FnMut(MouseEvent)>)>>> =
                Rc::new(RefCell::new(None));

            let holder_up = holder.clone();
            let move_cl = Closure::wrap(Box::new(move |ev: MouseEvent| {
                if let Some(session) = resize_session.get() {
                    let dx = (ev.client_x() as f64 - session.start_x) / PX_PER_COL;
                    let dy = (ev.client_y() as f64 - session.start_y) / PX_PER_ROW;
                    let new_w = (session.start_w as i32 + dx.round() as i32).max(1).min(12) as u32;
                    let new_h = (session.start_h as i32 + dy.round() as i32).max(1).min(8) as u32;
                    layout.update(|s| {
                        s.resize_module(id, GridSize { w: new_w, h: new_h });
                    });
                }
            }) as Box<dyn FnMut(MouseEvent)>);

            let up_cl = Closure::wrap(Box::new(move |_ev: MouseEvent| {
                set_resize_session.set(None);
                if let Some(w) = web_sys::window() {
                    if let Some((ref move_c, ref up_c)) = holder_up.borrow_mut().take() {
                        let _ = w.remove_event_listener_with_callback("mousemove", move_c.as_ref().unchecked_ref());
                        let _ = w.remove_event_listener_with_callback("mouseup", up_c.as_ref().unchecked_ref());
                    }
                }
            }) as Box<dyn FnMut(MouseEvent)>);

            if let Some(w) = web_sys::window() {
                let _ = w.add_event_listener_with_callback("mousemove", move_cl.as_ref().unchecked_ref());
                let _ = w.add_event_listener_with_callback("mouseup", up_cl.as_ref().unchecked_ref());
            }
            holder.borrow_mut().replace((move_cl, up_cl));
        }) as Box<dyn FnMut(MouseEvent)>);

        let _ = (&*el).add_event_listener_with_callback("mousedown", closure.as_ref().unchecked_ref());
        closure.forget();
    });

    view! {
        <div
            class="module-container"
            style=move || {
                let s = layout.get();
                let Some(m) = s.modules.iter().find(|x| x.id == id) else { return String::new(); };
                format!(
                    "grid-column: {} / span {}; grid-row: {} / span {};",
                    m.position.col + 1,
                    m.size.w,
                    m.position.row + 1,
                    m.size.h,
                )
            }
            data-id=placed.id.0
        >
            <div class="module-container-inner">
                <header class="module-header">
                    <span class="module-drag-handle" title="Drag to move">::</span>
                    <span class="module-title">{placed.kind.replace('_', " ")}</span>
                    <button
                        type="button"
                        class="module-remove"
                        on:click=on_remove
                        title="Remove module"
                    >
                        { "x" }
                    </button>
                </header>
                <div class="module-body">
                    {children()}
                </div>
            </div>
            <div
                ref=resize_handle_ref
                class="resize-handle resize-handle-se"
                title="Drag to resize"
                role="button"
                tabindex="0"
            >
                <span class="resize-handle-icon" aria-hidden="true">&#x231f;</span>
            </div>
        </div>
    }
}

#[derive(Clone)]
struct ResizeSession {
    start_x: f64,
    start_y: f64,
    start_w: u32,
    start_h: u32,
}
