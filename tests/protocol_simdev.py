# This is a "simulated device" pyserial test rig. It's built on top
# of protocol_loop, with some differences:
# - We use two protocol_loop instances so that we can have two distinct
#   RX/TX queues. We need this for some of our tests, especially ones
#   where the device is sending asynchronous notifications-- otherwise
#   the simulated device ends up reading off its own notifications and
#   gets very confused.
# - We also have a hook in write() to have the DUT handle the command
#   just sent by the client. This is mostly a convenience that keeps us
#   from needing to create a thread to run the "DUT" logic in. It does
#   mean that command processing ends up being synchronized, but that's
#   sufficient for test purposes.

import logging
import serial  # type: ignore
from serial.urlhandler.protocol_loop import LOGGER_LEVELS  # type: ignore
from serial.urlhandler.protocol_loop import Serial as LoopSerial
from serial.serialutil import SerialBase, SerialException, PortNotOpenError
import urllib.parse as urlparse
import re
from sistrum.exceptions import SISError
import inspect
import time
from typing import Dict


class Serial(SerialBase):
    def __init__(self, *args, **kwargs):
        self.local_loopback = LoopSerial(*args, **kwargs)
        self.remote_loopback = LoopSerial(*args, **kwargs)
        self.is_open = False
        self._real_port = None
        super(Serial, self).__init__(*args, **kwargs)

    def open(self):
        self.from_url(self._real_port)

        self.local_loopback.open()
        self.remote_loopback.open()
        self.is_open = True

    def close(self):
        self.remote_loopback.close()
        self.local_loopback.close()
        self.is_open = False

    def from_url(self, url):
        parts = urlparse.urlsplit(url)
        if parts.scheme != "simdev":
            raise SerialException(
                "expected a string in the form "
                '"simdev://<class>[?logging=(debug|info|warning|error)]": not starting '
                "with simdev:// ({!r})".format(parts.scheme)
            )
        try:
            # process options now, directly altering self
            for option, values in urlparse.parse_qs(parts.query, True).items():
                if option == "logging":
                    logging.basicConfig()
                    self.logger = logging.getLogger("simdev")
                    self.logger.setLevel(LOGGER_LEVELS[values[0]])
                    self.logger.debug("enabled logging")
                else:
                    raise ValueError("unknown option: {!r}".format(option))
        except ValueError as e:
            raise SerialException(
                "expected a string in the form " '"simdev://<class>[?logging=(debug|info|warning|error)]": {}'.format(e)
            )

        devclass = simulator_classes[parts.hostname]
        self.simdev = devclass(self)

        reconstructed_url = urlparse.urlunsplit(("loop", parts[1], parts[2], parts[3], parts[4]))
        self.local_loopback.from_url(reconstructed_url)
        self.remote_loopback.from_url(reconstructed_url)

    def _reconfigure_port(self):
        self.local_loopback._reconfigure_port()
        self.remote_loopback._reconfigure_port()

    @property
    def port(self):
        return self._real_port

    @port.setter
    def port(self, port):
        self._real_port = port
        if port:
            parts = urlparse.urlsplit(port)
            port = urlparse.urlunsplit(("loop", parts[1], parts[2], parts[3], parts[4]))

        self.local_loopback.port = port
        self.remote_loopback.port = port

    @property
    def baudrate(self, baudrate):
        return self.local_looback.baudrate

    @baudrate.setter
    def baudrate(self, baudrate):
        self.local_loopback.baudrate = baudrate
        self.remote_loopback.baudrate = baudrate

    @property
    def timeout(self):
        return self.local_loopback.timeout

    @timeout.setter
    def timeout(self, timeout):
        self.local_loopback.timeout = timeout
        self.remote_loopback.timeout = timeout

    # -----------------------------------------------------------------------
    # This is the "normal pyserial client" side.
    # -----------------------------------------------------------------------

    @property
    def in_waiting(self):
        return self.local_loopback.in_waiting

    def read(self, size=1):
        return self.local_loopback.read(size)

    def cancel_read(self):
        self.local_loopback.cancel_read()

    def reset_input_buffer(self):
        self.local_looback.reset_input_buffer()

    @property
    def out_waiting(self):
        return self.remote_loopback.out_waiting

    def write(self, data):
        ret = self.remote_loopback.write(data)
        self.simdev.process_write()
        return ret

    def cancel_write(self):
        self.remote_loopback.cancel_write()

    def reset_output_buffer(self):
        self.remote_loopback.reset_output_buffer()

    # -----------------------------------------------------------------------
    # These probably aren't right, but devices don't use flow control anyway.
    # -----------------------------------------------------------------------

    @property
    def cts(self):
        return self.remote_loopback.cts

    @property
    def dsr(self):
        return self.remote_loopback.dsr

    @property
    def ri(self):
        return self.local_loopback.ri

    @property
    def cd(self):
        return self.local_loopback.cd

    # -----------------------------------------------------------------------
    # This is the DUT side.
    # -----------------------------------------------------------------------

    @property
    def dut_in_waiting(self):
        return self.remote_loopback.in_waiting

    def dut_read(self, size=1):
        return self.remote_loopback.read(size)

    def dut_cancel_read(self):
        self.remote_loopback.cancel_read()

    def dut_reset_input_buffer(self):
        self.remote_looback.reset_input_buffer()

    @property
    def dut_out_waiting(self):
        return self.local_loopback.out_waiting

    def dut_write(self, data):
        return self.local_loopback.write(data)

    def dut_cancel_write(self):
        self.local_loopback.cancel_write()

    def dut_reset_output_buffer(self):
        self.local_loopback.reset_output_buffer()
    
    # convenience functions

    def dut_write_str(self, data, timeout=1.0):
        timeout_complete = time.time() + timeout
        self.dut_write((data + "\r\n").encode("latin-1", "replace"))
        # sit and wait for the client's ReaderThread to realize there's stuff enqueued
        while self.dut_out_waiting > 0 and time.time() < timeout_complete:
            pass


class SimulatedDevice(object):
    def __init__(self, serial, part_number):
        self.serial = serial
        self.part_number = part_number
        self.handlers = []

        self.handlers.append((r"^[Nn]$", self.get_part_number))

    def process_write(self):
        buffer = self.serial.dut_read(self.serial.dut_in_waiting)
        cmd = buffer.decode("latin-1", "replace")

        for regexp, func in self.handlers:
            m = re.match(regexp, cmd)
            if m:
                try:
                    # Use the type annotations to cast values to the desired types (usually int)
                    # to save on boilerplate
                    params = inspect.signature(func).parameters
                    match_groups = m.groups()
                    match_group_id = 0
                    manipulated_args = []
                    for param_name in params:
                        param_cls = params[param_name].annotation
                        if param_cls is inspect.Parameter.empty:
                            manipulated_args.append(match_groups[match_group_id])
                        else:
                            manipulated_args.append(param_cls(match_groups[match_group_id]))
                        match_group_id += 1

                    resp = func(*tuple(manipulated_args))
                    self.serial.dut_write_str(resp)
                except SISError as e:
                    self.serial.dut_write_str("E{0}".format(e.code))
                return

        # nothing matched
        self.serial.dut_write_str("E10")

    def get_part_number(self) -> str:
        return self.part_number


simulator_classes: Dict[str, SimulatedDevice] = {}
