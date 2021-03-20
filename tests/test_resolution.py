from sistrum._resolution import Resolution, AspectRatio
import pytest


def test_str():
    assert str(Resolution(640, 480)) == "640x480"
    assert str(Resolution(800, 600)) == "800x600"
    assert str(Resolution(720, 480)) == "480p"
    assert str(Resolution(720, 576)) == "576p"
    assert str(Resolution(1280, 720)) == "720p"
    assert str(Resolution(1920, 1080)) == "1080p"
    assert str(Resolution(1920, 1080, interlaced=True)) == "1080i"


def test_comparisons():
    assert Resolution(640, 480) == Resolution(640, 480)
    assert Resolution(640, 480) != Resolution(480, 640)
    assert Resolution(640, 480) < Resolution(640, 500)
    assert Resolution(800, 600) > Resolution(640, 480)
    assert Resolution(800, 600) >= Resolution(640, 480)
    assert Resolution(800, 600) >= Resolution(800, 600)


def test_fromstring():
    assert Resolution("640x480") == Resolution(640, 480)
    assert Resolution("800x600") == Resolution(800, 600)
    assert Resolution("480p") == Resolution(720, 480)
    assert Resolution("576p") == Resolution(720, 576)
    assert Resolution("720p") == Resolution(1280, 720)
    assert Resolution("1080p") == Resolution(1920, 1080)
    assert Resolution("1080i") == Resolution(1920, 1080, interlaced=True)
    assert Resolution("1080p Sharp") == Resolution(1920, 1080, sharp=True)
    assert Resolution("1080p CVT") == Resolution(1920, 1080, cvt=True)

    with pytest.raises(ValueError):
        Resolution("-200x-300")

    with pytest.raises(ValueError):
        Resolution("200y300")

    with pytest.raises(ValueError):
        Resolution("200x300x400")


def test_bonus_modifiers():
    assert str(Resolution("1080p Sharp")) == "1080p Sharp"
    assert str(Resolution("1080p CVT")) == "1080p CVT"


def test_resolution_repr():
    assert Resolution("1080p Sharp").__repr__() == 'Resolution("1080p Sharp")'
    assert Resolution("1080p CVT").__repr__() == 'Resolution("1080p CVT")'
    assert Resolution("640x480").__repr__() == 'Resolution("640x480")'


def test_from_other_resolution():
    assert Resolution(Resolution(640, 480)) == Resolution(640, 480)


def test_from_bad_type():
    with pytest.raises(TypeError):
        assert Resolution(1.5)

    with pytest.raises(TypeError):
        assert Resolution([1, 2, 3])

    with pytest.raises(TypeError):
        assert Resolution((1, 2, 3))


def test_hash():
    assert hash(Resolution(640, 480)) == hash(Resolution(640, 480))
    assert hash(Resolution(640, 480)) != hash(Resolution(800, 600))
    assert hash(Resolution(1920, 1080, sharp=True)) != hash(Resolution(1920, 1080))
    assert hash(Resolution(1920, 1080, interlaced=True)) != hash(Resolution(1920, 1080))


def test_aspect_ratio():
    assert AspectRatio(4, 3) == AspectRatio(4, 3)
    assert AspectRatio(4, 3).numerator == 4
    assert AspectRatio(4, 3).denominator == 3
    assert str(AspectRatio(4, 3)) == "4:3"
    assert AspectRatio("4:3") == AspectRatio(4, 3)
    assert str(AspectRatio("400:300")) == "4:3"
    assert str(AspectRatio(400, 300)) == "4:3"

    with pytest.raises(ValueError):
        AspectRatio("-1:1")

    with pytest.raises(ValueError):
        AspectRatio("1:-1")

    with pytest.raises(ZeroDivisionError):
        AspectRatio("1:0")

    with pytest.raises(TypeError):
        AspectRatio("1", "0")


def test_res_aspect_ratio():
    assert Resolution(640, 480).aspect_ratio() == AspectRatio(4, 3)
    assert Resolution(1920, 1080).aspect_ratio() == AspectRatio(16, 9)
