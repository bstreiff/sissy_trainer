import threading
import logging
import inspect
import copy
from typing import Callable

import serial.threaded  # type: ignore

from sistrum.exceptions import exception_from_error_code
from sistrum._event import Event, EventProperty

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

__all__ = ["ExtronProtocol"]


class _ExtronProtocol(serial.threaded.LineReader):
    """\
    This is a "private" superclass of ExtronProtocol, containing all the internal machinery
    that we don't want to have documented as the public API. Having this split out as a
    separate class gives us a private-public buffer that we can specify with the inherited-members
    directive option in sphinx.
    """

    TERMINATOR = b"\r\n"
    ENCODING = "latin-1"

    def __init__(self):
        super().__init__()
        self._line_handler_event = threading.Event()
        self._waiting_for_response = False
        self._response = None
        self._response_exception = None

        # list of (name, listener) tuples. probably room for a more efficient data structure here...
        self._listeners = []

        # We don't expect new properties to be added to the class after __init__
        # (should this be cached in the class members?)
        self._event_members = copy.copy(inspect.getmembers(self.__class__, lambda o: isinstance(o, EventProperty)))

    def _add_event_listener(self, name: str, listener: Callable[[Event], bool]) -> None:
        self._listeners.append((name, listener))

    def _remove_event_listener(self, name: str, listener: Callable[[Event], bool]) -> None:
        self._listeners.remove((name, listener))

    def _handle_device_event(self, line) -> bool:
        for name, prop in self._event_members:
            event_obj = prop.fmatch(self, line)
            if event_obj:
                event_obj.name = name
                event_obj.source = self
                for listener_event_name, listener in self._listeners:
                    if listener_event_name in ("*", name):
                        # if the function returns something truthy, stop processing
                        if listener(event_obj):
                            return True
                return True
        return False

    def handle_line(self, line: str) -> None:
        """Handler method for serial.threaded.LineReader."""
        logger.debug("<-- %s", line)
        if self._waiting_for_response:
            if line.startswith("E"):
                self._response_exception = exception_from_error_code(line)
            self._response = line
            self._line_handler_event.set()
        elif self._handle_device_event(line):
            return
        else:
            logger.debug("got unexpected line %s", line)

    def _handle_possible_exception_from_thread(self) -> None:
        if self._response_exception is not None:
            # pylint: disable=raising-bad-type
            exception_from_thread = self._response_exception
            self._response_exception = None
            raise exception_from_thread

    def make_request(self, request: str, timeout=1.0) -> str:
        logger.debug("--> %s", request)
        self._waiting_for_response = True

        # Can't use write_line, because we want to send without TERMINATOR.
        self.transport.write(request.encode(self.ENCODING, self.UNICODE_HANDLING))

        self._line_handler_event.wait(timeout)
        self._line_handler_event.clear()
        self._waiting_for_response = False

        self._handle_possible_exception_from_thread()
        return self._response


class ExtronProtocol(_ExtronProtocol):
    """
    Handles the basic line-oriented functions of the Extron SIS control protocol.

    This class handles the common "Q" (firmware version) and "N" (part number)
    commands. Subclasses are intended to handle more specific commands.
    """

    def add_event_listener(self, name: str, listener: Callable[[Event], bool]) -> None:
        """\
        Add an event listener.

        :param str name: Name of the event to listen for. A string of ``*`` listens for all events.
        :param Callable[[sistrum.Event],bool] listener: A callable to be called for this event. \
                                                              Returning True stops further listeners from \
                                                              being called for this event.
        """
        self._add_event_listener(name, listener)

    def remove_event_listener(self, name: str, listener: Callable[[Event], bool]) -> None:
        """\
        Remove a previously-added an event listener.

        :param str name: Name of the event that was listened for.
        :param Callable[[sistrum.Event],bool] listener: Listener that was previously added.
        """
        self._remove_event_listener(name, listener)

    @property
    def firmware_version(self) -> str:
        """\
        Retrieve the firmware version from the device.
        """
        return self.make_request("Q")

    @property
    def part_number(self) -> str:
        """\
        Retrieve the part number from the device.
        """
        return self.make_request("N")
