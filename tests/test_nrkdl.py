#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import mock
from os.path import dirname, abspath, split, basename
import sys

sys.path.append(dirname(dirname(abspath(__file__))))

from nrkdl import NRK
import nrkdl
from utils import ppatch

# We dont want to download ANY files
NRK.dry_run = True

if sys.version_info >= (3, 0):
    PY3 = True
else:
    PY3 = False


def c_out(s):
    if not PY3:
        return s.encode('latin-1', 'ignore')
    else:
        return s


def test_search_live():
    r = NRK.search('brannman-sam')
    assert r[0].name == 'Brannmann Sam'


def test_program_live():
    r = NRK.program('msui22009314')
    assert r[0].full_title == 'Brannmann Sam 23:26'


@mock.patch('os.makedirs')
def test_download_live(*args):
    r = NRK.program('msui22009314')
    url, q, fp = r[0].download()  # add test for path
    folder, f = [basename(x) for x in split(fp)]

    assert url == 'http://nordond26c-f.akamaihd.net/i/no/open/12/12e45a2be69e24cb072f9d92a9c30727224ddd0e/7595713e-ee38-4325-8d05-c0ac2e2fd53c_,141,316,563,1266,2250,.mp4.csmil/master.m3u8?cc1=uri%3Dhttps%3a%2f%2fundertekst.nrk.no%2fprod%2fMSUI22%2f00%2fMSUI22009314AA%2fTMP%2fmaster.m3u8%7Ename%3DNorsk%7Edefault%3Dyes%7Eforced%3Dno%7Elang%3Dnb'
    assert q == 'high'
    assert f == 'Brannmann Sam 23_26'
    assert folder == 'Brannmann Sam'
    assert len(NRK.downloads()) == 1
    #NRK.downloads().start()


def test_series_live():
    r = NRK.series('brannmann-sam')
    assert r[0].name == 'Brannmann Sam'


def test_categories_live():
    r = NRK.categories()
    sl = [c.id for c in sorted(r, key=lambda v: v.id)]
    assert sl == ['all-programs', 'barn', 'dokumentar', 'drama-serier', 'film', 'humor',
                  'kultur', 'livsstil', 'natur', 'nyheter', 'samisk', 'sport', 'synstolk',
                  'tegnspraak', 'underholdning', 'vitenskap']


def test_programs_live():
    # r = NRK.programs()
    pass


def test_site_rip_live():
    # r = NRK.site_rip()
    pass


def test_parse_url_live():
    parsed = NRK.parse_url('https://tv.nrk.no/serie/skam/MYNT15001016/sesong-2/episode-10 http://tv.nrksuper.no/serie/lili/MSUI28008314/sesong-1/episode-3')
    assert len(parsed) == 2


def test_seasons_live():
    r = NRK.series('brannmann-sam')
    x = sorted([s.season_number for s in r[0].seasons()])
    assert x == [1, 2, 3, 4, 5]


@ppatch('program.json')
def p(item):
    return nrkdl.Episode(item)


def test_program_static():
    assert NRK.program('msui22009314')[0] == p()


#test_seasons_live()
#test_parse_url_live()
#test_download_live()
test_program_static()
#test_download_live()