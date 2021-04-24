"""\
This module supports the Extron `DVS 304`_ and `DVS 304 DVI`_ Digital Video Scalers.

The DVS 304 is a four-input video and RGB scaler. Variants include audio switching ("A" models),
a SDI input ("D" models), and DVI-I output ("DVI" models).

These devices feature four inputs:
    - Input 1: A BNC connector for composite video.
    - Input 2: Three BNC connectors, capable of composite video, S-Video, or component video.
    - Input 3: A 4-pin mini DIN connector, capable of S-Video.
    - Input 4: A HD15 connector that can accept composite, S-Video, component, RGBHV, RGBS, RGsB, or RGBcvS.

More information is available in the `user manual`_.

.. _DVS 304: https://www.extron.com/product/dvs304
.. _DVS 304 DVI: https://www.extron.com/product/dvs304dvi
.. _user manual: https://media.extron.com/public/download/files/userman/DVS_304_Series_68-1039-01_G.pdf
"""

import math
from typing import Mapping, Optional, Tuple
import re
from sistrum._protocol import ExtronProtocol
from sistrum._enums import TestPattern, InputVideoFormat, InputStandard
from sistrum._resolution import Resolution
from sistrum._event import (
    ValueConverter,
    EnumValueConverter,
    generic_event_property,
)
from sistrum.exceptions import InvalidParameterError  # pylint: disable=no-name-in-module


__all__ = ["ExtronDVS304Protocol", "Status"]


_INPUT_VIDEO_FORMAT = EnumValueConverter(
    {
        "1": InputVideoFormat.CVBS,
        "2": InputVideoFormat.SVIDEO,
        "3": InputVideoFormat.RGBCVS,
        "4": InputVideoFormat.YUV_I,
        "5": InputVideoFormat.YUV_P,
        "6": InputVideoFormat.RGB_SCALED,
        "7": InputVideoFormat.RGB_PASSTHROUGH,
        "8": InputVideoFormat.YUV_AUTO,
        "9": InputVideoFormat.SDI,
    }
)

# has to match against a string because of the "-" id
_INPUT_STANDARD = EnumValueConverter(
    {
        "0": InputStandard.NONE,
        "1": InputStandard.NTSC_3_58,
        "2": InputStandard.PAL,
        "3": InputStandard.NTSC_4_43,
        "4": InputStandard.SECAM,
        "-": InputStandard.OTHER,
    }
)

_OUTPUT_RESOLUTION = EnumValueConverter(
    {
        "1": Resolution(640, 480),
        "2": Resolution(800, 600),
        "3": Resolution(852, 480),
        "4": Resolution(1024, 768),
        "5": Resolution(1024, 852),
        "6": Resolution(1024, 1024),
        "7": Resolution(1280, 768),
        "8": Resolution(1280, 1024),
        "9": Resolution(1360, 765),
        "10": Resolution(1364, 768),
        "11": Resolution(1365, 1024),
        "12": Resolution(1366, 768),
        "13": Resolution(1400, 1050),
        "14": Resolution(1600, 1200),
        "15": Resolution("480p"),
        "16": Resolution("576p"),
        "17": Resolution("720p"),
        "18": Resolution("1080i"),
        "19": Resolution("1080p"),
        "20": Resolution(1440, 900),
        "21": Resolution(1680, 1050),
        "22": Resolution(1280, 800),
        "23": Resolution("1080p Sharp"),
        "24": Resolution(1920, 1200),
        "25": Resolution("1080p CVT"),
    }
)

_OUTPUT_REFRESH_RATE = EnumValueConverter(
    {
        "1": 50.00,
        "2": 60.00,
        "3": 72.00,  # note: 3 is "75 Hz for 1440x900, 24 Hz for 1080p"
        "4": 96.00,
        "5": 100.0,
        "6": 120.0,
        "7": 59.94,
    }
)


class OutputRateConverter(ValueConverter):
    _MATCHER = re.compile(r"(\d+)\*(\d+)")

    def __init__(self):
        self.prim_type = Tuple[Resolution, float]

    def to_raw(self, obj: Tuple[Resolution, float]) -> str:
        (resolution, refresh) = obj

        try:
            resolution_raw = _OUTPUT_RESOLUTION.to_raw(resolution)
        except ValueError as value_error:
            raise InvalidParameterError() from value_error

        # the '3' case is weird...
        if resolution.width == 1440 and resolution.height == 900 and math.isclose(refresh, 75.0):
            refresh_raw = "3"
        elif resolution.width == 1920 and resolution.height == 1080 and math.isclose(refresh, 24.0):
            refresh_raw = "3"
        else:
            try:
                refresh_raw = _OUTPUT_REFRESH_RATE.to_raw(refresh)
            except ValueError as value_error:
                raise InvalidParameterError() from value_error

        return "{0:02d}*{1:02d}".format(int(resolution_raw), int(refresh_raw))

    def to_api(self, obj: str) -> Tuple[Resolution, float]:
        match = self._MATCHER.match(obj)
        if match:
            resolution_raw = int(match[1])
            refresh_raw = int(match[2])

            resolution = _OUTPUT_RESOLUTION.to_api(str(resolution_raw))
            refresh = _OUTPUT_REFRESH_RATE.to_api(str(refresh_raw))
            # The "72 Hz" mode isn't always 72 Hz, annoyingly.
            if refresh_raw == 3:
                if resolution.width == 1440 and resolution.height == 900:
                    refresh = 75.0
                elif resolution.width == 1920 and resolution.height == 1080:
                    refresh = 24.0
            return (resolution, refresh)
        raise ValueError("unable to match {0}".format(obj))


_OUTPUT_RESOLUTION_AND_REFRESH = OutputRateConverter()


_TEST_PATTERN = EnumValueConverter(
    {
        "0": TestPattern.OFF,
        "1": TestPattern.CROP,
        "2": TestPattern.ALTERNATING_PIXELS,
        "3": TestPattern.COLOR_BARS,
    }
)


class Status:
    video_input: int
    audio_input: int
    input_format: InputVideoFormat
    input_standard: InputStandard
    preset: Mapping[int, InputStandard]
    sdi_input: Optional[int]

    __slots__ = ("video_input", "audio_input", "input_format", "input_standard", "preset", "sdi_input")

    def __init__(
        self,
        video_input: int,
        audio_input: int,
        input_format: InputVideoFormat,
        input_standard: InputStandard,
        preset: Mapping[int, InputStandard],
        sdi_input: Optional[int],
    ):
        #: selected video input
        self.video_input = video_input
        #: selected audio input
        self.audio_input = audio_input
        #: input format of selected input
        self.input_format = input_format
        #: input standard
        self.input_standard = input_standard
        #: memory presets (indexed 1 through 3)
        self.preset = preset
        #: current SDI input selection (if applicable)
        self.sdi_input = sdi_input


def _parse_status(line):
    pattern = re.compile(r"^Vid([\d\-]) Aud([\d\-]) Typ(\d) Std([\d\-]) Pre(\d)(\d)(\d)(| Sdi(\d))$")
    match = pattern.match(line)

    video_input = 0 if match[1] == "-" else int(match[1])
    audio_input = 0 if match[2] == "-" else int(match[2])
    input_format = _INPUT_VIDEO_FORMAT.to_api(match[3])
    input_standard = _INPUT_STANDARD.to_api(match[4])
    preset = dict(
        [
            (1, _INPUT_STANDARD.to_api(match[5])),
            (2, _INPUT_STANDARD.to_api(match[6])),
            (3, _INPUT_STANDARD.to_api(match[7])),
        ]
    )
    if match[9] is None:
        sdi_input = None
    else:
        sdi_input = 0 if match[9] == "-" else int(match[9])

    return Status(video_input, audio_input, input_format, input_standard, preset, sdi_input)


class ExtronDVS304Protocol(ExtronProtocol):

    input = generic_event_property(
        """\
        Selected video and audio input, from 1 to 4.

        .. code-block:: python

           dvs304.input = 4
        """,
        int,
        get_cmd="!",
        set_cmd="{0}!",
        set_cmd_response=r"^In(\d) All$",
    )

    video_input = generic_event_property(
        """\
        Selected video input, from 1 to 4.

        .. code-block:: python

           dvs304.video_input = 2
        """,
        int,
        get_cmd="&",
        set_cmd="{0}&",
        set_cmd_response=r"^In(\d) RGB$",
    )

    audio_input = generic_event_property(
        """\
        Selected audio input, from 1 to 4.

        .. code-block:: python

           dvs304.audio_input = 2
        """,
        int,
        get_cmd="$",
        set_cmd="{0}$",
        set_cmd_response=r"^In(\d) Aud$",
    )

    video_input_format = generic_event_property(
        """\
        Video input format for inputs 1 to 4. Not all inputs support all video formats.

        .. code-block:: python

           dvs304.video_input_format[2] = InputVideoFormat.SVIDEO

        :raises InvalidParameterError: if the input does not support the specified format
        :raises DeviceNotPresentError: if configuring SDI on a device model not having SDI
        """,
        _INPUT_VIDEO_FORMAT,
        indices=range(1, 5),
        get_cmd="{index}\\",
        set_cmd="{index}*{0}\\",
        set_cmd_response=r"^(\d)Typ(\d)$",
    )

    horiz_start = generic_event_property(
        """\
        horizontal location of first active pixel in active window
        """,
        int,
        get_cmd=")",
        set_cmd="{0})",
        set_cmd_response=r"^Hst(\d)$",
    )

    vert_start = generic_event_property(
        """\
        vertical location of first active line in active window
        """,
        int,
        get_cmd="(",
        set_cmd="{0}(",
        set_cmd_response=r"^Vst(\d)$",
    )

    pixel_phase = generic_event_property(
        """\
        the pixel phase
        """,
        int,
        get_cmd="U",
        set_cmd="{0}U",
        set_cmd_response=r"^Phs(\d+)$",
    )

    total_pixels = generic_event_property(
        """\
        the total pixels
        """,
        int,
        get_cmd="11#",
        set_cmd="11*{0}#",
        set_cmd_response=r"^Tpx(\d+)$",
    )

    active_pixels = generic_event_property(
        """\
        the active pixels
        """,
        int,
        get_cmd="12#",
        set_cmd="12*{0}#",
        set_cmd_response=r"^Apx(\d+)$",
    )

    active_lines = generic_event_property(
        """\
        the active lines
        """,
        int,
        get_cmd="13#",
        set_cmd="13*{0}#",
        set_cmd_response=r"^Aln(\d+)$",
    )

    film_mode = generic_event_property(
        """\
        Film mode (auto sense for 3:2 or 2:2 pull-down)
        """,
        bool,
        get_cmd="18#",
        set_cmd="18*{0}#",
        set_cmd_response=r"^Flm(\d+)$",
    )

    video_mute = generic_event_property(
        """\
        Blank selected input
        """,
        bool,
        get_cmd="B",
        set_cmd="{0}B",
        set_cmd_response=r"^Vmt(\d+)$",
    )

    color = generic_event_property(
        """\
        color level
        """,
        int,
        get_cmd="C",
        set_cmd="{0}C",
        set_cmd_response=r"^Col(\d+)$",
    )

    tint = generic_event_property(
        """\
        tint level
        """,
        int,
        get_cmd="T",
        set_cmd="{0}T",
        set_cmd_response=r"^Tin(\d+)$",
    )

    contrast = generic_event_property(
        """\
        constrast level
        """,
        int,
        get_cmd="^",
        set_cmd="{0}^",
        set_cmd_response=r"^Con(\d+)$",
    )

    brightness = generic_event_property(
        """\
        brightness level
        """,
        int,
        get_cmd="Y",
        set_cmd="{0}Y",
        set_cmd_response=r"^Brt(\d+)$",
    )

    detail_filter = generic_event_property(
        """\
        detail (sharpness) level
        """,
        int,
        get_cmd="D",
        set_cmd="{0}D",
        set_cmd_response=r"^Shp(\d+)$",
    )

    horiz_shift = generic_event_property(
        """\
        horizontal centering
        """,
        int,
        get_cmd="H",
        set_cmd="{0}H",
        set_cmd_response=r"^Hph(\d+)$",
    )

    vert_shift = generic_event_property(
        """\
        vertical centering
        """,
        int,
        get_cmd="/",
        set_cmd="{0}/",
        set_cmd_response=r"^Vph(\d+)$",
    )

    horiz_size = generic_event_property(
        """\
        horizontal sizing
        """,
        int,
        get_cmd=":",
        set_cmd="{0}:",
        set_cmd_response=r"^Hsz(\d+)$",
    )

    vert_size = generic_event_property(
        """\
        vertical sizing
        """,
        int,
        get_cmd=";",
        set_cmd="{0};",
        set_cmd_response=r"^Vsz(\d+)$",
    )

    zoom = generic_event_property(
        """\
        zoom percentage
        """,
        int,
        get_cmd="{",
        set_cmd="{0}{{",
        set_cmd_response=r"^Zom(\d+)$",
    )

    # pan will be wierd, it only has relative positioning
    # and the bounds change based on zoom percentage and resolution :(

    output_rate = generic_event_property(
        """\
        Output resolution and refresh rate.
        """,
        _OUTPUT_RESOLUTION_AND_REFRESH,
        get_cmd="=",
        set_cmd="{0}=",
        set_cmd_response=r"^Rte(\d+\*\d+)$",
    )

    test_pattern = generic_event_property(
        """\
        The currently configured test pattern.

        The DVS304 family supports values of :obj:`~sistrum.TestPattern.OFF`,
        :obj:`~sistrum.TestPattern.CROP`, :obj:`~sistrum.TestPattern.ALTERNATING_PIXELS`,
        and :obj:`~sistrum.TestPattern.COLOR_BARS`. Any other setting will result in
        an error.
        """,
        _TEST_PATTERN,
        get_cmd="J",
        set_cmd="{0}J",
        set_cmd_response=r"^Tst(\d+)$",
    )

    freeze = generic_event_property(
        """\
        Freeze the image for use as a logo or for annotation.
        """,
        bool,
        get_cmd="F",
        set_cmd="{0}F",
        set_cmd_response=r"^Frz(\d+)$",
    )

    auto_switch = generic_event_property(
        """\
        The Auto switch mode causes the highest numbered input having a signal present
        to be automatically detected. For example, if both inputs 1 and 3 have active
        input signals, input 3 will be selected. Note that the presence of any SDI
        input signal will be ignored.
        """,
        bool,
        get_cmd="10#",
        set_cmd="10*{0}#",
        set_cmd_response=r"^Asw(\d+)$",
    )

    blue_screen = generic_event_property(
        """\
        The Blue mode assists the user in setting up the color and tint level on
        the scaler. When enabled, only sync and blue video signals will be passed
        to the display.

        The Blue mode has no effect for RGB pass-through mode on input 4.
        """,
        bool,
        get_cmd="8#",
        set_cmd="8*{0}#",
        set_cmd_response=r"^Blu(\d+)$",
    )

    # TODO: The "2" setting here is an "execute now" function...
    auto_image = generic_event_property(
        """\
        When Auto-Image is enabled and a new input frequency is detected, the DVS
        first applies an existing Auto Memory for the signal, or if no entry exists,
        performs and automatic Auto-Image on the new signal.
        """,
        int,
        get_cmd="55#",
        set_cmd="55*{0}#",
        set_cmd_response=r"^Img(\d+)$",
    )

    @property
    def temperature(self) -> float:
        """\
        Get the device temperature, in degrees Celcius.
        """
        return float(self.make_request("20S"))

    reconfig = generic_event_property(
        """\
        Event triggered by signal change.
        """,
        None,
        set_cmd_response=r"^Reconfig$",
    )
