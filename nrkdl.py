#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function


import locale
from io import BytesIO
import os
import re
import subprocess
import sys
import time
from functools import wraps

import concurrent.futures as futures
import requests
import tqdm

"""
I take no credit for this. Pretty much everything is stolen from
https://github.com/tamland/xbmc-addon-nrk/blob/master/nrktv.py

"""

if sys.version_info >= (3, 0):
    PY3 = True
    raw_input = input
    xrange = range

else:
    PY3 = False

try:
    from urllib import quote_plus as qp
except ImportError as e:
    from urllib.parse import quote_plus as qp

API_URL = 'https://tvapi.nrk.no/v1/'

session = requests.Session()
session.headers['app-version-android'] = '999'

CLI = False
ENCODING = None
SAVE_PATH = os.path.join(os.getcwd(), 'downloads')
DRY_RUN = False
VERBOSE = False

try:
    locale.setlocale(locale.LC_ALL, "")
    ENCODING = locale.getpreferredencoding()
except (locale.Error, IOError):
    pass

try:
    os.mkdir(SAVE_PATH)
except:
    pass


def c_out(s):
    if not PY3:
        return s.encode(ENCODING, 'ignore')
    else:
        return s


def timeme(func):
    @wraps(func)
    def inner(*args, **kwargs):
        start = time.time()
        res = func(*args)
        print('\n\n%s took %s' % (func.__name__, time.time() - start))
        return res
    return inner


def dl(item):
    """Downloads a media file

       [('url', 'high', 'filepath')]

    """

    url, quality, filename = item

    if DRY_RUN:
        print(c_out('Should have downloaded %s because but didnt because of -dry_run\n' % filename))
        return

    # encode to the consoles damn charset...
    if not PY3 and os.name == 'nt':
        # subprocess and py2 dont like unicode on windows
        url = url.encode(ENCODING)
        filename = filename.encode(ENCODING, 'ignore')

    q = '' if VERBOSE else '-loglevel quiet '
    cmd = 'ffmpeg %s-i %s -n -vcodec copy -acodec ac3 "%s.mkv" \n' % (q, url, filename)
    process = subprocess.Popen(cmd,
                               shell=True,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=None)

    o, e = process.communicate()
    process.stdin.close()
    return 1


def _download_all(items):
    """Async download of the files.

       Example: [(url, quality, file_path)]
    """
    fut = {}
    with futures.ThreadPoolExecutor(max_workers=8) as executor:
        fut = {executor.submit(dl, item): item for item in items}
        if CLI:
            for j in tqdm.tqdm(futures.as_completed(fut), total=len(items)):
                try:
                    res = j.result()
                except Exception as e:
                    print(e)
        else:
            for j in futures.as_completed(fut):
                res = j.result()


def _console_select(l, print_args=None):
    """ Helper function to allow grab dicts from list with ints and slice. """
    print('\n')

    if isinstance(l, dict):
        l = [l]

    if print_args is None:
        print_args = []

    for i, stuff in reversed(list(enumerate(l))):

        if not isinstance(stuff, (list, dict, tuple)):  # classes, functions
            try:
                x = [c_out(getattr(stuff, x)) for x in print_args]
                x.insert(0, str(i))
                print(' '.join(x))

            except Exception as e:
                print('some crap happend %s' % e)

        elif isinstance(stuff, tuple):  # unbound, used to build a menu
            x = [c_out(stuff[x]) for x in print_args if stuff[x]]
            x.insert(0, str(i))
            print(' '.join(x))

        else:
            # Normally a dict
            x = [c_out(stuff.get(k)) for k in print_args if stuff.get(k)]
            x.insert(0, str(i))
            print(' '.join(x))

    # select the grab...
    grab = raw_input('\nNumber or use slice notation\n')
    # Check if was slice..
    if any(s in grab for s in (':', '::', '-')):
        grab = slice(*map(lambda x: int(x.strip()) if x.strip() else None, grab.split(':')))
        l = l[grab]
    else:
        l = l[int(grab)]

        if isinstance(l, dict):
            l = [l]

    return l


def _fetch(path, *args, **kwargs):
    try:
        r = session.get(API_URL + path, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print('Error in fetch %s' % e)
        return []


def get_media_url(id=None):
    if id:
        try:
            response = _fetch('programs/%s' % id)
            return response.get('mediaUrl', '')
        except Exception as e:
            print(e)
            return {}


def _build(item):

    hit_type = item.get('type', None)
    if hit_type is not None:
        item = item.get('hit')

    if hit_type == 'serie' or item.get('seriesId', '').strip():
        return Series(item)
    else:
        return Program(item)


def parse_url(s):
    urls = [u.strip() for u in s.split(' ')]
    to_dl = []
    # grouped regex for the meta tag
    regex = re.compile(ur'<meta\sname="(.*?)"\scontent="(.*?)"\s/>')

    for s in urls:
        r = requests.get(s)
        html = r.content

        meta_tags = regex.findall(html)
        # only add it to the dict if the value exist
        meta = {k: v for k, v in meta_tags if len(v)}
        if meta.get('programid'):
            media = NRK().program(meta.get('programid'))[0]
            to_dl.append(media.download())
        else:
            print('The url has no programid')

    if to_dl:
        _download_all(to_dl)


class NRK(object):
    """ Useless class """

    def __init__(self):
        pass

    def _build(self, item):

        hit_type = item.get('type', None)
        if hit_type is not None:
            item = item.get('hit')

        if hit_type == 'serie' or item.get('seriesId', '').strip():
            return Series(item)
        else:
            return Program(item)

    def search(self, q, raw=False, strict=False):
        """ Search nrk for stuff

            Params:
                    raw(bool): used by cli,
                    strict(bool): limit the search to a exact match

            Returns:
                    If raw is false it will return a Program, Episode or series,
                    else json

        """
        s = _fetch('search/%s' % qp(q))

        if strict:
            s['hits'] = [item for item in s['hits']
                         if item['hit'].get('title', '').lower() == q.lower()]

        if s:
            if not raw:
                if s['hits'] is None:
                    return []
                return filter(None, map(_build, s['hits']))
            else:
                return s
        else:
            return []

    def programs(self, category_id):
        items = _fetch('categories/%s/programs' % category_id)
        items = [item for item in items
                 if item.get('title', '').strip() != '' and
                 item['programId'] != 'notransmission']

        return map(self._build, items)

    def program(self, program_id):
        return [_build(_fetch('programs/%s' % program_id))]

    def recent_programs(self, category_id='all-programs'):
        return [_build(data) for data in _fetch('categories/%s/recentlysentprograms' % category_id)]

    def channels(self):
        return [Channel(data) for data in _fetch('channels/')]

    def categories(self):
        return [Category(item) for item in _fetch('categories/')]

    def popular_programs(self, category_id='all-programs'):  # fixme
        return [_build(item) for item in
                _fetch('categories/%s/popularprograms' % category_id)]

    def recommended_programs(self, category_id='all-programs'):
        return [_build(item) for item in
                _fetch('categories/%s/recommendedprograms' % category_id)]

    def downloads(self):
        return Downloader()

    def _console(self, q):
        """ Used by CLI """
        # rewrite this or keep it for speed?

        to_download = []
        all_stuff = []
        all_streams = []

        response = self.search(q, raw=True)

        if response['hits'] is None:
            print('Didnt find shit')
            return
        else:
            # use reverse since 0 is the closest match and i dont want to scoll
            for i, hit in reversed(list(enumerate(response['hits']))):
                print('%s: %s' % (i, c_out(hit['hit']['title'])))

            # If there are more then one result, the user should pick a show
            if len(response['hits']) > 1:

                grab = raw_input('\nPick a show or use slice notation\n')
                # Check if was slice..
                if any(s in grab for s in (':', '::', '-')):
                    grab = slice(*map(lambda x: int(x.strip()) if x.strip() else None, grab.split(':')))
                    search_res = response['hits'][grab]
                else:
                    search_res = response['hits'][int(grab)]

            else:
                search_res = response['hits'][0]

            # check for a simgle item
            if isinstance(search_res, dict):
                search_res = [search_res]

            for sr in search_res:
                name = sr['hit']['title'].replace(':', '')  # ffppeg dont like : in the title

                base_folder = os.path.join(SAVE_PATH, name)

                try:
                    os.mkdir(base_folder)
                except:
                    pass

                if sr['type'] == 'serie':
                    # do some search object stuff..
                    id = sr['hit']['seriesId']

                    show = _fetch('series/%s' % id)

                    if 'programs' in show:
                        all_stuff = [episode for episode in show['programs'] if episode['isAvailable']]

                    # Allow selection of episodes
                    to_download = _console_select(all_stuff, ['title', 'episodeNumberOrDate'])

                elif sr['type'] == 'program':
                    to_download.append(sr['hit'])

                if to_download:
                    for d in to_download:
                        has_url = get_media_url(d['programId'])
                        if has_url:
                            if d.get('episodeNumberOrDate'):
                                filename = '%s_%s' % (d['title'].replace(':', ''), d['episodeNumberOrDate'].replace(':', '_'))
                            else:
                                filename = '%s' % d['title'].replace(':', '')

                            #  clean up for ffmpeg
                            filename = re.sub('[/\\\?%\*:|"<>]', '', filename)  # new check this

                            f_path = os.path.join(base_folder, filename)
                            # set quality # TODO
                            t = (has_url, 'high', f_path)
                            all_streams.append(t)

                if all_streams:
                    _download_all(all_streams)
                else:
                    print('Nothing to download')

    def _browse(self):
        categories = _console_select(self.categories(), ['title'])
        what_programs = [('Popular', self.popular_programs),
                         ('Recommended', self.recommended_programs),
                         ('Recent', self.recent_programs)
                         ]

        x = _console_select(what_programs, [0])  # should be list?
        media_element = [_console_select(x[1](categories.id), ['title'])]
        # type_list should be a media object
        print('Found %s media elements' % len(media_element))
        for m_e in media_element:
            if not isinstance(m_e, list):
                m_e = [m_e]
            for z in m_e:
                print(c_out('%s\n' % z.name))
                print(c_out('%s\n' % z.description))
                a = raw_input('Do you wish to download this? y/n\n')
                if a == 'y':
                    Downloader().add(z.download())

        aa = raw_input('Download que is %s do you wish to download everything now? y/n\n' % len(self.downloads()))
        d = self.downloads()
        if aa == 'y':
            print(Downloader().files_to_download)
            bb = d.start()
            print(bb)
        else:
            d.clear()


class Media(object):
    def __init__(self, data, *args, **kwargs):
        self.data = data
        self.name = data.get('name', '') or data.get('title', '')
        self.name = self.name.strip()
        self.type = data.get('type', None)
        self.id = data.get('id', None)
        self.available = data.get('isAvailable', False)
        self.media_url = data.get('mediaUrl') or get_media_url(data.get('programId'))

    def as_dict(self):
        return self.data

    def download(self, path=None):
        if self.available is False or self.media_url is None:
            print('Cant download %s' % self.name)
            return

        if path is None:
            path = SAVE_PATH

        try:
            os.makedirs(os.path.join(SAVE_PATH, self.name))
        except:
            pass

        title = self.data['title'].replace(':', '')
        if 'episodeNumberOrDate' in self.data:
            title += '_%s' % self.data.get('episodeNumberOrDate', '').replace(':', '')

        # remove stuff that ffmpeg could complain about
        title = re.sub('[/\\\?%\*:|"<>]', '_', title)

        q = 'high'  # fix me
        url = self.media_url

        base_folder = os.path.join(SAVE_PATH, self.name.replace(':', ''))
        fp = os.path.join(base_folder, title)

        if url:
            if CLI is False:  # add fix for -browse
                return Downloader().add((url, q, fp))
            else:
                return (url, q, fp)
        else:
            print("No download url")


class Episode(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        #self.__dict__.update(data)
        self.ep_name = data.get('episodeNumberOrDate', '')
        self.category = Category(data.get('category') if 'category' in data else None)


class Season(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        #self.id = data.get('id')

    #def episode(self):
    #    pass


class Program(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        self.type = 'program'
        #self.__dict__.update(data) # this needed?
        self.programid = data.get('programId')
        self.id = data.get('programId')
        self.description = data.get('description', '')
        self.available = data.get('isAvailable', False)
        self.category = Category(data.get('category') if 'category' in data else None)


class Series(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        self.type = 'serie'
        self.id = data.get('seriesId'),
        self.title = data['title'].strip()
        self.name = data['title'].strip() # test
        self.description = data.get('description', '')
        self.legal_age = data.get('legalAge') or data.get('aldersgrense')
        self.image_id = data.get('seriesImageId', data.get('imageId', None))
        self.available = data.get('isAvailable', False)
        self.category = Category(data.get('category') if 'category' in data else None)

    #def seasons(self):
        #  No usefull info
    #   return [Season(d) for d in self.data['seasons']]

    def episodes(self):
        return [Episode(d) for d in _fetch('series/%s' % self.id)['programs']]


class Channel(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        self.channel_id = data.get('channelId')
        self.title = data.get('title').strip()
        self.id_live = data.get('isLive')
        self.has_epg = data.get('hasEpg')
        self.priority = data.get('priority')

    def epg(self):
        return [_build(e) for e in self.data['epg']['liveBufferEpg']]


class Downloader(object):
    files_to_download = []

    def __len__(cls):
        return len(cls.files_to_download)

    @classmethod
    def add(cls, media):
        print("downloder add got %s" % c_out(', '.join(media)))
        cls.files_to_download.append(media)

    @classmethod
    def start(cls):
        print('Downloads starting soon.. %s downloads to go' % len(cls.files_to_download))
        return _download_all(cls.files_to_download)

    @classmethod
    def clear(cls):
        print('Cleared downloads')
        cls.files_to_download = []


class Category(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        self.id = data.get('categoryId', None)
        self.name = data.get('displayValue', None)
        self.title = data.get('displayValue', None)


class Subtitle(object):
    # untested, add translate?
    def get_subtitles(cls, video_id):
        html = session.get("http://v8.psapi.nrk.no/programs/%s/subtitles/tt" % video_id).text
        if not html:
            return None

        content = cls.ttml_to_srt(html)
        filename = None
        filename = os.path.join(SAVE_PATH, 'nor.srt')
        with open(filename, 'w') as f:
            f.write(content)
        return filename

    @classmethod
    def _time_to_str(cls, time):
        return '%02d:%02d:%02d,%03d' % (time / 3600, (time % 3600) / 60, time % 60, (time % 1) * 1000)

    @classmethod
    def _str_to_time(cls, txt):
        p = txt.split(':')
        try:
            ms = float(p[2])
        except ValueError:
            ms = 0
        return int(p[0]) * 3600 + int(p[1]) * 60 + ms

    @classmethod
    def _ttml_to_srt(cls, ttml):
        lines = re.compile(r'<p begin="(.*?)" dur="(.*?)".*?>(.*?)</p>',
                           re.DOTALL).findall(ttml)

        # drop copyright line
        if len(lines) > 0 and lines[0][2].lower().startswith('copyright'):
            lines.pop(0)

        subtitles = []
        for start, duration, text in lines:
            start = cls._str_to_time(start)
            duration = cls._str_to_time(duration)
            end = start + duration
            subtitles.append((start, end, text))

        # fix overlapping
        for i in xrange(0, len(subtitles) - 1):
            start, end, text = subtitles[i]
            start_next, _, _ = subtitles[i + 1]
            subtitles[i] = (start, min(end, start_next - 1), text)

        output = BytesIO()
        for i, (start, end, text) in enumerate(subtitles):
            text = text.replace('<span style="italic">', '<i>') \
                .replace('</span>', '</i>') \
                .replace('&amp;', '&') \
                .split()
            text = ' '.join(text)
            text = re.sub('<br />\s*', '\n', text)
            text = text.encode(ENCODING)

            output.write(str(i + 1))
            output.write('\n%s' % cls._time_to_str(start))
            output.write(' --> %s\n' % cls._time_to_str(end))
            output.write(text)
            output.write('\n\n')

        return output.getvalue()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('-s', '--search', default=False,
                        required=False, help='Search nrk for a show and download all available eps')

    parser.add_argument('-e', '--encoding', default='latin-1',
                        required=False, help='Console encoding')

    parser.add_argument('-u', '--url', default=False,
                        required=False, help='Download show for the interwebz')

    parser.add_argument('-b', '--browse', action='store_true', default=False,
                        required=False, help='Categories') #TODO?

    parser.add_argument('-save', '--save_path', default=False,
                        required=False, help='Download to this folder')

    parser.add_argument('-dr', '--dry_run', action='store_true', default=False,
                        required=False, help='Dry run, dont download anything')

    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        required=False, help='Show ffmpeg outup')

    p = parser.parse_args()

    DRY_RUN = p.dry_run
    VERBOSE = p.verbose

    CLI = True
    ENCODING = p.encoding

    if p.save_path:
        SAVE_PATH = p.save_path

    if p.url:
        parse_url(p.url)

    elif p.search:
        c = NRK()._console(p.search)

    elif p.browse:
        c = NRK()._browse()




"""
Examples

As a module:

nrk = NRK()
s = nrk.search("lille jack", strict=True)
for e in s.episodes():
    print(e.download())

all_downloads = nrk.downloads()

# How many files are we gonna download
print(len(nrk.downloads()))
all_downloads.start()


CLI:
    python nrkdl.py -s "lille jack"
"""
