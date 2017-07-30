import asyncio
import datetime
import os
import logging
import re
import sys

from asyncio.streams import IncompleteReadError
from functools import partial
from urllib.parse import quote_plus

import tqdm

from .httpz import httpclient
from .helpers import parse_uri, to_ms, progress_bars, parse_datestring
from .classes import *


__all__ = ['NRK']

LOG = logging.getLogger(__file__)
SAVE_PATH = os.path.expanduser('~/nrkdl')
_build = build  # fixme


if sys.platform == 'win32':  # pragma: no cover
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)


class NRK:
    """Main class for the api."""

    def __init__(self, dry_run=False, client=None,
                 save_path=None, subtitle=False, cli=False):

        self.dry_run = dry_run
        self.client = client or httpclient
        self.subs = subtitle
        self.cli = cli

        # Set a default ssl path
        self.save_path = save_path or SAVE_PATH
        self.q = asyncio.Queue()

        # Make sure the save_path exist
        os.makedirs(self.save_path, exist_ok=True)

    async def series(self, series_id):
        return Series(await self.client('series/%s' % series_id), nrk=self)

    async def channels(self):
        return [Channel(data, nrk=self) for data in await self.client('channels/')
                if data.get('title') != 'alle']

    async def programs(self, category_id='all-programs'):
        items = await self.client('categories/%s/programs' % category_id)
        return [_build(item, nrk=self) for item in items
                if item.get('title', '').strip() != '' and
                item['programId'] != 'notransmission']

    async def auto_complete(self, q):
        return await self.client('autocomplete?query=%s' % q)

    async def program(self, program_id):
        """ Get details about a program/series """
        item = await self.client('programs/%s' % program_id)
        if item.get('seriesId', '').strip():
            return Episode(item, nrk=self)
        else:
            return Program(item, nrk=self)

    async def search(self, query, raw=False, strict=False):
        """ Search nrk for stuff
            Params:
                    raw(bool): used by cli,
                    strict(bool): limit the search to a exact match
            Returns:
                    If raw is false it will return a Program, Episode or Serie,
                    else json
        """
        LOG.debug('Searching for %s', query)
        response = await self.client('search/%s' % quote_plus(query))
        if response:
            if strict:
                response['hits'] = [item for item in response.get('hits', [])
                                    if item.get('hit', {}).get('title', '').lower() == query.lower()]

            if not raw:
                f = [_build(item, nrk=self) for item in response['hits'] if item]
                return f
            else:
                return response
        return []

    def downloads(self):
        """Used for manage downloads."""
        return Downloader(self)

    async def dl(self, item, bar_nr=1):
        """Downloads a media file

           Args:
                item(tuple) = Fx ('url', 'q', 'path/to/file')
        """
        url, quality, filename = item

        if self.dry_run:
            print('Should have downloaded %s because but didnt because of -dry_run\n' % filename)
            return

        q = '' if self.cli else '-loglevel quiet '
        cmd = 'ffmpeg %s-i %s -n -vcodec copy -acodec ac3 "%s.mkv"' % (q, url, filename)
        proc = await asyncio.create_subprocess_shell(cmd, stderr=asyncio.subprocess.PIPE)

        if self.cli:
            durr = None
            dur_regex = re.compile(b'Duration: (?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})')
            time_regex = re.compile(b'\stime=(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})')

            while True:
                try:
                    line = await proc.stderr.readuntil(b'\r')
                except IncompleteReadError:
                    line = await proc.stderr.readline()

                if line:
                    line = line.strip()

                    if durr is None and dur_regex.search(line):
                        dur = dur_regex.search(line).groupdict()
                        dur = to_ms(**dur)

                    result = time_regex.search(line)
                    if result and result.group('hour'):
                        elapsed_time = to_ms(**result.groupdict())
                        t = round(elapsed_time / dur * 100, 2)
                        await self.q.put((t, os.path.basename(filename), bar_nr))

                    # This isnt needed since the exception is raised..
                    if not line:
                        await self.q.put((100, os.path.basename(filename), bar_nr))
                        break
            else:
                await proc.wait()

    async def _helper_programs(self, program_type, category_id='all-programs'):
        x = [self.program(item.get('programId')) for item in
             await self.client('categories/%s/%s' % (category_id, program_type))]
        return await asyncio.gather(*x)

    async def recent_programs(self, category_id='all-programs'):
        return await self._helper_programs('recentlysentprograms', category_id=category_id)

    async def popular_programs(self, category_id='all-programs'):
        return await self._helper_programs('popularprograms', category_id=category_id)

    async def recommended_programs(self, category_id='all-programs'):
        """ We need to call programs since the title is wrong in recommendedprograms"""
        return await self._helper_programs('recommendedprograms', category_id=category_id)

    async def categories(self):
        return [Category(item, nrk=self) for item in await self.client('categories/')]

    async def parse_url(self, urls):
        """ Parse the urls and download the media item.

            Args:
                urls(list): ''

        """
        LOG.debug('Parsing url(s) %s', ' '.join(urls))

        regex_list = [re.compile(r'programId: \"([a-zA-Z]+\d+)\"'),
                      re.compile(r'data-video-id=\"(\d+)\"')]

        all_ids = set()
        for i, idx in enumerate(parse_uri(urls)):
            if idx:
                all_ids.add(idx)
            else:
                html = await self.client(urls[i], type='text')

                for reg in regex_list:
                    item = reg.findall(html)
                    if item:
                        all_ids.add(item[0])
                        break

        download_list = []
        for i in all_ids:
            media = await self.program(i)
            if self.subs is True:
                await media.subtitle()  # fix me?

            download_list.append(await media.download())

        if download_list:
            await self._download_all(download_list)

        return download_list

    async def _download_all(self, to_download, include_progressbar=True, include_sub_bars=True):
        """Download all the files in to_download.to_download

           Args:
                to_download (list): list of tuples.
                include_progressbar (bool): How show the progressbar.
                include_sub_bars (bool): Add one extra bar pr download.

           Returns:
                list of tuples. fx [(url, q, name)]
        """
        fut_tasks = []
        for i, dl in enumerate(to_download):
            fut = asyncio.ensure_future(self.dl(dl, i))
            fut_tasks.append(fut)

        if self.cli and include_progressbar:  # pragma: no cover
            bars = []
            bar_format = '{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'

            len_tasks = len(to_download)

            main_bar = tqdm.tqdm(total=len_tasks, position=0,
                                 mininterval=0.02, dynamic_ncols=True,
                                 smoothing=1, bar_format=bar_format, desc='Total')

            if len_tasks > 1 and include_sub_bars:
                for ii, task in enumerate(to_download):
                    bar_pos = ii + 1
                    filename = os.path.basename(task[2])
                    sub_bar = partial(tqdm.tqdm, total=100, mininterval=0.02,
                                      position=bar_pos, miniters=1, dynamic_ncols=True,
                                      leave=True, smoothing=1, bar_format=bar_format,
                                      desc='%s' % filename)
                    bars.append(sub_bar())

            await progress_bars(to_download, self.q, bars, main_bar)
            return to_download

        else:
            return await asyncio.gather(*fut_tasks)

    async def site_rip(self):
        """Find every video file."""
        LOG.debug('Grabbing every video file we can')
        added_ids = []
        program_ids = []
        series_ids = []
        series = []
        programs = []
        for category in await self.client('categories'):
            await asyncio.sleep(0)
            if category.get('categoryId') != 'all-programs':  # useless shit...
                cat = await self.client('categories/%s/programs' % category.get('categoryId'))
                for i in cat:
                    await asyncio.sleep(0)
                    if i.get('seriesId', '').strip() != '':
                        if i.get('seriesId', '') not in added_ids:
                            series_ids.append(i.get('seriesId', ''))
                            try:
                                s = asyncio.ensure_future(self.series(i.get('seriesId', '')))
                                series.append(s)
                            except:  # pragma: no cover
                                # CRAPS out if json is shit. IDK
                                pass
                    else:
                        if i.get('programId') not in added_ids:
                            program_ids.append(i.get('programId'))
                            # Note series with the category tegnspraak will
                            # still count as program as they have no seriesId
                            try:
                                p = asyncio.ensure_future(self.program(i.get('programId')))
                                programs.append(p)
                            except:  # pragma: no cover
                                # CRAPS out if json is shit. IDK
                                pass

        eps = []

        for i in await asyncio.gather(*series):
            eps += await i.episodes()
        progs = await asyncio.gather(*programs)

        if self.cli:
            print('Found:\n')
            print('Series %s' % len(series))
            print('%s episodes' % len(eps))
            print('%s programs' % len(programs))
            print('%s media files in total' % (len(eps) + len(programs)))

        return eps + progs

    async def expires_at(self, date=None, category=None, media_type=None):
        """Find every media element that expires on a date or a date range."""
        new = None
        if date is None:
            date = datetime.datetime.now().date().strftime("%d.%m.%Y")
        else:
            old, new = parse_datestring(date)
            if new is None:
                date = old.date()

        expires_soon = []
        all_programs = await self.site_rip()

        for media in all_programs:

            if category and category != media.category.name:
                continue

            elif media_type and media_type != media.type:
                continue

            if new and media.available and old <= media.available_to <= new:
                expires_soon.append(media)

            elif media.available and media.available_to.date() == date:
                expires_soon.append(media)

        return expires_soon
