#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import mock
import subprocess
import sys
from os.path import abspath, basename, dirname, getsize, split

sys.path.append(dirname(dirname(abspath(__file__))))

from nrkdl import NRK
import nrkdl
from utils import ppatch


# We dont want to download ANY files
nrk = NRK(dry_run=True, encoding='utf-8')

if sys.version_info >= (3, 0):
    PY3 = True
    ips = 'builtins.input'
else:
    PY3 = False
    ips = '__builtin__.raw_input'


def c_out(s):
    if not PY3:
        return s.encode('latin-1', 'ignore')
    else:
        return s


def q_clear():
    def outer(func):
        def inner(*args, **kwargs):
            try:
                func(*args, **kwargs)
            finally:
                nrk.downloads().clear()
        return inner
    return outer


def test_search_live():
    r = nrk.search('Kash og Zook')
    assert r[0].name == 'Kash og Zook'


def test_program_live():
    r = nrk.program('MSUS27001913')
    assert r[0].full_title == 'Kash og Zook S01E11'


@q_clear()
@mock.patch('os.makedirs')
def test_download_live(*args):
    r = nrk.program('MSUS27001913')

    url, q, fp = r[0].download()  # add test for path
    folder, f = [basename(x) for x in split(fp)]
    print(fp)
    assert url == 'http://nordond19b-f.akamaihd.net/i/wo/open/ec/ecbdad2e3fa4e5762e093c873ea2e3dd93529952/2fea3fe8-4c40-4ab9-9e60-3e52766c8e00_,563,1266,2250,.mp4.csmil/master.m3u8'
    assert q == 'high'
    assert f == 'Kash.og.Zook.S01E11.WEBDL-nrkdl'
    assert folder == 'Kash og Zook'
    assert len(nrk.downloads()) == 1


def test_series_live():
    r = NRK.series('kash-og-zook')
    print(r[0].name)
    assert r[0].name == 'Kash og Zook'


def test_categories_live():
    r = NRK.categories()
    sl = [c.id for c in sorted(r, key=lambda v: v.id)]
    assert sl == ['NRK-arkivet', 'all-programs', 'barn', 'dokumentar', 'drama-serier', 'film', 'humor',
                  'kultur', 'livsstil', 'natur', 'nyheter', 'samisk', 'sport', 'synstolk',
                  'tegnspraak', 'underholdning', 'vitenskap']


def test_programs_live():
    # r = NRK.programs()
    pass


def test_site_rip_live():
    # r = NRK.site_rip()
    pass


@q_clear()
@mock.patch('os.makedirs')
def test_parse_url_live(*args):
    """ tests parsing of the uri and fallbacks to html
        also tests the downloader and clearing the downloader
    """
    parsed = nrk.parse_url('https://tv.nrk.no/serie/skam') # https://tv.nrk.no/serie/skam/MYNT15001016/sesong-2/episode-10
    assert len(parsed) == 1
    assert len(nrk.downloads()) == 1
    # clean q.
    nrk.downloads().clear()
    assert len(nrk.downloads()) == 0


def test_seasons_live():
    r = NRK.series('brannmann-sam')
    x = sorted([s.season_number for s in r[0].seasons()])
    assert x == [1, 2, 3, 4, 5]

    eps_in_third_season = sorted([s for s in r[0].seasons()], key=lambda s: s.season_number)
    # find another way to test this as the result will be
    # invalid when nrk loose its usage rights to this season
    assert len(eps_in_third_season[2].episodes()) == 52


@q_clear()
@mock.patch('os.makedirs')
def test_console_live(*args, **kwargs):
    """ Try to download the last episode of brannman sam via cli """
    with mock.patch(ips, side_effect=['0', '0']):
        t = nrk._console('Brannmann Sam')
        assert len(t) == 1


@q_clear()
@mock.patch('os.makedirs')
def test_browse_live(*args, **kwargs):
    NRK.encoding = 'utf-8'
    with mock.patch(ips, side_effect=['0', '0', '0', 'y', 'y']):
        t = nrk._browse()
        assert len(t) == 1


def test_channels_live():
    assert len(NRK.channels()) == 5


@q_clear()
@mock.patch('os.makedirs')
@ppatch('from_file.txt')
def test_from_file_static(f, *args):
    parsed = nrk._from_file(f)
    assert len(parsed) == 2
    assert len(nrk.downloads()) == 2
    # clean q.
    nrk.downloads().clear()
    assert len(nrk.downloads()) == 0


@ppatch('program.json')
def p(item):
    return nrkdl.Episode(item)


def test_program_static():
    assert NRK.program('MSUS27001913')[0] == p()


def test_console_select_static():
    d = {'name': 'word',
         'cookie': 'monster'}

    stuff = []
    dicts = []
    classes = []

    for i in range(10):
        dicts.append(d)
        classes.append(p())

    stuff.append(dicts)
    stuff.append(classes)
    # test more shit

    for s in stuff:
        with mock.patch(ips, return_value='::'):
            x = nrkdl._console_select(s, ['name'])
            assert len(x) == 10  # we kinda assume 10 eps exist here..


@ppatch('program.json')
def test_build_static(item):
    serie = nrkdl._build(item)
    assert serie.type == 'serie'

def test_subtitle_from_episode_from_live():
    show = nrk.program('MSUB19120616')[0]
    assert getsize(show.subtitle()) > 0


def test_if_ffmpeg_is_installed_static():
    pass
    #assert subprocess.check_call('ffmpeg -h', shell=False) == 0


# test_seasons_live()
# test_parse_url_live()
# test_download_live()
# test_series_live()
# test_program_static()
# test_download_live()
# test_from_file_static()
# test_console_select_static()
# test_console_live()
# test_browse_live()
# test_console_select_static()
# test_build_static()
# test_subtitle_from_episode_from_static()
# test_seasons_live()
# test_channels_live()
# test_download_live()
