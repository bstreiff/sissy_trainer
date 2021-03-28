from typing import Any, Callable, Text, Mapping, Optional, Iterable
import re
import collections.abc

__all__ = [
    "Event",
    "ValueChangeEvent",
    "IndexValueChangeEvent",
    "ValueConverter",
    "BasicValueConverter",
    "EnumValueConverter",
    "EventProperty",
    "generic_event_property",
]


def _is_sphinx_build() -> bool:
    """Are we currently generating documentation in Sphinx?"""

    try:
        if __sphinx_build__:  # type: ignore[name-defined]
            return __sphinx_build__  # type: ignore[name-defined]
        else:
            return False
    except NameError:
        return False


class Event:
    """\
    Parent class for all events.
    """

    __slots__ = ("name", "source")

    name: str
    source: Any

    def __init__(self, name: str, source: Any):
        #: The name of this event.
        self.name = name
        #: The source of the event.
        self.source = source


class ValueChangeEvent(Event):
    """\
    Event class for all events indicating a property value change.
    """

    __slots__ = ("value",)

    value: Any

    def __init__(self, name: str, source: Any, value: Any):
        super().__init__(name=name, source=source)
        #: The updated value
        self.value = value


class IndexValueChangeEvent(ValueChangeEvent):
    """\
    Event class for all events indicating a property value change.
    """

    __slots__ = ("index",)

    index: int

    def __init__(self, name: str, source: Any, value: Any, index: int):
        super().__init__(name=name, source=source, value=value)
        #: The updated value
        self.index = index


# TODO: This interface is not great.
#       Is there something we can do to replace it? That might also work with primitive types?
#       a bool's __str__ returns 'True' or 'False' and not a number :/


class ValueConverter:
    def to_api(self, obj: str) -> Any:
        """Convert a string sequence from the serial protocol into an API-visible value."""
        # pylint: disable=unused-argument
        return None

    def to_raw(self, obj) -> str:
        """Convert an API-visible value into a raw string suitable for transmission."""
        # pylint: disable=unused-argument
        return ""


class BasicValueConverter(ValueConverter):
    def __init__(self, prim_type):
        self.prim_type = prim_type

    def to_api(self, obj: str) -> Any:
        return self.prim_type(obj)

    def to_raw(self, obj) -> str:
        return "{0:d}".format(obj)


_BOOL_VALUE_CONVERTER = BasicValueConverter(bool)
_INT_VALUE_CONVERTER = BasicValueConverter(int)


class EnumValueConverter(ValueConverter):
    def __init__(self, mapping: Mapping[str, Any]):
        self.mapping = mapping
        self.prim_type = next(iter(mapping.values())).__class__

    def to_api(self, obj: str) -> Any:
        return self.mapping[obj]

    def to_raw(self, obj) -> str:
        for key, val in self.mapping.items():
            if val == obj:
                return key
        raise ValueError("Unable to find match for {0}".format(obj))


# The main EventProperty container. This is a `property`, but also contains
# an additional `fmatch` field for a Callable for checking that an input
# line matches an event occurrance.
#
# (Note: This comment is not a docstring, because we want to override the
#        docstring at each individual instance.)
class EventProperty(property):
    def __init__(
        self,
        fget: Optional[Callable[[Any], Any]] = None,
        fset: Optional[Callable[[Any, Any], None]] = None,
        fmatch: Optional[Callable[[Any, str], Optional[Event]]] = None,
        doc: Optional[Text] = None,
    ):
        super().__init__(fget=fget, fset=fset, fdel=None, doc=doc)
        self.fmatch = fmatch
        if doc is None and fget is not None:
            doc = fget.__doc__
        self.__doc__ = doc

    def matcher(self, fmatch):
        return type(self)(self.fget, self.fset, fmatch, self.__doc__)


class _ArrayEventProperty(collections.abc.Mapping):
    def __init__(
        self,
        parent: Any,
        indices: Iterable,
        fgetitem: Optional[Callable[[Any, Any], Any]] = None,
        fsetitem: Optional[Callable[[Any, Any, Any], None]] = None,
    ):
        self._parent = parent
        self._indices = indices
        self._fgetitem = fgetitem
        self._fsetitem = fsetitem

    def __getitem__(self, index):
        if index not in self._indices:
            raise IndexError("invalid index")
        return self._fgetitem(self._parent, index)

    def __setitem__(self, index, value):
        if index not in self._indices:
            raise IndexError("invalid index")
        self._fsetitem(self._parent, index, value)

    def __len__(self):
        return self._indices.__len__()

    def __iter__(self):
        return self._indices.__iter__()

    def __contains__(self, item):
        return self._indices.__contains__(item)


def _make_getter(doc, type_converter, get_cmd):
    if get_cmd is None:
        return None

    def getter(self):
        return type_converter.to_api(self.make_request(get_cmd))

    getter.__doc__ = doc
    getter.__annotations__ = {"return": type_converter.prim_type}

    return getter


def _make_doconly_getter(doc):
    # Hack for documentation purposes; sphinx looks only at 'fget' for docstring
    # and type, but we're creating a goofy "property" that has no getter nor setter.
    # So if we're running in sphinx, create a dummy 'fget' to satisfy this.
    fake_fget: Optional[Callable[[Any], None]]
    if _is_sphinx_build():

        def fake_fget(self) -> None:
            # pylint: disable=unused-argument,function-redefined
            pass

        fake_fget.__doc__ = doc
    else:
        fake_fget = None

    return fake_fget


def _make_setter(doc, type_converter, set_cmd):
    if set_cmd is None:
        return None

    def setter(self, value):
        self.make_request(set_cmd.format(type_converter.to_raw(value)))

    setter.__doc__ = doc

    return setter


def _make_getitemmer(doc, type_converter, get_cmd):
    if get_cmd is None:
        return None

    def getitemmer(self, index):
        return type_converter.to_api(self.make_request(get_cmd.format(index=index)))

    getitemmer.__doc__ = doc
    getitemmer.__annotations__ = {"return": type_converter.prim_type}

    return getitemmer


def _make_setitemmer(doc, type_converter, set_cmd):
    if set_cmd is None:
        return None

    def setitemmer(self, index, value):
        self.make_request(set_cmd.format(type_converter.to_raw(value), index=index))

    setitemmer.__doc__ = doc

    return setitemmer


def _make_indexed_getter(doc, indices, fgetitem, fsetitem):
    def getter(self):
        return _ArrayEventProperty(parent=self, indices=indices, fgetitem=fgetitem, fsetitem=fsetitem)

    getter.__doc__ = doc
    getter.__annotations__ = {"return": Mapping[int, fgetitem.__annotations__["return"]]}  # type: ignore

    return getter


def _make_event_matcher(set_cmd_response_re):
    def matcher(self, line):
        # pylint: disable=unused-argument
        match = set_cmd_response_re.match(line)
        if match:
            return Event(None, None)
        else:
            return None

    return matcher


def _make_valuechangeevent_matcher(type_converter, set_cmd_response_re):
    def matcher(self, line):
        # pylint: disable=unused-argument
        match = set_cmd_response_re.match(line)
        if match:
            return ValueChangeEvent(None, None, type_converter.to_api(match[1]))
        else:
            return None

    return matcher


def _make_indexvaluechangeevent_matcher(type_converter, set_cmd_response_re):
    def matcher(self, line):
        # pylint: disable=unused-argument
        match = set_cmd_response_re.match(line)
        if match:
            return IndexValueChangeEvent(None, None, int(match[1]), type_converter.to_api(match[2]))
        else:
            return None

    return matcher


def generic_event_property(
    doc: Optional[Text],
    type_: Any,
    indices: Optional[Iterable] = None,
    get_cmd: Optional[str] = None,
    set_cmd: Optional[str] = None,
    set_cmd_response: Optional[str] = None,
    fget: Optional[Callable[[Any], Any]] = None,
    fset: Optional[Callable[[Any, Any], None]] = None,
    fmatch: Optional[Callable[[Any, str], Optional[Event]]] = None,
) -> EventProperty:
    """\
    Factory function for creating an event property.

    This function is intended to be a one-stop shop for most means for creating EventProperty.

    :param Optional[Text] doc: docstring for the property
    :param Any type: type of the property
    :param Optional[Iterable] indices: for map-type properties, the indices
    :param Optional[str] get_cmd: format string for value getting
    :param Optional[str] set_cmd: format string for value setting
    :param Optional[str] set_cmd_response: regular expression string for parsing device-initiated messages
    :param Optional[Callable[[Any], T]] fget: direct fget function
    :param Optional[Callable[[Any, T], None]] fset: direct fset function
    :param Optional[Callable[[Any, str], Optional[Event]]] fmatch: direct fmatch function
    """
    # pylint: disable=too-many-branches

    if get_cmd is not None and fget is not None:
        raise ValueError("choose only one of get_cmd and fget, but not both")

    if set_cmd is not None and fset is not None:
        if indices is None:
            raise ValueError("choose only one of set_cmd and fset, but not both")

    if set_cmd_response:
        set_cmd_response_re = re.compile(set_cmd_response)

    # None is for device-initiated events that are unassociated with any configuration;
    # the "Reconfig" event on the DVS 304 is a good example.
    if type_ is None:

        if get_cmd is not None or set_cmd is not None:
            raise ValueError("get/set must be unspecified for None-type events")

        fget = _make_doconly_getter(doc)
        if fmatch is None:
            fmatch = _make_event_matcher(set_cmd_response_re)

    else:

        type_converter: ValueConverter
        if type_ is bool:
            type_converter = _BOOL_VALUE_CONVERTER
        elif type_ is int:
            type_converter = _INT_VALUE_CONVERTER
        else:
            type_converter = type_

        if indices is not None:
            if fget is None:
                fgetitem = _make_getitemmer(doc, type_converter, get_cmd)
                fsetitem = _make_setitemmer(doc, type_converter, set_cmd)
                fget = _make_indexed_getter(doc, indices, fgetitem, fsetitem)
            if fmatch is None:
                fmatch = _make_indexvaluechangeevent_matcher(type_converter, set_cmd_response_re)
        else:
            if fget is None:
                fget = _make_getter(doc, type_converter, get_cmd)
            if fset is None:
                fset = _make_setter(doc, type_converter, set_cmd)
            if fmatch is None:
                fmatch = _make_valuechangeevent_matcher(type_converter, set_cmd_response_re)

    return EventProperty(
        doc=doc,
        fget=fget,
        fset=fset,
        fmatch=fmatch,
    )
