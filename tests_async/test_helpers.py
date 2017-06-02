# test_helpers
import datetime
from helpers import clean_name, parse_datestring, parse_uri


def test_clean_name():
    s = 'l-/\?%\*|"<>::ol'

    assert clean_name(s) == 'l__ol'


def test_utils_parse_datestring():
    single_dot = parse_datestring('01.01.1970')
    assert single_dot == (datetime.datetime(1970, 1, 1, 23, 59), None)

    single_dash = parse_datestring('01-01-1970')
    assert single_dash == (datetime.datetime(1970, 1, 1, 23, 59), None)

    ans_range = (datetime.datetime(1970, 1, 1, 23, 59), datetime.datetime(1970, 5, 1, 23, 59))
    range_dot = parse_datestring('01.01.1970 - 01.05.1970')
    assert range_dot == ans_range

    range_dash = parse_datestring('01.05.1970 01-01-1970')
    assert range_dash == ans_range

    assert parse_datestring('01.05.1970.0101-1970') == ans_range


def test_parse_uri():
    # This will fails since we have to download the http
    # page to get the id
    assert None in list(parse_uri('https://tv.nrk.no/serie/skam'))
    assert 'MYNT15000917' in list(parse_uri('https://tv.nrk.no/serie/skam/MYNT15000917/sesong-4/episode-9'))
    assert 'KOID75007816' in list(parse_uri('https://tv.nrk.no/program/KOID75007816/drifting-livet'))
    assert '232953' in list(parse_uri('https://www.nrk.no/skole/?mediaId=21221&page=objectives&subject=norsk&objective=K15393'))
    # test for the old ps format when you find a link
