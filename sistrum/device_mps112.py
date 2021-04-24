"""\
This module supports the Extron `MPS 112`_ and `MPS 112CS`_ Media Presentation Switchers.

These devices feature three A/V switchers:
    - Four inputs on HD15 connectors, capable of carrying RGBHV, RGBS, RGsB, or RsGsBs signals.
    - Four inputs on 4-pin mini DIN connectors, capable of carrying S-Video.
    - Four inputs on 4 BNC connectors, capable of carrying composite video.

These input groups are numbered ``1``, ``2``, and ``3``.

The device can operate in two modes:
    - "single" mode, where the device is treated as a single 12-input switch
    - "separate" mode, where the three switchers are independent and each group can output simultaneously.

Each of the twelve inputs has an associated audio input, and each group has an audio output. In addition,
there is a single "program out" that can output the audio from any group.

More information is available in the `user manual`_.

.. _MPS 112: https://www.extron.com/product/mps112
.. _MPS 112CS: https://www.extron.com/product/mps112cs
.. _user manual: https://www.extron.com/download/files/userman/MPS112_manual_revH_010507.pdf
"""

import re
from typing import Mapping, Union

from sistrum._protocol import ExtronProtocol
from sistrum._enums import ExecutiveMode, SwitcherMode
from sistrum._event import EnumValueConverter, generic_event_property
from sistrum._event import _ArrayEventProperty

__all__ = ["ExtronMPS112Protocol", "Status"]

_EXECUTIVE_MODE = EnumValueConverter(
    {
        "0": ExecutiveMode.UNLOCKED,
        "1": ExecutiveMode.LIMITED,
        "2": ExecutiveMode.COMPLETE,
    }
)

_SWITCHER_MODE = EnumValueConverter(
    {
        "1": SwitcherMode.SINGLE,
        "2": SwitcherMode.SEPARATE,
    }
)


class Status:
    mode: SwitcherMode
    input: Mapping[int, int]
    audio_group: int
    audio_input: int

    __slots__ = ("mode", "input", "audio_group", "audio_input")

    def __init__(
        self,
        mode: SwitcherMode,
        input: Mapping[int, int],  # pylint: disable=redefined-builtin
        audio_group: int,
        audio_input: int,
    ):
        #: switcher mode
        self.mode = mode
        #: current input per input group
        self.input = input
        #: source group for program audio
        self.audio_group = audio_group
        #: program audio input within group
        self.audio_input = audio_input


def _parse_status(line):
    pattern = re.compile(r"^Mod(\d) 1G(\d) 2G(\d) 3G(\d) 4G=(\d)G(\d)$")
    match = pattern.match(line)

    mode = _SWITCHER_MODE.to_api(match[1])

    return Status(
        mode=mode,
        input=dict(
            [
                (1, int(match[2])),
                (2, int(match[3])),
                (3, int(match[4])),
            ]
        ),
        audio_group=int(match[5]),
        audio_input=int(match[6]),
    )


def _separate_to_single_input(group: int, index: int) -> int:
    if index == 0:
        return 0
    else:
        return ((group - 1) * 4) + index


def _mic_volume_property_fset(self, value):
    if value >= 0:
        self.make_request("16*{0}G".format(value))
    else:
        self.make_request("16*{0}g".format(-value))


class _SwitchInputProperty(int, _ArrayEventProperty):  # pylint: disable=too-many-ancestors
    """\
    Integer proxy class to handle mixed single-switcher/separate-switcher syntax
    for ExtronMPS112Protocol.input.

    This is designed to be an object returned from the ``input`` property, so that
    we can support two different syntaxes:

    .. code-block: python

       x.input = <int>
       x.input[<int>] = <int>

    """

    def __new__(cls, parent):
        if isinstance(parent, ExtronMPS112Protocol):
            status = parent.status

            # look at the audio group and input to determine what input we use.
            # In single-switcher mode, this always matches up with the singular input.
            # In separate-switcher mode, it at least gives us a reasonable singular value.
            intval = _separate_to_single_input(status.audio_group, status.audio_input)

            self = super().__new__(cls, intval)
            return self
        else:
            raise ValueError("Not sure how to work with {0}".format(parent.__class__.__name__))

    def __init__(self, parent):
        def getitem(self, group_number) -> int:
            return self.status.input[group_number]

        def setitem(self, group_number, value) -> None:
            self.make_request("{0}*{1}!".format(group_number, value))

        super().__init__(parent=parent, indices=range(1, 4), fgetitem=getitem, fsetitem=setitem)

    def __copy__(self) -> Mapping[int, int]:
        # TODO: this makes copy.copy() work, but we lose the "works as an integer"
        return {k: v for k, v in self.items()}  # pylint: disable=unnecessary-comprehension


def _input_fget(self) -> Union[int, Mapping[int, int]]:
    return _SwitchInputProperty(parent=self)


def _input_fset(self, value) -> None:
    self.make_request("{0}!".format(value))


class ExtronMPS112Protocol(ExtronProtocol):
    """\
    This class implements the SIS Communication and Control protocol as documented
    in the `user manual`_.
    """

    @property
    def status(self) -> Status:
        """Retrieve the current status of the switcher."""
        return _parse_status(self.make_request("I"))

    input = generic_event_property(
        """\
        Input selection.

        This property can both be accessed as an integer value for single-switcher mode,
        as well as indexed for separate-switcher mode.

        When in seperate-switcher mode,

        .. code-block: python

           mps112.input = 7       # set input six (s-video #3)
           mps112.input[2] = 3    # set input three in group 2 (s-video)

           print(mps112.input)    # 7
           print(mps112.input[2]) # '3'

        """,
        int,
        range(1, 4),
        set_cmd="{index}*{0}!",
        set_cmd_response=r"^(\d+)*^(\d+)$",
        fget=_input_fget,
        fset=_input_fset,
    )

    volume = generic_event_property(
        """\
        Program audio volume, from 0 to 100.
        """,
        int,
        get_cmd="V",
        set_cmd="{0}V",
        set_cmd_response=r"^Vol(\d+)$",
    )

    mute = generic_event_property(
        """\
        Toggle program audio output on or off.

        Program audio output does not mute the microphone.
        """,
        int,
        get_cmd="Z",
        set_cmd="{0}Z",
        set_cmd_response=r"^Amt(\d+)$",
    )

    mic_volume = generic_event_property(
        """\
        The overall mic gain/attenuation, between -66 and 12.
        """,
        int,
        get_cmd="16G",
        fset=_mic_volume_property_fset,
        set_cmd_response=r"^Aud([+\-]\d+)$",
    )

    mic_mute = generic_event_property(
        """\
        Toggles the mic on or off.
        """,
        bool,
        get_cmd="M",
        set_cmd="{0}M",
        set_cmd_response=r"^Mix(\d+)$",
    )

    executive_mode = generic_event_property(
        """\
        Lock the front panel.

        If :const:`~sistrum.ExecutiveMode.UNLOCKED`, then the front panel is available for use.

        If :const:`~sistrum.ExecutiveMode.LIMITED`, then microphone controls are locked.

        If :const:`~sistrum.ExecutiveMode.COMPLETE`, then all front panel controls are locked.
        """,
        _EXECUTIVE_MODE,
        get_cmd="X",
        set_cmd="{0}X",
        set_cmd_response=r"^Exe(\d+)$",
    )

    switcher_mode = generic_event_property(
        """\
        Switcher mode.

        In :const:`~sistrum.SwitcherMode.SINGLE` mode, the MPS 112 emulates one switcher with 12
        inputs. When one input is selected, all others are disabled and muted.

        In :const:`~sistrum.SwitcherMode.SEPARATE` mode, there are three selection groups,
        corresponding to the three independent switches in the MPS 112. Each group has four
        inputs that can be chosen independently of the other groups. Only audio from one group
        is routed to program audio output.
        """,
        _SWITCHER_MODE,
        get_cmd="1#",
        set_cmd="{0}*1#",
        set_cmd_response=r"^Mod(\d+)$",
    )

    mic_threshold = generic_event_property(
        """\
        The mic talk-over threshold.

        Valid values range from 0 to 15; the default is 8.
        """,
        int,
        get_cmd="2#",
        set_cmd="{0}*2#",
        set_cmd_response=r"^Thr(\d+)$",
    )
