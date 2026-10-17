from dataclasses import dataclass

from bolt.core.events import Event, EventBus


@dataclass(frozen=True, slots=True, eq=False)
class Parent(Event):
    value: int


@dataclass(frozen=True, slots=True, eq=False)
class Child(Parent):
    extra: str = ""


def test_listeners_receive_subclass_events():
    bus = EventBus()
    received = []
    bus.subscribe(Parent, lambda event: received.append(("parent", type(event).__name__)))
    bus.subscribe(Child, lambda event: received.append(("child", type(event).__name__)))
    bus.emit(Child, 1, "x")
    bus.emit(Parent, 2)
    assert received == [("child", "Child"), ("parent", "Child"), ("parent", "Parent")]


def test_subscription_close_and_context_manager():
    bus = EventBus()
    received = []
    with bus.subscribe(Event, received.append):
        bus.dispatch(Parent(1))
    bus.dispatch(Parent(2))
    assert [event.value for event in received] == [1]
    assert not bus.has_listeners(Parent)


def test_emit_without_listeners_does_not_build_events():
    bus = EventBus()

    class Exploding(Event):
        def __init__(self):
            raise AssertionError("should not be constructed")

    bus.emit(Exploding)
    bus.subscribe(Parent, lambda event: None)
    bus.emit(Exploding)


def test_failing_listener_does_not_stop_others(caplog):
    bus = EventBus()
    received = []

    def broken(event):
        raise ValueError("listener bug")

    bus.subscribe(Parent, broken)
    bus.subscribe(Parent, received.append)
    bus.emit(Parent, 3)
    assert len(received) == 1
    assert "listener bug" in caplog.text
