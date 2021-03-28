from enum import Enum, unique


__all__ = ["PartNumber"]


@unique
class PartNumber(str, Enum):
    """A list of Extron part numbers.

    The SIS protocol generically has a ``N`` command that returns a part
    number; because of this, we use part numbers to identify device models.
    """

    #: Extron MPS 112
    EXTRON_MPS_112 = "60-532-01"

    #: Extron MPS 112CS
    EXTRON_MPS_112CS = "60-532-02"

    #: Extron DVS 304
    EXTRON_DVS_304 = "60-736-01"

    #: Extron DVS 304 A
    EXTRON_DVS_304_A = "60-736-02"

    #: Extron DVS 304 D
    EXTRON_DVS_304_D = "60-736-03"

    #: Extron DVS 304 AD
    EXTRON_DVS_304_AD = "60-736-04"

    #: Extron DVS 304 DVI
    EXTRON_DVS_304_DVI = "60-1027-01"

    #: Extron DVS 304 DVI A
    EXTRON_DVS_304_DVI_A = "60-1027-02"

    #: Extron DVS 304 DVI D
    EXTRON_DVS_304_DVI_D = "60-1027-03"

    #: Extron DVS 304 DVI AD
    EXTRON_DVS_304_DVI_AD = "60-1027-04"
