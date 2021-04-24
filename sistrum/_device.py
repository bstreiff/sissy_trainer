import serial  # type: ignore
import serial.threaded  # type: ignore

from sistrum._auto_protocol import AutoExtronProtocol
from sistrum._auto_protocol import get_protocol_class_for_part_number


class ExtronDevice:
    def __init__(self, serial_uri, part_number=None):
        self.serial = serial.serial_for_url(
            serial_uri,
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=1,
            xonxoff=0,
            rtscts=0,
        )
        if part_number is None:
            protocol_class = AutoExtronProtocol
        else:
            protocol_class = get_protocol_class_for_part_number(part_number)

        self.thread = serial.threaded.ReaderThread(self.serial, protocol_class)

    def __enter__(self):
        return self.thread.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.thread.__exit__(exc_type, exc_val, exc_tb)
