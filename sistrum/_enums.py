from enum import Enum, unique


@unique
class TestPattern(str, Enum):
    """
    Test patterns.

    Not all devices support all test patterns.
    """

    #: No test pattern
    OFF = "off"

    #: A pattern with alternating pixels making horizontal bars, used to adjust clock and phase.
    #:
    #: .. raw:: html
    #:
    #:     <table class="testpattern alternating-lines"><tr><td></td></tr></table>
    ALTERNATING_LINES = "alternating-lines"

    #: A pattern with alternating pixels making vertical bars, used to adjust clock and phase.
    #:
    #: .. raw:: html
    #:
    #:     <table class="testpattern alternating-pixels"><tr><td></td></tr></table>
    ALTERNATING_PIXELS = "alternating-pixels"

    #: A pattern used to calibrate color settings on the display.
    #:
    #: .. raw:: html
    #:
    #:     <div class="aspect aspect-1_33"><div></div></div>
    ASPECT_1_33 = "aspect-1.33"

    #: A pattern used to center the output on the display.
    #:
    #: .. raw:: html
    #:
    #:     <div class="aspect aspect-1_78"><div></div></div>
    ASPECT_1_78 = "aspect-1.78"

    #: A pattern used to center the output on the display.
    #:
    #: .. raw:: html
    #:
    #:     <div class="aspect aspect-1_85"><div></div></div>
    ASPECT_1_85 = "aspect-1.85"

    #: A pattern used to center the output on the display.
    #:
    #: .. raw:: html
    #:
    #:     <div class="aspect aspect-2_35"><div></div></div>
    ASPECT_2_35 = "aspect-2.35"

    #: A pattern used to calibrate color settings on the display.
    #:
    #: .. raw:: html
    #:
    #:     <table class="testpattern color-bars">
    #:        <tr>
    #:           <td class="bar0"></td>
    #:           <td class="bar1"></td>
    #:           <td class="bar2"></td>
    #:           <td class="bar3"></td>
    #:           <td class="bar4"></td>
    #:           <td class="bar5"></td>
    #:           <td class="bar6"></td>
    #:           <td class="bar7"></td>
    #:        </tr>
    #:        <tr>
    #:           <td class="bar7"></td>
    #:           <td class="bar6"></td>
    #:           <td class="bar5"></td>
    #:           <td class="bar4"></td>
    #:           <td class="bar3"></td>
    #:           <td class="bar2"></td>
    #:           <td class="bar1"></td>
    #:           <td class="bar0"></td>
    #:        </tr>
    #:     </table>
    COLOR_BARS = "color-bars"

    #: A pattern with one-pixel lines on all four borders.
    #:
    #: .. raw:: html
    #:
    #:     <div class="aspect crop"><div></div></div>
    CROP = "crop"

    CROSSHATCH = "crosshatch"

    CROSSHATCH_4X4 = "crosshatch-4x4"

    #: A pattern used to calibrate brightness and grayscale settings on the display.
    #:
    #: .. raw:: html
    #:
    #:     <table class="testpattern grey-bars">
    #:        <tr>
    #:           <td class="bar0"></td>
    #:           <td class="bar1"></td>
    #:           <td class="bar2"></td>
    #:           <td class="bar3"></td>
    #:           <td class="bar4"></td>
    #:           <td class="bar5"></td>
    #:           <td class="bar6"></td>
    #:           <td class="bar7"></td>
    #:        </tr>
    #:        <tr>
    #:           <td class="bar7"></td>
    #:           <td class="bar6"></td>
    #:           <td class="bar5"></td>
    #:           <td class="bar4"></td>
    #:           <td class="bar3"></td>
    #:           <td class="bar2"></td>
    #:           <td class="bar1"></td>
    #:           <td class="bar0"></td>
    #:        </tr>
    #:     </table>
    GRAYSCALE = "grayscale"

    #: A pattern with alternating pixels making vertical bars, used to adjust clock and phase.
    #:
    #: .. raw:: html
    #:
    #:     <table class="testpattern grayscale-ramp"><tr><td></td></tr></table>
    GRAYSCALE_RAMP = "grayscale-ramp"

    #: A pattern that is full-white.
    #:
    #: .. raw:: html
    #:
    #:     <table class="testpattern white-field"><tr><td></td></tr></table>
    WHITE_FIELD = "white-field"


@unique
class InputStandard(str, Enum):
    """Input standard."""

    #: No input
    NONE = "none"

    #: NTSC 3.58
    NTSC_3_58 = "ntsc-3.58"

    #: PAL
    PAL = "pal"

    #: NTSC 4.43
    NTSC_4_43 = "ntsc-4.43"

    #: SECAM
    SECAM = "secam"

    #: Other (often used for "RGB or HDTV")
    OTHER = "other"


@unique
class InputVideoFormat(str, Enum):
    NONE = "none"

    #: CVBS (also known as Composite, or sometimes simply "Video")
    CVBS = "cvbs"

    #: S-Video (also known as "separate video" or "Y/C")
    SVIDEO = "svideo"

    #: RGB with sync-on-composite (composite video sync)
    RGBCVS = "rgbcvs"

    #: RGB with composite sync
    RGBS = "rgbs"

    #: RGB with horizontal and vertical sync on separate lines
    RGBHV = "rgbhv"

    #: RGB with sync-on-green
    RGSB = "rgsb"

    RGB_SCALED = "rgb-scaled"

    #: RGB, but with no manipulation of the input data
    RGB_PASSTHROUGH = "rgb-passthrough"

    #: Component video (also known as YUV or YPbPr) that is interlaced
    YUV_I = "yuv-i"

    #: Component video (also known as YUV or YPbPr) that is progressive-scan
    YUV_P = "yuv-p"

    #: Component video where the scan is autodetected
    YUV_AUTO = "yuv-auto"

    #: Serial Digital Interface
    SDI = "sdi"

    #: DVI
    DVI = "dvi"

    #: HDMI
    HDMI = "hdmi"


@unique
class SyncFormat(str, Enum):
    #: RGB, with Horizontal and Vertical sync on dedicated channels (aka VGA)
    RGBHV = "rgbhv"

    #: RGB, with composite horizontal/vertical sync
    RGBS = "rgbs"

    #: RGB, with sync-on-green
    RGSB = "rgsb"

    #: Component, aka "Y, R-Y, B-Y"
    YUV_BILEVEL = "yuv-bilevel"

    #: Component, aka "Y, R-Y, B-Y"
    YUV_TRILEVEL = "yuv-trilevel"


@unique
class AspectMode(str, Enum):
    """Aspect mode determines how an input should fill the output."""

    #: The input should preserve its native aspect ratio.
    FOLLOW = "follow"

    #: The input should fill the entire raster output.
    FILL = "fill"


@unique
class SyncPolarity(str, Enum):
    NEGATIVE = "negative"
    POSITIVE = "positive"


@unique
class ExecutiveMode(str, Enum):
    """Executive Mode is used to lock front panel controls."""

    #: Front panel controls are unlocked.
    UNLOCKED = "unlocked"

    #: Some front panel controls are locked. Which controls are locked will vary by device.
    LIMITED = "limited"

    #: All front panel controls are locked.
    COMPLETE = "complete"


@unique
class SwitcherMode(str, Enum):
    SINGLE = "single"
    SEPARATE = "separate"
