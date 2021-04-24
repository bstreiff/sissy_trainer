import serial.threaded  # type: ignore
from sistrum.device_dvs304 import ExtronDVS304Protocol
from sistrum.device_mps112 import ExtronMPS112Protocol
from sistrum._protocol import ExtronProtocol
from sistrum._part_numbers import PartNumber


_PROTOCOL_INDEX = {
    PartNumber.EXTRON_DVS_304: ExtronDVS304Protocol,
    PartNumber.EXTRON_DVS_304_A: ExtronDVS304Protocol,
    PartNumber.EXTRON_DVS_304_D: ExtronDVS304Protocol,
    PartNumber.EXTRON_DVS_304_AD: ExtronDVS304Protocol,
    PartNumber.EXTRON_DVS_304_DVI: ExtronDVS304Protocol,
    PartNumber.EXTRON_DVS_304_DVI_A: ExtronDVS304Protocol,
    PartNumber.EXTRON_DVS_304_DVI_D: ExtronDVS304Protocol,
    PartNumber.EXTRON_DVS_304_DVI_AD: ExtronDVS304Protocol,
    PartNumber.EXTRON_MPS_112: ExtronMPS112Protocol,
    PartNumber.EXTRON_MPS_112CS: ExtronMPS112Protocol,
}


def get_protocol_class_for_part_number(part):
    if part in _PROTOCOL_INDEX:
        return _PROTOCOL_INDEX[part]
    else:
        return ExtronProtocol


class AutoExtronProtocol(serial.threaded.Protocol):
    """
    Auto-detecting class for finding an ExtronProtocol subclass based on part number.

    On connection_made, we make a part number request, then turn around and use that
    to replace the transport with a new class.
    """

    TERMINATOR = b"\r\n"

    def connection_made(self, transport):
        """
        Called when the transport connects.

        Retrieves the part number from the device, then replaces itself in the transport
        with a more-specific subclass that understands the commands for this particular
        model.
        """
        ser = transport.serial
        buffer = bytearray()

        # Send part number request
        ser.write("N".encode("latin-1", "replace"))

        # block for read
        while ser.is_open:
            data = ser.read(ser.in_waiting or 1)
            buffer.extend(data)
            if self.TERMINATOR in buffer:
                packet, buffer = buffer.split(self.TERMINATOR, 1)
                part_number = packet.decode("latin-1", "replace")
                proto_class = get_protocol_class_for_part_number(part_number)
                if proto_class is not None:
                    new_proto = proto_class()
                    transport.protocol = new_proto
                    new_proto.connection_made(transport)
                    return
