import asyncio
import datetime
from unittest import mock
import logging

import pytest

from cli import browse, expires_at, parse, search


#logging.basicConfig(level=logging.DEBUG)


async def resp(r):
    """Helper for side effect"""
    return r



def test_search(runner, nrk):
    nrk.cli = False
    with mock.patch('helpers.prompt_async', side_effect=[resp('0'), resp('1')]):
        with mock.patch('cli.prompt_async', side_effect=[resp('y')]):

            async def gogo():
                results = await search(nrk, 'skam')
                assert len(nrk.downloads())

            runner(asyncio.wait([gogo()]))


def test_expire_at(runner, fresh_nrk):
    today = datetime.date.today()
    next_mounth = today + datetime.timedelta(weeks=4)
    time_periode = '%s-%s' % (today.strftime("%d.%m.%Y"), next_mounth.strftime("%d.%m.%Y"))
    fresh_nrk.cli = False
    fresh_nrk.downloads().clear()

    with mock.patch('helpers.prompt_async', side_effect=[resp('0')]):
        with mock.patch('cli.prompt_async', side_effect=[resp('y')]):
            async def gogo():
                await expires_at(fresh_nrk, time_periode)
                assert len(fresh_nrk.downloads()) == 1

            runner(gogo())


def test_browse(runner, fresh_nrk):
    fresh_nrk.downloads().clear()
    fresh_nrk.cli = False
    with mock.patch('helpers.prompt_async', side_effect=[resp('0'), resp('0'), resp('0')]):
        with mock.patch('cli.prompt_async', side_effect=[resp('all'), resp('y')]):
            async def gogo():
                await browse(fresh_nrk)
                assert len(fresh_nrk.downloads()) == 1

            runner(gogo())

def test_parse(runner, fresh_nrk):
    fresh_nrk.cli = False
    fresh_nrk.downloads().clear()
    async def gogo():
        await parse(fresh_nrk, 'https://tv.nrk.no/serie/skam/MYNT15000117/sesong-4/episode-1 http://tv.nrksuper.no/serie/kash-og-zook'.split())
        assert len(fresh_nrk.downloads()) == 2

    runner(gogo())
