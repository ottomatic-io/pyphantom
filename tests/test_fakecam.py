from pyphantom import fakecam

state = {'string': 'some string',
         'integer': 2,
         'taglist': ['RDY', 'ACT'],
         'subdict': {'string': 'another string',
                     'integer': 3,
                     'subsubdict': {'substring': 'blaa'}}}


def test_simple():
    assert fakecam.get(state, 'string') == 'string : "some string"'
    assert fakecam.get(state, 'integer') == 'integer : 2'
    assert fakecam.get(state, 'taglist') == 'taglist : { RDY ACT }'


def test_subdict_direct():
    assert fakecam.get(state, 'subdict.string') == 'string : "another string"'
    assert fakecam.get(state, 'subdict.integer') == 'integer : 3'


def test_subdict_whole():
    assert fakecam.get(state, 'subdict') == 'subdict : { integer : 3, subsubdict : { substring : "blaa" }, ' \
                                            'string : "another string" }'
