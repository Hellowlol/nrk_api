#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from nrkdl import NRK


async def example_search():
    nrk = NRK()
    search_results = await nrk.search('Brannman Sam')
    for search in search_results:
        for season in search.seasons():
            for episode in await season.episodes():
                await episode.download()
                episode.subtitle()

    print('We found %s episodes to download' % len(nrk.downloads()))
    nrk.dry_run = True
    await nrk.downloads().start()

# example_search()


async def example_site_rip(date=None):
    """ Please, dont do this.. """
    nrk = NRK()
    all_programs = await nrk.site_rip()

    for media in all_programs:
        if media.type == 'serie':
            for serie in await media.episodes():
                await serie.download()
        else:
            await media.download()

    #await nrk.downloads().start()

#example_site_rip()


async def example_parse_url():
    # This starts downloading right away
    await NRK().parse_urls('https://tv.nrk.no/serie/skam/MYNT15001016/sesong-2/episode-10 http://tv.nrksuper.no/serie/lili/MSUI28008314/sesong-1/episode-3')

#example_parse_url()

