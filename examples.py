#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import os
from datetime import datetime
from nrkdl import NRK


def example_search():
    nrk = NRK()
    search_results = nrk.search('Brannman Sam')
    for search in search_results:
        for season in search.seasons():
            for episode in season.episodes():
                episode.download()
                episode.subtitle()

    print('We found %s episodes to download' % len(nrk.downloads()))
    nrk.dry_run = True
    nrk.downloads().start()

# example_search()


def example_site_rip(date=None):
    """ Please, dont do this.. """
    nrk = NRK()
    all_programs = nrk.site_rip()

    for media in all_programs:
        if media.type == 'serie':
            for serie in media.episodes():
                serie.download()
        else:
            media.download()

    #nrk.downloads().start()

#example_site_rip()


def download_since(date=None, category=None, media_type=None, download=False, save_path=None):
    from nrkdl import SAVE_PATH

    if date is None:
        date = datetime.now().date()
    else:
        date = datetime.strptime(date, '%d.%m.%Y')

    if save_path is None:
        save_path = os.path.join(SAVE_PATH, str(date))

    try:
        os.makedirs(save_path)
    except OSError:
        if not os.path.isdir(save_path):
            raise

    nrk = NRK(save_path=save_path, cli=True)

    expires_soon = []

    all_programs = nrk.site_rip()

    for media in all_programs:
        if media.type == 'serie' and media_type is None or media_type == 'serie':
            for ep in media.episodes():
                if category:
                    if category != ep.category.name:
                        continue
                try:
                    aired = datetime.fromtimestamp(int(ep.data.get('usageRights', {}).get('availableTo', 0) / 1000), None)
                except (ValueError, OverflowError, OSError):
                    aired = None

                if aired:
                    if aired.date() == date:
                        expires_soon.append(ep)

        else:
            if category:
                if category != media.category.name:
                    continue

            if media_type:
                if media_type != media.type:
                    continue

            try:
                aired = datetime.fromtimestamp(int(media.data.get('usageRights', {}).get('availableTo', 0) / 1000), None)
            except (ValueError, OverflowError, OSError):
                aired = None

            if aired:
                if aired.date() == date:
                    expires_soon.append(media)

    print('%s mediaitems expires today' % len(expires_soon))
    if download and expires_soon:
        for f in expires_soon:
            f.download()
            print('Adding %s to download que' % f.full_title.encode('utf-8'))

        if nrk.downloads():
            nrk.downloads().start()

#download_since()


def example_parse_url():
    # This starts downloading right away
    NRK().parse_urls('https://tv.nrk.no/serie/skam/MYNT15001016/sesong-2/episode-10 http://tv.nrksuper.no/serie/lili/MSUI28008314/sesong-1/episode-3')

#example_parse_url()


