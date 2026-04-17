import math
import os

import pytest

from pyphantom import flex
from pyphantom.fakecam import state as fakecam_state


@pytest.fixture(scope="module")
def cam(request):
    c = flex.Phantom("127.0.0.1", 7115, "PH16")
    c.connect()

    def fin():
        c.disconnect()

    request.addfinalizer(fin)

    return c


def test_flag(cam):
    # Raw YAML can represent empty enum leaves as None; Flex round-trip uses "".
    def _empty_str_if_none(x):
        if isinstance(x, dict):
            return {k: _empty_str_if_none(v) for k, v in x.items()}
        return "" if x is None else x

    expected = _empty_str_if_none(fakecam_state["c1"]["state"])
    got = cam.ask("get c1.state")
    assert got == expected
    assert str(cam.structures.c1.state) == str(got)


def test_simple(cam):
    assert cam.ask("get fc0.res") == "2048 x 1152"
    assert str(cam.structures.fc0.res) == "2048 x 1152"


def test_simple_with_colon(cam):
    assert cam.ask("get fc0.meta.trigtc") == "11:40:46.11"
    assert str(cam.structures.fc0.meta.trigtc) == "11:40:46.11"


def test_dict(cam):
    expected = fakecam_state["defc"]
    assert cam.ask("get defc") == expected
    assert str(cam.structures.defc) == str(expected)


def test_parse_response_scientific_without_dot():
    """Multi-bracket Flex replies use yaml.load; -2e-06 must be float (not left as str by PyYAML)."""
    r = flex.parse_response(
        "Ok! fc0 : { adj : { rgamma : -2e-06, bgamma : -2e-06 } }"
    )
    assert isinstance(r["adj"]["rgamma"], float)
    assert isinstance(r["adj"]["bgamma"], float)
    assert math.isclose(r["adj"]["rgamma"], -2e-06, rel_tol=1e-9)
    assert math.isclose(r["adj"]["bgamma"], -2e-06, rel_tol=1e-9)


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
