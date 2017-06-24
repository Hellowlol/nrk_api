# helpers
import datetime
import logging
import re
from json import loads
import asyncio
from shutil import which
import sys

import requests
from prompt_toolkit import prompt_async

LOG = logging.getLogger(__file__)


def clean_name(name):
    """ remove all illegal chars for ffmpeg"""
    cn = re.sub(r'[-\/\\\?%\*|"<>]', '', name).replace(':', '_')
    jcn = ' '.join(cn.split()).strip()
    return jcn


def parse_skole(url):
    # stolen from youtube dl
    obj = re.match(r'https?://(?:www\.)?nrk\.no/skole/?\?.*\bmediaId=(?P<id>\d+)', url)

    if obj:
        r = requests.get('https://mimir.nrk.no/plugin/1.0/static?mediaId=%s' % obj.group('id'))
        media_id = re.search(r'<script[^>]+type=["\']application/json["\'][^>]*>({.+?})</script>', r.text)

    try:
        real_id = loads(media_id.groups()[0])['activeMedia']['psId']
        return real_id

    except Exception as e:
        pass


def parse_uri(urls):
    if isinstance(urls, str):
        urls = urls.split(',') or urls.split()

    for s in urls:
        u = s.split('/')
        programid = None
        try:
            t = u[3]
            if t == 'serie':
                programid = u[5]
            elif t == 'program':
                programid = u[4]
            # Old style.
            elif 'PS*' in s:
                programid = u[4][3:]

            elif t == 'skole':
                programid = parse_skole(s)

            if programid:
                yield programid
        except:
            yield


def parse_datestring(s):
    """Convert a string to datetime
    "1-01-2016-13-07-2015"
    Returns:
        (datetime.datetime(2015, 7, 13, 23, 59), datetime.datetime(2016, 1, 1, 23, 59))
    """
    r = r'(\d{1,2}).(\d{1,2}).(\d{2,4})'
    res = re.findall(r, s)

    def real(t):
        d, m, y = t
        year = int(y)
        if len(y) == 2:
            y = int('20%s' % year) if year <= 30 else int('19%s' % year)
        return datetime.datetime(day=int(d), month=int(m), year=int(y), hour=23, minute=59)

    if len(res) == 2:
        return tuple(sorted((real(z) for z in res)))
    else:
        return real(res[0]), None


def to_ms(s=None, des=None, **kwargs):
    if s:  # pragma: no cover
        hour = int(s[0:2])
        minute = int(s[3:5])
        sec = int(s[6:8])
        ms = int(s[10:11])
    else:
        hour = int(kwargs.get('hour', 0))
        minute = int(kwargs.get('min', 0))
        sec = int(kwargs.get('sec', 0))
        ms = int(kwargs.get('ms', 0))

    result = (hour * 60 * 60 * 1000) + (minute * 60 * 1000) + (sec * 1000) + ms
    if des and isinstance(des, int):
        return round(result, des)
    return result


async def console_select(data, print_args=None, description=False): # pragma: no cover
    """ Helper function to allow grab dicts/objects from list with ints and slice.


        Args:
            data (list, tuple): Holding the data
            print_args (list): list of string to print
            description (bool): Should we print a description

        Returns:
            list

    """
    # We need this to be a list since we are
    # using indexes for the console.
    if not isinstance(data, list):
        data = list(data)

    # Force a reload to make sure that tvshow sxxexx works.
    # this is used by search
    if not isinstance(data[0], tuple):
        data = await asyncio.gather(*[i.reload(soft=True) for i in data])

    if print_args is None:
        print_args = []

    out = []
    # We want this reversed so we get the most relevant
    # hits at the bottom of the console.
    for i, item in reversed(list(enumerate(data))):

        # for class attrs
        if not isinstance(item, (list, tuple)):  # as a cls or func:
            out = [getattr(item, arg) for arg in print_args]
            # add the index
            out.insert(0, '{0:>3}:'.format(i))
            print(' '.join(out))
            if description and item.description is not None:
                print("     {0}".format(item.description[:110].rstrip()))

        elif isinstance(item, tuple):  # unbound, used to build a menu
            x = [item[x] for x in print_args if item[x]]
            x.insert(0, '{0:>3}:'.format(i))
            print(' '.join(x))

    ans = await prompt_async('\nSelect a number or use slice notation:\n> ', patch_stdout=True)
    # Check if was slice..
    if any(s in ans for s in (':', '::', '-')):
        idx = slice(*map(lambda x: int(x.strip()) if x.strip() else None, ans.split(':')))
        data = data[idx]
    else:
        data = data[int(ans)]

    # Just incase the user selects just one.
    if not isinstance(data, list):
        data = [data]

    return data


async def progress_bars(tasks, q, bars, main_bar):  # pragma: no cover

    len_tasks = len(tasks)
    bars_done = 0
    progress = {'def': 0}
    while True:
        if bars_done == len_tasks:
            for bb in bars:
                # Update the sub-bars.
                if bb:
                    bb.n = 100
                    bb.update(100)

            # Update main bar.
            main_bar.n = 0
            main_bar.update(len_tasks)
            break

        item = await q.get()
        if item:
            bar_progress, filename, bar_nr = item

            # Update the sub_bars:
            # Ignore if they dont exist.
            try:
                b = bars[bar_nr]
                b.n = 0
                b.update(bar_progress)
            except IndexError:
                pass

            # Update the dict holding the values for the main bar.
            progress[str(bar_nr)] = bar_progress

            main_bar_progress = round(sum(progress.values()) / 100, 2)
            main_bar.n = 0
            main_bar.update(main_bar_progress)

            if bar_progress == 100:
                bars_done += 1


def has_ffmpeg():
    ffmpeg = which('ffmpeg')
    if not ffmpeg:
        print('You need ffmpeg to download stuff')
        exit(1)
