from sistrum import ExtronDevice
from sistrum import PartNumber, InputVideoFormat, InputStandard, Resolution
from tests.protocol_simdev import simulator_classes, SimulatedDevice
from sistrum.device_dvs304 import _parse_status as dvs304_parse_status
from sistrum.exceptions import InvalidParameterError, InvalidInputNumberError
import pytest  # type: ignore
import logging
import re


def _get_supported_output_combination_list():
    VALID_OUTPUT_COMBINATIONS_50 = [(x, 1) for x in range(1, 23) if x not in [15, 20, 21]]
    VALID_OUTPUT_COMBINATIONS_60 = [(x, 2) for x in range(1, 26) if x not in [16]]
    VALID_OUTPUT_COMBINATIONS_72 = [(x, 3) for x in range(1, 13) if x not in [3, 11]]
    VALID_OUTPUT_COMBINATIONS_75 = [(20, 3)]
    # TODO: docs say that "1080p at 24 Hz" is valid, but this combination fails on my device (too-old firmware?)
    # TODO: what about behavior of "1080p Sharp" and "1080p CVT"?
    VALID_OUTPUT_COMBINATIONS_24 = [(19, 3)]
    VALID_OUTPUT_COMBINATIONS_96 = [(x, 4) for x in [1, 2, 4, 5, 7]]
    VALID_OUTPUT_COMBINATIONS_100 = [(x, 5) for x in [1, 2, 16]]
    VALID_OUTPUT_COMBINATIONS_120 = [(x, 6) for x in [1, 2]]
    VALID_OUTPUT_COMBINATIONS_59 = [(x, 7) for x in [15, 17, 18, 19]]

    return (VALID_OUTPUT_COMBINATIONS_50 +
            VALID_OUTPUT_COMBINATIONS_60 +
            VALID_OUTPUT_COMBINATIONS_72 +
            VALID_OUTPUT_COMBINATIONS_75 +
            VALID_OUTPUT_COMBINATIONS_24 +
            VALID_OUTPUT_COMBINATIONS_96 +
            VALID_OUTPUT_COMBINATIONS_100 +
            VALID_OUTPUT_COMBINATIONS_120 +
            VALID_OUTPUT_COMBINATIONS_59)


class SimulatedDVS304(SimulatedDevice):
    _VALID_OUTPUT_COMBINATIONS = _get_supported_output_combination_list()

    def __init__(self, serial, part_number=PartNumber.EXTRON_DVS_304):
        super(SimulatedDVS304, self).__init__(serial, part_number)
        self.reset()

        self.handlers.append((r"^(\d+)!$", self.set_both_input))
        self.handlers.append((r"^(\d+)&$", self.set_video_input))
        self.handlers.append((r"^(\d+)\$$", self.set_audio_input))
        self.handlers.append((r"^!$", self.get_both_input))
        self.handlers.append((r"^&$", self.get_video_input))
        self.handlers.append((r"^\$$", self.get_audio_input))

        self.handlers.append((r"^(\d+)\*(\d+)\\$", self.set_video_format))
        self.handlers.append((r"^(\d+)\\$", self.get_video_format))

        self.handlers.append((r"^(\d+)C$", self.set_color))
        self.handlers.append((r"^C$", self.get_color))

        self.handlers.append((r"^(\d+)\*(\d+)=$", self.set_output_rate))
        self.handlers.append((r"^=$", self.get_output_rate))

        self.handlers.append((r"^20S$", self.get_temperature))

    def reset(self) -> str:
        self.video_input = 1
        self.audio_input = 1
        self.input_format = [ 1, 2, 2, 8 ]
        self.color = 64
        self.output_rate = 1
        self.output_resolution = 2
        return "Zpx"

    def _check_input_number(self, value):
        # Observed behavior: Attempting to use an input "0" gives E13 instead of E01
        if value < 0:
            raise InvalidParameterError()
        if value > 4:
            raise InvalidInputNumberError()

    def set_both_input(self, value: int):
        self.set_video_input(value)
        self.set_audio_input(value)
        return "In{0} All".format(value)

    def set_video_input(self, value: int):
        self._check_input_number(value)
        self.video_input = value
        return "In{0} RGB".format(value)

    def set_audio_input(self, value: int):
        self._check_input_number(value)
        self.audio_input = value
        return "In{0} Aud".format(value)

    def get_both_input(self):
        return self.get_video_input()

    def get_video_input(self):
        return "{0}".format(self.video_input)

    def get_audio_input(self):
        return "{0}".format(self.audio_input)

    def set_video_format(self, index: int, value: int):
        self._check_input_number(index)

        # Input 1 can be CVBS or SDI
        if index == 1 and value not in [1, 9]:
            raise InvalidParameterError()
        # Input 2 can be CVBS, S-Video, YUVi, YUVp, YUV Auto, or SDI
        if index == 2 and value not in [1, 2, 4, 5, 8, 9]:
            raise InvalidParameterError()
        # Input 3 can be S-Video or SDI
        if index == 3 and value not in [2, 9]:
            raise InvalidParameterError()
        # Input 4 can be any of the possible options
        if index == 4 and value not in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
            raise InvalidParameterError()

        self.input_format[index - 1] = value
        return "{0}Typ{1}".format(index, value)

    def get_video_format(self, index: int):
        self._check_input_number(index)

        return "{0}".format(self.input_format[index - 1])

    def set_color(self, value: int) -> str:
        self.color = value
        return "Col{0}".format(self.color)

    def get_color(self) -> str:
        return "{0}".format(self.color)

    def set_output_rate(self, res: int, rate: int) -> str:
        if (res, rate) not in self._VALID_OUTPUT_COMBINATIONS:
            raise InvalidParameterError()
        self.output_resolution = res
        self.output_rate = rate
        return "Rte{0:02d}*{1:02d}".format(self.output_resolution, self.output_rate)

    def get_output_rate(self) -> str:
        return "{0:02d}*{1:02d}".format(self.output_resolution, self.output_rate)

    def get_temperature(self) -> str:
        # sure, this seems like a temperature
        return "45.5"


@pytest.fixture(scope="package", autouse=True)
def register_simulator():
    simulator_classes["dvs304"] = SimulatedDVS304
    yield
    del simulator_classes["dvs304"]


def test_dvs304_input_selection():
    dev = ExtronDevice("simdev://dvs304", part_number=PartNumber.EXTRON_DVS_304)
    with dev as protocol:
        for i in range(1, 5):
            protocol.input = i
            assert protocol.input == i
            assert protocol.video_input == i
            assert protocol.audio_input == i

        protocol.audio_input = 2

        for i in range(1, 5):
            protocol.video_input = i
            assert protocol.video_input == i
            assert protocol.audio_input == 2

        protocol.video_input = 2

        for i in range(1, 5):
            protocol.audio_input = i
            assert protocol.video_input == 2
            assert protocol.audio_input == i


def test_dvs304_input_format():
    dev = ExtronDevice("simdev://dvs304", part_number=PartNumber.EXTRON_DVS_304)
    with dev as protocol:
        protocol.video_input_format[1] = InputVideoFormat.CVBS
        assert protocol.video_input_format[1] == InputVideoFormat.CVBS

        protocol.video_input_format[2] = InputVideoFormat.SVIDEO
        assert protocol.video_input_format[2] == InputVideoFormat.SVIDEO

        protocol.video_input_format[3] = InputVideoFormat.SVIDEO
        assert protocol.video_input_format[3] == InputVideoFormat.SVIDEO

        protocol.video_input_format[4] = InputVideoFormat.RGB_SCALED
        assert protocol.video_input_format[4] == InputVideoFormat.RGB_SCALED


def test_dvs304_output_rate():
    dev = ExtronDevice("simdev://dvs304", part_number=PartNumber.EXTRON_DVS_304)
    with dev as protocol:
        RES_640x480at60 = (Resolution("640x480"), 60)
        RES_640x480at72 = (Resolution("640x480"), 72)
        RES_1440x900at75 = (Resolution("1440x900"), 75)
        RES_720pat50 = (Resolution("720p"), 50)
        RES_1080pat59_94 = (Resolution("1080p"), 59.94)
        RES_1080pat24 = (Resolution("1080p"), 24)

        protocol.output_rate = RES_1440x900at75
        assert protocol.output_rate == RES_1440x900at75

        protocol.output_rate = RES_640x480at72
        assert protocol.output_rate == RES_640x480at72

        protocol.output_rate = RES_1080pat59_94
        assert protocol.output_rate == RES_1080pat59_94

        protocol.output_rate = RES_1080pat24
        assert protocol.output_rate == RES_1080pat24

        protocol.output_rate = RES_720pat50
        assert protocol.output_rate == RES_720pat50

        protocol.output_rate = RES_640x480at60
        assert protocol.output_rate == RES_640x480at60

        with pytest.raises(InvalidParameterError):
            protocol.output_rate = (Resolution("852x480"), 96)

        with pytest.raises(InvalidParameterError):
            protocol.output_rate = (Resolution("640x480"), 24)

        with pytest.raises(InvalidParameterError):
            protocol.output_rate = (Resolution("123x456"), 60)


def test_dvs304_temperature():
    dev = ExtronDevice("simdev://dvs304", part_number=PartNumber.EXTRON_DVS_304)
    with dev as protocol:
        # we don't get a deterministic result from this, so just check that it's reasonable
        assert protocol.temperature >= 0.0


def test_dvs304_color():
    dev = ExtronDevice("simdev://dvs304", part_number=PartNumber.EXTRON_DVS_304)
    with dev as protocol:
        assert protocol.color == 64
        protocol.color = 32
        assert protocol.color == 32


def test_dvs304_status_parser():
    s = dvs304_parse_status("Vid4 Aud- Typ8 Std- Pre000")
    assert s.video_input == 4
    assert s.audio_input == 0
    assert s.input_format == InputVideoFormat.YUV_AUTO
    assert s.preset[1] == InputStandard.NONE
    assert s.preset[2] == InputStandard.NONE
    assert s.preset[3] == InputStandard.NONE
    assert s.sdi_input is None

    s = dvs304_parse_status("Vid2 Aud1 Typ1 Std0 Pre100 Sdi3")
    assert s.video_input == 2
    assert s.audio_input == 1
    assert s.input_format == InputVideoFormat.CVBS
    assert s.preset[1] == InputStandard.NTSC_3_58
    assert s.preset[2] == InputStandard.NONE
    assert s.preset[3] == InputStandard.NONE
    assert s.sdi_input == 3
