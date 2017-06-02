# test api
from os.path import basename, getsize
from unittest import mock
import pytest

import asyncio



def test_search(runner, nrk):
    nrk = runner(nrk.search('skam', strict=True))
    assert len(nrk) == 1
    assert nrk[0].title == 'SKAM'


def test_program(runner, nrk):
    nrk = runner(nrk.program('MYNT15000717'))
    assert nrk.id == 'mynt15000717'


#@mock.patch('os.makedirs') fix the patch
def  test_parse_url(runner, nrk):
    nrk = runner(nrk.parse_url(['https://tv.nrk.no/serie/skam']))
    dl_link, _, fn = nrk[0]
    assert dl_link
    assert basename(fn) == 'SKAM.S04E07.WEBDL-nrkdl'


def test_series(runner, nrk):
    r = runner(nrk.series('kash-og-zook'))
    assert r.name == 'Kash og Zook'


def test_seasons(runner, nrk):
    r = runner(nrk.series('brannmann-sam'))
    x = sorted([s.season_number for s in r.seasons()])
    assert x == [1, 2, 3, 4, 5]

    eps_in_third_season = sorted([s for s in r.seasons()], key=lambda s: s.season_number)
    # find another way to test this as the result will be
    # invalid when nrk loose its usage rights to this season
    assert len(runner(eps_in_third_season[2].episodes())) == 52


def test_categories(runner, nrk):
    r = runner(nrk.categories())
    sl = [c.id for c in sorted(r, key=lambda v: v.id)]
    assert sl == ['Familie', 'NRK-arkivet', 'all-programs', 'barn',
                  'dokumentar', 'drama-serier', 'film', 'humor', 'kultur',
                  'livsstil', 'natur', 'nyheter', 'samisk', 'sport', 'synstolk',
                  'tegnspraak', 'underholdning', 'vitenskap']



def _test_subtitle_from_episode(runner, nrk): # TODO
    show = runner(nrk.program('MSUB19120616'))
    assert getsize(show.subtitle()) > 0


def test_site_rip(runner, nrk):
    rip = runner(nrk.site_rip())
    assert len(rip)

def test_popular_programs(runner, nrk):
    x = runner(nrk.popular_programs())

def test_programs(runner, nrk):
    all_programs = runner(nrk.programs())
    assert len(all_programs)

def test_channels(runner, nrk):
    channels = runner(nrk.channels())
    ch = sorted(channels, key=lambda k: k.title)
    nrk1 = ch[1]
    assert nrk1.title == 'NRK1'
    assert len(ch) == 4

def test_download(runner, nrk):
    nrk.dry_run = False
    nrk.cli = True
    async def gogo():
        p = await nrk.program('MYNT15000717')
        info = await p.download()
        await nrk.dl(info)

    runner(gogo())

"""
def test_download_all(runner, nrk):
    nrk.dry_run = False
    async def gogo():
        one = await nrk.program('MYNT15000717')
        dl_one = await one.download()
        #two = await nrk.program('MSUB19120616')
        #dl_two = await two.download()

        tasks = [dl_one]#dl_two]
        f = await nrk._download_all(tasks)
        return f

    runner(gogo())
"""
