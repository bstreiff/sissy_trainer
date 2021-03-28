from sistrum import Event, ValueChangeEvent, IndexValueChangeEvent

class EventSource():
    def __init__(self):
        pass


def test_event():
    event_source = EventSource()

    ev = Event(name="example", source=event_source)

    assert ev.name == "example"
    assert ev.source == event_source


def test_value_change_event():
    event_source = EventSource()

    ev = ValueChangeEvent(name="example", source=event_source, value=42)

    assert ev.name == "example"
    assert ev.source == event_source
    assert ev.value == 42


def test_index_value_change_event():
    event_source = EventSource()

    ev = IndexValueChangeEvent(name="example", source=event_source, index=2, value=42)

    assert ev.name == "example"
    assert ev.source == event_source
    assert ev.index == 2
    assert ev.value == 42

