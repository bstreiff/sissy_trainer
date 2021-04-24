from sistrum import ExtronDevice
from sistrum import PartNumber, SwitcherMode, InputVideoFormat
from sistrum.exceptions import InvalidInputNumberError, InvalidParameterError
from tests.protocol_simdev import simulator_classes, SimulatedDevice
import pytest  # type: ignore
import logging
import re
import time


class SimulatedMPS112(SimulatedDevice):
    def __init__(self, serial, part_number=PartNumber.EXTRON_MPS_112):
        super(SimulatedMPS112, self).__init__(serial, part_number)
        self.reset()

        self.handlers.append((r"^(\d+)\*(\d+)!$", self.select_separate))
        self.handlers.append((r"^(\d+)!", self.select_single))

        self.handlers.append((r"^(\d+)V$", self.set_volume))
        self.handlers.append((r"^V$", self.get_volume))
        self.handlers.append((r"^(\d+)[Zz]$", self.set_audio_mute))
        self.handlers.append((r"^[Zz]$", self.get_audio_mute))
        self.handlers.append((r"^[Xx]$", self.get_exec_mode))

        self.handlers.append((r"^[Qq]$", self.get_firmware_version))

        self.handlers.append((r"^16\*(\d+)G$", self.set_mic_gain))
        self.handlers.append((r"^16\*(\d+)g$", self.set_mic_attenuation))
        self.handlers.append((r"^16[Gg]", self.get_mic_volume))

        self.handlers.append((r"^(\d+)[Mm]$", self.set_mic))
        self.handlers.append((r"^[Mm]$", self.get_mic))

        self.handlers.append((r"^(\d+)[Xx]$", self.set_exec_mode))

        ESCAPE = "\x1B"
        self.handlers.append((r"^" + ESCAPE + r"ZXXX$", self.reset))

        self.handlers.append((r"^[Ii]$", self.get_info))

        self.handlers.append((r"^(\d+)\*1#$", self.set_switcher_mode))
        self.handlers.append((r"^1#$", self.get_switcher_mode))

        self.handlers.append((r"^(\d+)\*2#$", self.set_mic_thresh))
        self.handlers.append((r"^2#$", self.get_mic_thresh))

    def reset(self) -> str:
        self.mode = 1
        self.single_input = 0
        self.separate_input = [1, 1, 1]
        self.audio_group = 1
        self.audio_input = 0
        self.main_volume = 70
        self.mic_volume = 0
        self.exec_mode = 0
        self.mic_thresh = 8
        self.follow_sub_mode = 0
        self.mic_power = 0
        self.ducking_level = 6
        self.audio_mute = 0
        self.mic_on = 0
        return "Zpx"

    # TODO: figure out all the rules for transitioning between
    # single and separate switcher mode

    def select_separate(self, group: int, input: int) -> str:
        if group < 1 or group > 3:
            raise InvalidParameterError()
        if input < 0 or input > 4:
            raise InvalidParameterError()

        if self.mode == 1:
            # single-switcher mode: just set the input, all others are off
            self.single_input = input
        else:
            # separate-switcher mode
            self.separate_input[(group - 1)] = input
            self.audio_group = group
            self.audio_input = input

        return "Chn{0}*{1}".format(group, input)

    def select_single(self, input: int) -> str:
        if input < 0 or input > 12:
            raise InvalidParameterError()

        # command is not valid in separate-switcher mode
        if self.mode == 2:
            raise InvalidInputNumberError()

        self.single_input = input

        return "Chn{0}".format(input)

    def set_volume(self, volume: int) -> str:
        if volume < 0 or volume > 100:
            raise InvalidParameterError()

        self.main_volume = volume
        return "Vol{0}".format(self.main_volume)

    def get_volume(self) -> str:
        return "{0}".format(self.main_volume)

    def set_audio_mute(self, audio_mute: int) -> str:
        if audio_mute < 0 or audio_mute > 1:
            raise InvalidParameterError()

        self.audio_mute = audio_mute
        return "Amt{0}".format(self.audio_mute)

    def get_audio_mute(self) -> str:
        return "{0}".format(self.audio_mute)

    def get_firmware_version(self) -> str:
        return "1.02"

    def set_exec_mode(self, exec_mode: int) -> str:
        if exec_mode < 0 or exec_mode > 3:
            raise InvalidParameterError()

        self.exec_mode = exec_mode
        return "Exe{0}".format(self.exec_mode)

    def get_exec_mode(self) -> str:
        return "{0}".format(self.exec_mode)

    def set_mic_gain(self, mic_gain: int) -> str:
        if mic_gain < 0 or mic_gain > 12:
            raise InvalidParameterError()

        self.mic_volume = mic_gain

        return "Aud+{0}".format(mic_gain)

    def set_mic_attenuation(self, mic_att: int) -> str:
        if mic_att < 1 or mic_att > 66:
            raise InvalidParameterError()

        self.mic_volume = -mic_att

        return "Aud-{0}".format(mic_att)

    def get_mic_volume(self) -> str:
        return "{0}".format(self.mic_volume)

    def set_mic(self, mic_on: int) -> str:
        if mic_on < 0 or mic_on > 1:
            raise InvalidParameterError()
        self.mic_on = mic_on
        return "Mix{0}".format(self.mic_on)

    def get_mic(self) -> str:
        return "{0}".format(self.mic_on)

    def get_info(self) -> str:
        if self.mode == 1:
            # single-input mode
            inputs = [0, 0, 0]

            if self.single_input > 0:
                active_group = ((self.single_input - 1) // 4) + 1
                active_input = ((self.single_input - 1) % 4) + 1
                inputs[active_group - 1] = active_input
            else:
                active_group = 1
                active_input = 0

            return "Mod{mode} 1G{g1} 2G{g2} 3G{g3} 4G={audgroup}G{audinput}".format(
                mode=self.mode, g1=inputs[0], g2=inputs[1], g3=inputs[2], audgroup=active_group, audinput=active_input
            )
        else:
            # separate-input mode
            return "Mod{mode} 1G{g1} 2G{g2} 3G{g3} 4G={audgroup}G{audinput}".format(
                mode=self.mode,
                g1=self.separate_input[0],
                g2=self.separate_input[1],
                g3=self.separate_input[2],
                audgroup=self.audio_group,
                audinput=self.audio_input,
            )

    def set_switcher_mode(self, mode: int) -> str:
        if mode < 1 or mode > 2:
            raise InvalidParameterError()

        self.mode = mode
        return "Mod{0}".format(self.mode)

    def get_switcher_mode(self) -> str:
        return "{0}".format(self.mode)

    def set_mic_thresh(self, thresh: int) -> str:
        if thresh < 0 or thresh > 15:
            raise InvalidParameterError()
        self.mic_thresh = thresh
        return "Thr{0}".format(self.mic_thresh)

    def get_mic_thresh(self) -> str:
        return "{0}".format(self.mic_thresh)


@pytest.fixture(scope="package", autouse=True)
def register_simulator():
    simulator_classes["mps112"] = SimulatedMPS112
    yield
    del simulator_classes["mps112"]


def test_mps112_auto():
    dev = ExtronDevice("simdev://mps112")
    with dev as protocol:
        assert protocol.part_number == PartNumber.EXTRON_MPS_112


def test_mps112_volume():
    dev = ExtronDevice("simdev://mps112", part_number=PartNumber.EXTRON_MPS_112)
    with dev as protocol:
        protocol.volume = 42
        assert protocol.volume == 42

        with pytest.raises(InvalidParameterError):
            protocol.volume = 256


def test_mps112_input_single():
    dev = ExtronDevice("simdev://mps112", part_number=PartNumber.EXTRON_MPS_112)
    with dev as protocol:
        protocol.switcher_mode = SwitcherMode.SINGLE
        assert protocol.switcher_mode == SwitcherMode.SINGLE

        for i in range(0, 12):
            protocol.input = i
            assert protocol.input == i


def test_mps112_input_separate():
    dev = ExtronDevice("simdev://mps112", part_number=PartNumber.EXTRON_MPS_112)
    with dev as protocol:
        protocol.switcher_mode = SwitcherMode.SEPARATE
        assert protocol.switcher_mode == SwitcherMode.SEPARATE

        for group in [1, 2, 3]:
            for i in range(0, 4):
                protocol.input[group] = i
                assert protocol.input[group] == i


def test_mps112_input_works_like_an_int():
    dev = ExtronDevice("simdev://mps112", part_number=PartNumber.EXTRON_MPS_112)
    with dev as protocol:
        protocol.switcher_mode = SwitcherMode.SINGLE
        assert protocol.switcher_mode == SwitcherMode.SINGLE

        protocol.input = 3
        latched_value = protocol.input
        assert latched_value == 3

        # set it to something different
        protocol.input = 5
        # make sure the value didn't change
        assert latched_value == 3

        # cast to int should give same result
        assert int(latched_value) == 3
        # how about some math?
        assert latched_value + 1 == 4
        assert latched_value - 1 == 2
        # comparisons
        assert latched_value > 2
        assert latched_value < 4


def test_mps112_input_works_like_a_dict():
    from copy import copy

    dev = ExtronDevice("simdev://mps112", part_number=PartNumber.EXTRON_MPS_112)
    with dev as protocol:
        protocol.switcher_mode = SwitcherMode.SEPARATE
        assert protocol.switcher_mode == SwitcherMode.SEPARATE

        protocol.input[1] = 4
        protocol.input[2] = 0
        protocol.input[3] = 2

        latched_value = protocol.input
        protocol.input[1] = 1
        protocol.input[2] = 3
        protocol.input[3] = 4

        # like assigning a dict, it's just a reference and not a copy
        assert latched_value[1] == 1
        assert latched_value[2] == 3
        assert latched_value[3] == 4

        assert len(latched_value) == 3
        assert 1 in latched_value
        assert 2 in latched_value
        assert 3 in latched_value
        assert 4 not in latched_value
        assert list(latched_value.keys()) == [1, 2, 3]
        assert list(latched_value.values()) == [1, 3, 4]

        # but we can make a copy?
        copied_value = copy(latched_value)
        protocol.input[1] = 2
        protocol.input[2] = 4
        protocol.input[3] = 1

        assert copied_value[1] == 1
        assert copied_value[2] == 3
        assert copied_value[3] == 4


def test_mps112_input_switch_modes():
    dev = ExtronDevice("simdev://mps112", part_number=PartNumber.EXTRON_MPS_112)
    with dev as protocol:
        protocol.switcher_mode = SwitcherMode.SINGLE
        assert protocol.switcher_mode == SwitcherMode.SINGLE

        protocol.input = 7
        status = protocol.status
        assert status.input[1] == 0
        assert status.input[2] == 3
        assert status.input[3] == 0
        assert status.audio_group == 2
        assert status.audio_input == 3

        protocol.switcher_mode = SwitcherMode.SEPARATE

        protocol.input[1] = 2
        status = protocol.status
        assert status.input[1] == 2
        assert status.input[2] == 1
        assert status.input[3] == 1
        assert status.audio_group == 1
        assert status.audio_input == 2

        protocol.switcher_mode = SwitcherMode.SINGLE

        # when switching back, we get the old settings from single mode
        status = protocol.status
        assert status.input[1] == 0
        assert status.input[2] == 3
        assert status.input[3] == 0
        assert status.audio_group == 2
        assert status.audio_input == 3


def test_mps112_mic_volume():
    dev = ExtronDevice("simdev://mps112", part_number=PartNumber.EXTRON_MPS_112)
    with dev as protocol:
        protocol.mic_volume = 0
        assert protocol.mic_volume == 0

        protocol.mic_volume = 12
        assert protocol.mic_volume == 12

        protocol.mic_volume = -66
        assert protocol.mic_volume == -66

        with pytest.raises(InvalidParameterError):
            protocol.mic_volume = -67

        with pytest.raises(InvalidParameterError):
            protocol.mic_volume = 13

        protocol.mic_volume = 0


def get_simdev(protocol):
    return protocol.transport.serial.simdev

def simdev_write_line(protocol, string):
    protocol.transport.serial.dut_write_str(string)

def test_mps112_test_volume_notifications():
    dev = ExtronDevice("simdev://mps112", part_number=PartNumber.EXTRON_MPS_112)
    with dev as protocol:
        protocol.volume = 40

        class VolumeEventHandler(object):
            def __init__(self):
                self.last_value = 0

            def __call__(self, ev):
                self.last_value = ev.value
                return True

        handle_volume_event = VolumeEventHandler()

        protocol.add_event_listener('volume', handle_volume_event)

        # Simulate changing the volume knob
        simdev = get_simdev(protocol)
        simdev_write_line(protocol, simdev.set_volume(40))
        assert handle_volume_event.last_value == 40

        simdev_write_line(protocol, simdev.set_volume(41))
        assert handle_volume_event.last_value == 41

        simdev_write_line(protocol, simdev.set_volume(42))
        assert handle_volume_event.last_value == 42

        simdev_write_line(protocol, simdev.set_volume(43))
        assert handle_volume_event.last_value == 43

        protocol.volume = 50
        assert protocol.volume == 50


def test_mps112_separate_to_single_input():
    from sistrum.device_mps112 import _separate_to_single_input

    CASES = [
        ((1, 0), 0),
        ((1, 1), 1),
        ((1, 2), 2),
        ((1, 3), 3),
        ((1, 4), 4),
        ((2, 0), 0),
        ((2, 1), 5),
        ((2, 2), 6),
        ((2, 3), 7),
        ((2, 4), 8),
        ((3, 0), 0),
        ((3, 1), 9),
        ((3, 2), 10),
        ((3, 3), 11),
        ((3, 4), 12),
    ]

    for case in CASES:
        (group, input), expected = case

        assert _separate_to_single_input(group, input) == expected

