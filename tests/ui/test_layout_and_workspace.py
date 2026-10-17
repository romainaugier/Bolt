import threading

from PySide6.QtCore import QThread, Qt
from qt_support import pump, wait_until

from bolt.core import events
from bolt.core.events import EventBus
from bolt.ui.events import CurrentDocumentChanged, CurrentGraphChanged, DocumentStateChanged, SelectionChanged
from bolt.ui.layout import Pane, Workbench
from bolt.ui.qt import Dispatcher, EventRelay
from bolt.ui.views import View, ViewRegistry


class DummyView(View):
    view_type = "dummy"
    label = "Dummy"
    closed = 0

    def __init__(self, workspace, parent=None):
        super().__init__(workspace, parent)
        self.state = {}

    def save_state(self):
        return dict(self.state)

    def restore_state(self, state):
        self.state = dict(state)

    def close_view(self):
        DummyView.closed += 1
        super().close_view()


class OtherView(DummyView):
    view_type = "other"
    label = "Other"


def make_workbench(workspace):
    views = ViewRegistry()
    views.register(DummyView)
    views.register(OtherView)
    workbench = Workbench(workspace, views)
    workbench.resize(800, 600)
    workbench.show()
    return workbench


def test_split_close_and_serialize(workspace):
    workbench = make_workbench(workspace)
    root = workbench.root
    assert isinstance(root, Pane)
    root.add_view("dummy", {"zoom": 2})
    right = root.split(Qt.Horizontal)
    assert right.current_view().view_type == "dummy"
    right.add_view("other")
    below = right.split(Qt.Vertical)
    third = right.split(Qt.Vertical)
    assert workbench.pane_count() == 4
    data = workbench.to_dict()
    assert data["type"] == "split" and data["orientation"] == "horizontal"
    assert data["children"][1]["orientation"] == "vertical" and len(data["children"][1]["children"]) == 3

    workbench.close_pane(third)
    workbench.close_pane(below)
    assert workbench.pane_count() == 2
    assert workbench.to_dict()["children"][1]["type"] == "pane"

    workbench.restore(data)
    assert workbench.pane_count() == 4
    restored = workbench.panes()[0].views()[0]
    assert restored.state == {"zoom": 2}
    assert workbench.to_dict()["children"][1]["children"][0]["views"][1]["view"] == "other"


def test_closing_last_view_closes_pane_but_keeps_root(workspace):
    workbench = make_workbench(workspace)
    root = workbench.root
    root.add_view("dummy")
    other = root.split(Qt.Horizontal)
    other.close_view(0)
    pump()
    assert workbench.pane_count() == 1
    before = DummyView.closed
    workbench.close_pane(workbench.root)
    assert workbench.pane_count() == 1 and not workbench.root.views()
    assert DummyView.closed == before + 1


def test_unknown_views_are_skipped(workspace):
    workbench = make_workbench(workspace)
    workbench.restore({"type": "pane", "views": [{"view": "missing"}, {"view": "dummy"}]})
    assert [view.view_type for view in workbench.root.views()] == ["dummy"]


def test_tab_reordering_keeps_views_in_sync(workspace):
    workbench = make_workbench(workspace)
    pane = workbench.root
    first = pane.add_view("dummy")
    second = pane.add_view("other")
    pane.tabs.moveTab(1, 0)
    assert pane.views() == [second, first]


def test_relay_moves_events_to_gui_thread(qapp):
    source, target = EventBus(), EventBus()
    relay = EventRelay(source, target, coalesce=(events.NodeProgress,))
    received = []
    target.subscribe(events.Event, lambda event: received.append((type(event).__name__,
                                                                  QThread.currentThread() is qapp.thread())))

    def worker():
        for index in range(50):
            source.dispatch(events.NodeProgress(None, "node", index / 50))
        source.dispatch(events.NodeCooked(None, "node", 0.1))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    assert wait_until(lambda: any(name == "NodeCooked" for name, _ in received))
    pump(0.1)
    assert all(in_gui for _, in_gui in received)
    progress = [name for name, _ in received if name == "NodeProgress"]
    assert 1 <= len(progress) < 50
    relay.close()


def test_dispatcher_runs_on_gui_thread(qapp):
    dispatcher = Dispatcher()
    threads = []
    worker = threading.Thread(target=lambda: dispatcher.call_soon(
        lambda: threads.append(QThread.currentThread() is qapp.thread())))
    worker.start()
    worker.join()
    assert wait_until(lambda: threads == [True])


def test_workspace_documents_and_navigation(workspace, tmp_path):
    received = []
    workspace.events.subscribe(CurrentDocumentChanged, lambda event: received.append("document"))
    workspace.events.subscribe(CurrentGraphChanged, lambda event: received.append("graph"))
    workspace.events.subscribe(SelectionChanged, lambda event: received.append(("selection", len(event.nodes))))
    workspace.events.subscribe(DocumentStateChanged, lambda event: received.append("state"))
    first = workspace.new_document("first")
    graph = first.graph
    sub = graph.create_node("bolt.subgraph")
    workspace.select([sub])
    workspace.set_current_graph(sub.subgraph)
    assert first.current_graph is sub.subgraph and first.selection == ()
    second = workspace.new_document("second")
    assert workspace.current is second
    workspace.set_current_graph(sub.subgraph)
    assert workspace.current is first

    from bolt.ui.commands import create_node_command
    first.push(create_node_command(first, graph, "values.int"))
    assert first.modified
    path = tmp_path / "first.bolt"
    first.save(str(path))
    assert not first.modified and first.name == "first"
    assert workspace.open(str(path)) is first

    workspace.close_document(first)
    assert workspace.current is second
    reopened = workspace.open(str(path))
    assert reopened is not first and reopened.graph.find_node("subgraph") is not None
    assert "graph" in received and ("selection", 1) in received and "state" in received


def test_graph_events_from_cooks_reach_workspace_bus(workspace, document):
    cooked = []
    workspace.events.subscribe(events.NodeCooked, lambda event: cooked.append(
        (event.node.name, QThread.currentThread() is workspace.thread())))
    document.graph.create_node("values.int", "value")
    document.live.cook()
    assert wait_until(lambda: cooked == [("value", True)])


def test_submit_job(workspace, document):
    from bolt.core.jobs import JobStatus
    document.graph.create_node("values.int", "value").displayed = True
    job = workspace.submit_job()
    assert job.targets == ["value"]
    assert job.wait(30) and job.status is JobStatus.succeeded
