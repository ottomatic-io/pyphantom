import math
import os

import pytest
import yaml

from pyphantom import flex
from pyphantom.flex import FlexLoader


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
    # c1 is deepcopy(fc1) after load_takes; take YAML uses `state : { STR }` -> dict
    assert cam.ask("get c1.state") == {"STR": ""}
    assert str(cam.structures.c1.state) == str({"STR": ""})


def test_simple(cam):
    assert cam.ask("get fc0.res") == "2048 x 1152"
    assert str(cam.structures.fc0.res) == "2048 x 1152"


def test_simple_with_colon(cam):
    assert cam.ask("get fc0.meta.trigtc") == "11:40:46.11"
    assert str(cam.structures.fc0.meta.trigtc) == "11:40:46.11"


def test_dict(cam):
    assert cam.ask("get defc") == {
        "aexpcomp": 0,
        "aexpmode": 0,
        "bcount": 0,
        "bperiod": 10416317,
        "decimation": 1,
        "edrexp": 0,
        "exp": 3333332,
        "frcount": 5000,
        "frsize": 2949120,
        "hqenable": 0,
        "meta": {"crop": 1, "h": 1080, "oh": 0, "ow": 0, "ox": 0, "oy": 0, "w": 1920},
        "ptframes": 1,
        "ramp": "",
        "rate": 150,
        "res": "2048 x 1152",
        "shoff": 0,
    }
    assert str(cam.structures.defc) == str(
        {
            "rate": 150,
            "res": "2048 x 1152",
            "exp": 3333332,
            "edrexp": 0,
            "ptframes": 1,
            "shoff": 0,
            "ramp": "",
            "bcount": 0,
            "bperiod": 10416317,
            "hqenable": 0,
            "decimation": 1,
            "frcount": 5000,
            "frsize": 2949120,
            "aexpmode": 0,
            "aexpcomp": 0,
            "meta": {"ox": 0, "oy": 0, "w": 1920, "h": 1080, "ow": 0, "oh": 0, "crop": 1},
        }
    )


def test_parse_response_scientific_without_dot():
    """Multi-bracket Flex replies use yaml.load; -2e-06 must be float (YAML 1.2), not str."""
    r = flex.parse_response(
        "Ok! fc0 : { adj : { rgamma : -2e-06, bgamma : -2e-06 } }"
    )
    assert isinstance(r["adj"]["rgamma"], float)
    assert isinstance(r["adj"]["bgamma"], float)
    assert math.isclose(r["adj"]["rgamma"], -2e-06, rel_tol=1e-9)
    assert math.isclose(r["adj"]["bgamma"], -2e-06, rel_tol=1e-9)


def test_flex_loader_inf_nan():
    """FlexLoader extends SafeLoader for YAML 1.2 Core .inf / .nan (not exercised by single-bracket parse_simple)."""
    doc = "X : { x : .inf, y : .nan, z : -2e-06 }"
    loaded = yaml.load(doc, Loader=FlexLoader)["X"]
    assert math.isinf(loaded["x"]) and loaded["x"] > 0
    assert math.isnan(loaded["y"])
    assert isinstance(loaded["z"], float)
    assert math.isclose(loaded["z"], -2e-06, rel_tol=1e-9)


def test_parse_response_fc0_fixture():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "fc0_flex_response.txt")
    with open(fixture_path, encoding="utf-8") as f:
        body = f.read()
    r = flex.parse_response("Ok! " + body)
    assert isinstance(r, dict)
    assert r["adj"]["gamma"] == 2.2
    assert isinstance(r["adj"]["rgamma"], float)
    assert isinstance(r["adj"]["bgamma"], float)
    assert math.isclose(r["adj"]["rgamma"], -2e-06, rel_tol=1e-9)
    assert math.isclose(r["adj"]["bgamma"], -2e-06, rel_tol=1e-9)
