from decimal import Decimal
from fractions import Fraction
from functools import total_ordering
import math
import numbers
import re


__all__ = ["AspectRatio", "Resolution"]


_ASPECT_FORMAT = re.compile(r"^(\d+):(\d+)$")
_SMPTE_RESOLUTION_FORMAT = re.compile(r"^(\d+)([pi])(| Sharp| CVT)$")
_RESOLUTION_FORMAT = re.compile(r"^(\d+)x(\d+)$")


class AspectRatio(Fraction):
    """\
    This class implements an aspect ratio. This class works like Fraction,
    except it supports construction via an 'x:y' format, is stringified in
    'x:y' format, and is canonically in a normalized form.
    """

    __slots__ = ("_numerator", "_height")

    _numerator: int
    _denominator: int

    # We're immutable, so use __new__ not __init__
    def __new__(cls, numerator=0, denominator=None):
        """\
        Constructs an AspectRatio.

        Takes a string like '16:9', another Aspect instance,
        a numerator/height pair, or a float.
        """

        self = super(AspectRatio, cls).__new__(cls)

        if denominator is None:
            if isinstance(numerator, int):
                denominator = 1
                return self

            elif isinstance(numerator, numbers.Rational):
                numerator = numerator.numerator
                denominator = numerator.denominator
                return self

            elif isinstance(numerator, (float, Decimal)):
                numerator, denominator = numerator.as_integer_ratio()
                return self

            elif isinstance(numerator, str):
                match = _ASPECT_FORMAT.match(numerator)
                if match is None:
                    raise ValueError("Invalid literal for AspectRatio: %r" % numerator)
                numerator = int(match.group(1))
                denominator = int(match.group(2))

            else:
                raise TypeError("argument should be a string or Rational")

        elif isinstance(numerator, int) and isinstance(denominator, int):
            pass

        if denominator == 0:
            raise ZeroDivisionError("AspectRatio(%s, 0)" % numerator)

        gcd = math.gcd(numerator, denominator)
        numerator //= gcd
        denominator //= gcd
        self._numerator = numerator
        self._denominator = denominator
        return self

    def __str__(self):
        return "%s:%s" % (self._numerator, self._denominator)


@total_ordering
class Resolution:
    """
    Represents a resolution.

    A resolution has a width and a height, and has a selection of other attributes
    to describe timing parameters.

    A resolution can be constructed from a string like ``640x480`` or ``480p``,
    another Resolution instance, or a width/height pair with additional optional flags.
    """

    __slots__ = ("_width", "_height", "_interlaced", "_cvt", "_sharp")

    _width: int
    _height: int
    _interlaced: bool
    _cvt: bool
    _sharp: bool

    # We're immutable, so use __new__ not __init__
    def __new__(cls, width, height=None, interlaced=False, cvt=False, sharp=False):
        self = super().__new__(cls)

        if height is None:
            if isinstance(width, Resolution):
                # copy-construction
                self._width = width._width
                self._height = width._height
                self._interlaced = width._interlaced
                self._cvt = width._cvt
                self._sharp = width._sharp

            elif isinstance(width, str):
                # construction from string
                return Resolution.fromstring(width)

            else:
                raise TypeError("argument should be a string")
        else:
            self._width = width
            self._height = height
            self._interlaced = interlaced
            self._cvt = cvt
            self._sharp = sharp

        return self

    _SMPTE_RESOLUTIONS = [
        (720, 480),  # 480p
        (720, 576),  # 576p
        (1280, 720),  # 720p
        (1920, 1080),  # 1080p/1080i
    ]

    def _is_smpte_resolution(self) -> bool:
        return (self._width, self._height) in self._SMPTE_RESOLUTIONS

    @classmethod
    def fromstring(cls, string: str):
        match = _SMPTE_RESOLUTION_FORMAT.match(string)
        if match:
            for smpte_res in cls._SMPTE_RESOLUTIONS:
                if smpte_res[1] == int(match[1]):
                    interlaced = match[2] == "i"
                    sharp = match[3] == " Sharp"
                    cvt = match[3] == " CVT"
                    return Resolution(smpte_res[0], smpte_res[1], interlaced=interlaced, cvt=cvt, sharp=sharp)

        match = _RESOLUTION_FORMAT.match(string)
        if match:
            return Resolution(int(match[1]), int(match[2]))

        raise ValueError("Unable to parse resolution string: {0}".format(str))

    def __str__(self):
        if self._is_smpte_resolution():
            base = "{0}{1}".format(self.height, "i" if self.interlaced else "p")
        else:
            base = "{0}x{1}".format(self.width, self.height)

        if self.cvt:
            return "{0} CVT".format(base)
        elif self.sharp:
            return "{0} Sharp".format(base)
        else:
            return base

    def __repr__(self):
        return 'Resolution("{0}")'.format(self.__str__())

    @property
    def width(self) -> int:
        """Width, in pixels."""
        return self._width

    @property
    def height(self) -> int:
        """Height, in pixels."""
        return self._height

    @property
    def interlaced(self) -> bool:
        """Whether this resolution is interlaced (True) or progressive-scan (False)."""
        return self._interlaced

    @property
    def cvt(self) -> bool:
        """Whether this resolution uses VESA Coordinated Video Timings (True)."""
        return self._cvt

    @property
    def sharp(self) -> bool:
        """Whether this resolution is "sharp". (Extron does not define what this means.)"""
        return self._sharp

    def aspect_ratio(self) -> AspectRatio:
        """Return an object representing the aspect ratio of this resolution."""

        return AspectRatio(self._width, self._height)

    def _attrtuple(self):
        return (self._width, self._height, self._interlaced, self._cvt, self._sharp)

    def __eq__(self, other):
        return self._attrtuple() == other._attrtuple()

    def __lt__(self, other):
        return self._attrtuple() < other._attrtuple()

    def __hash__(self):
        return self._attrtuple().__hash__()
