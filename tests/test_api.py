# test api
import datetime
from functools import partial
from os.path import basename, getsize
from unittest import mock
import pytest

import asyncio



def test_search(runner, nrk):
    nrk = runner(nrk.search('skam', strict=True))
    assert len(nrk) == 1
    assert nrk[0].title == 'SKAM'


def test_program(runner, nrk): # fixme
    program = runner(nrk.program('msus27003613'))


#@mock.patch('os.makedirs') fix the patch
def test_parse_url(runner, nrk):
    nrk.cli = False
    result = runner(nrk.parse_url(['https://tv.nrk.no/serie/skam/MYNT15000117/sesong-4/episode-1',
                                   'http://tv.nrksuper.no/serie/kash-og-zook']))
    result = sorted(result, key=lambda k: k[2])
    dl_link, _, fn = result[1]
    assert dl_link
    assert basename(fn) == 'SKAM.S04E01.WEBDL-nrkdl'
    assert len(result) == 2


def test_series(runner, nrk):
    async def gogo():

        serie = await nrk.series('kash-og-zook')
        assert serie.name == 'Kash og Zook'
        assert serie.title == serie.name == 'Kash og Zook'
        assert serie.image_id == 'B1ic3I62vTH1__3jBABKnA16GCgkzGAjTR-3YIHPd25A'
        assert serie.season_ids == [{"id": 77862, "name": "Sesong 2"},{"id": 77282, "name": "Sesong 1"}]
        assert serie.category.id == 'barn'
        assert serie.description
        eps = await serie.episodes()
        assert len(eps)
    runner(gogo())


def test_seasons(runner, nrk):
    r = runner(nrk.series('brannmann-sam'))
    x = sorted([s.season_number for s in r.seasons()])
    assert x == [1, 2, 3, 4, 5]

    eps_in_third_season = sorted([s for s in r.seasons()], key=lambda s: s.season_number)
    # find another way to test this as the result will be
    # invalid when nrk loose its usage rights to this season
    async def lol():
        s3 = eps_in_third_season[2]
        s3_eps = await s3.episodes()
        assert len(s3_eps) == 52
    runner(lol())


def test_categories(runner, nrk):
    r = runner(nrk.categories())
    sl = [c.id for c in sorted(r, key=lambda v: v.id)]
    assert sl == ['Familie', 'NRK-arkivet', 'all-programs', 'barn',
                  'dokumentar', 'drama-serier', 'film', 'humor', 'kultur',
                  'livsstil', 'natur', 'nyheter', 'samisk', 'sport', 'synstolk',
                  'tegnspraak', 'underholdning', 'vitenskap']



def test_subtitle_from_episode(runner, nrk): # TODO

    async def lol():
        ep = await nrk.program('MSUB19120616')
        srt = await ep.subtitle()
        assert getsize(srt) > 0

    runner(lol())

# add slow
def _test_site_rip(runner, nrk):
    rip = runner(nrk.site_rip())
    assert len(rip)


def test_popular_programs(runner, nrk):
    x = runner(nrk.popular_programs())
    assert len(x)


def test_recent_programs(runner, nrk):
    x = runner(nrk.recent_programs())
    assert len(x)


def test_recommended_programs(runner, nrk):
    x = runner(nrk.recommended_programs())
    assert len(x)


def test_programs(runner, nrk):
    all_programs = runner(nrk.programs())
    assert len(all_programs)


def test_channels(runner, nrk):
    channels = runner(nrk.channels())
    ch = sorted(channels, key=lambda k: k.title)
    nrk1 = ch[1]
    assert nrk1.title == 'NRK1'
    assert len(ch) == 4


def _test_download(runner, nrk): # This test works but hangs in pytest
    nrk.dry_run = True
    nrk.cli = False

    async def gogo():
        p = await nrk.program('MYNT15000717')
        info = await p.download()
        k = await nrk.dl(info)

    runner(gogo())


def _test_download_all(runner, nrk):
    nrk.dry_run = True

    async def gogo():
        one = await nrk.program('MYNT15000717')
        dl_one = await one.download()
        two = await nrk.program('MSUB19120616')
        dl_two = await two.download()

        tasks = [dl_one, dl_two]
        f = await nrk._download_all(tasks)
        assert len(f) == 2
        return f

    runner(gogo())


def test_downloader(runner, nrk):
    async def gogo():
        episode = await nrk.program('MYNT15000717')
        assert episode.available is True
        assert episode.category
        assert episode.description == '– Det er noen som angriper oss.'
        assert episode.duration == 2202400
        assert episode.ep_name == '7:10'
        assert episode.file_name == 'SKAM.S04E07.WEBDL-nrkdl'
        #assert episode.file_path == 'C:\Users\alexa/nrkdl\SKAM\SKAM.S04E07.WEBDL-nrkdl'
        assert episode.full_title == 'SKAM S04E07'
        assert episode.geo_blocked is True
        assert episode.has_subtitle is True
        assert episode.id == 'mynt15000717'
        assert episode.image_id == 'TEFdD69m0SjyvkknfPsMvgncdCcMW-aiJbQG-iSCHb3g'
        assert episode.legal_age == '12'
        assert episode.name == 'SKAM'
        assert episode.relative_origin_url == 'serie/skam/MYNT15000717/sesong-4/episode-7'
        assert episode.season_number == 91415
        assert episode.series_id == 'skam'
        assert episode.title == 'SKAM'
        assert episode.type == 'episode'

        await episode.download()

        dlr = nrk.downloads()
        assert len(dlr) == 3
        dlr.clear()
        assert not len(dlr)

    runner(gogo())


#@pytest.mark.slow
def test_expires_at(runner, nrk):
    today = datetime.date.today()
    next_mounth = today + datetime.timedelta(weeks=4)
    time_periode = '%s-%s' % (today.strftime("%d.%m.%Y"), next_mounth.strftime("%d.%m.%Y"))

    async def gogo():
        media_that_expires = await nrk.expires_at(time_periode)
        assert len(media_that_expires)

    runner(gogo())
