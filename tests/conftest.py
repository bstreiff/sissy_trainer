import pytest  # type: ignore
import serial  # type: ignore


@pytest.fixture(scope="module", autouse=True)
def pyserial_registrar():
    serial.protocol_handler_packages.append("tests")
