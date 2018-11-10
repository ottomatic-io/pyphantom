import pytest

from pyphantom import flex


@pytest.fixture(scope="module")
def cam(request):
    c = flex.Phantom("127.0.0.1", 7115, "PH16")
    c.connect()

    def fin():
        c.disconnect()

    request.addfinalizer(fin)

    return c


# FIXME: Find a nicer way to test structures than calling `str()` on them
def test_flag(cam):
    assert cam.ask("get c1.state") == ["RDY"]
    assert str(cam.structures.c1.state) == str(["RDY"])


def test_simple(cam):
    assert cam.ask("get fc0.res") == "2048 x 1152"
    assert str(cam.structures.fc0.res) == "2048 x 1152"


def test_simple_with_colon(cam):
    assert cam.ask("get fc0.meta.trigtc") == "11:40:46.11"
    assert str(cam.structures.fc0.meta.trigtc) == "11:40:46.11"


def test_dict(cam):
    assert cam.ask("get defc") == {
        "exp": 1250000,
        "meta": {"crop": 0, "oh": 0, "ow": 0, "resize": 0},
        "rate": 400,
        "res": "4096x2304",
    }
    assert str(cam.structures.defc) == str(
        {"rate": 400, "res": "4096x2304", "exp": 1250000, "meta": {"crop": 0, "resize": 0, "ow": 0, "oh": 0}}
    )
