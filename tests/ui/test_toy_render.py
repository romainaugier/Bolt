import pathlib
import sys

from qt_support import wait_until

examples = pathlib.Path(__file__).resolve().parents[2] / "examples"


def test_application_with_toy_renderer(qapp):
    sys.path.insert(0, str(examples))
    try:
        import toy_render_app
    finally:
        sys.path.remove(str(examples))
    application = toy_render_app.make_application()
    application.organization = "BoltTest"
    window = application.build([str(examples / "graphs" / "toy_scene.bolt")])
    window.resize(1200, 800)
    window.show()
    workspace = application.workspace
    document = workspace.current
    graph = document.graph
    render_views = [view for view in window.workbench.all_views() if view.view_type == "toy.render_view"]
    assert render_views
    view = render_views[0]
    render = graph.node("render")
    assert wait_until(lambda: render.session is not None and render.session.stats.updates >= 1
                      and not render.session.stats.rendering, 10)
    assert view.session is render.session
    assert "color" in application.ui.parameter_widgets._factories

    graph.node("moon").set("radius", 0.25)
    assert wait_until(lambda: render.session.stats.last_update == "delta: +0 -0 ~1", 10)
    assert "delta" in view.info.text() or wait_until(lambda: "delta" in view.info.text(), 2)

    window.auto_action.setChecked(False)
    assert document.live.mode.value == "manual"
    window.cook()
    document.undo_stack.setClean()
    window.close()
