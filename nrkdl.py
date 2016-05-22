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
WORKERS = 4
SUBTITLE = False

APICALLS = 0

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


def clean_name(s):
    s = re.sub(ur'[-/\\\?%\*|"<>]', '', s).replace(':', '_')
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
    global WORKERS
    # limit workers to max number of items
    if len(items) > WORKERS:
        WORKERS = len(items)

    with futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
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


def _fetch(path, **kwargs):
    try:
        r = session.get(API_URL + path, **kwargs)
        global APICALLS
        APICALLS += 1
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print('Error in fetch %s' % e)
        return []


def get_media_url(media_id=None):
    #print('get_media_url called %s media_id' % media_id)
    if media_id:
        try:
            response = _fetch('programs/%s' % media_id)
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

    def programs(self, category_id='all-programs'):
        items = _fetch('categories/%s/programs' % category_id)
        items = [item for item in items
                 if item.get('title', '').strip() != '' and
                 item['programId'] != 'notransmission']

        return map(_build, items)

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
                if sr['type'] == 'serie':
                    # do some search object stuff..
                    id = sr['hit']['seriesId']

                    show = _fetch('series/%s' % id)

                    # if we select a show, we should be able to choose all eps.
                    if 'programs' in show:
                        all_stuff = [Episode(e) for e in show['programs'] if e['isAvailable']]

                    # Allow selection of episodes
                    all_eps = _console_select(all_stuff, ['full_title'])
                    if not isinstance(all_eps, list):
                        all_eps = [all_eps]

                    to_download += all_eps

                elif sr['type'] in ['program', 'episode']:
                    to_download.append(_build(sr['hit']))

                if to_download:

                    for d in to_download:
                        d.download()
                        if SUBTITLE is True:
                            d.subtitle()

            if len(self.downloads()):
                self.downloads().start()
            else:
                print('Nothing to download')


    def _browse(self):
        categories = _console_select(self.categories(), ['title'])
        what_programs = [('Popular ' + categories.name, self.popular_programs),
                         ('Recommended ' + categories.name, self.recommended_programs),
                         ('Recent ' + categories.name, self.recent_programs)
                         ]

        x = _console_select(what_programs, [0])  # should be list?
        media_element = [_console_select(x[1](categories.id), ['full_title'])]
        # type_list should be a media object
        print('Found %s media elements' % len(media_element))
        for m_e in media_element:
            if not isinstance(m_e, list):
                m_e = [m_e]
            for z in m_e:
                if SUBTITLE is True:
                    z.subtitle()
                print(c_out('%s\n' % z.name))
                print(c_out('%s\n' % z.description))
                a = raw_input('Do you wish to download this? y/n\n')
                if a == 'y':
                    z.download()

        if len(self.downloads()):
            aa = raw_input('Download que is %s do you wish to download everything now? y/n\n' % len(self.downloads()))
            d = self.downloads()
            if aa == 'y':
                d.start()
            else:
                d.clear()


class Media(object):
    def __init__(self, data, *args, **kwargs):
        self.data = data
        self.name = data.get('name', '') or data.get('title', '')
        self.name = self.name.strip()
        self.title = data.get('title')  # test
        self.type = data.get('type', None)
        self.id = data.get('id', None)  # check this
        self.available = data.get('isAvailable', False)
        #self.media_url = data.get('mediaUrl') or get_media_url(data.get('programId')) # test
        self.file_name = self._filename()
        self.file_path = os.path.join(SAVE_PATH, clean_name(self.name), self.file_name)

        if 'episodeNumberOrDate' in data:
            self.full_title = '%s %s' % (self.name, data.get('episodeNumberOrDate', ''))
        else:
            self.full_title = self.title

    def _filename(self):
        name = clean_name(self.name)
        if 'episodeNumberOrDate' in self.data:
            name += ' %s' % self.data.get('episodeNumberOrDate', '')
            # remove stuff that ffmpeg could complain about
            name = clean_name(name)
        return name

    def as_dict(self):
        """ raw response """
        return self.data

    def subtitle(self):
        """ download a subtitle """
        print(self.type)
        return Subtitle().get_subtitles(self.id, name=self.name, file_name=self.file_name)

    def media_url(self):
        """ Allow mediaurl to be created manually """
        return get_media_url(self.id)

    def download(self, path=None):
        if self.available is False:
            print('Cant download %s' % self.name)
            return

        url = get_media_url(self.id)
        if url is None:
            return

        if path is None:
            path = SAVE_PATH

        name = clean_name(self.name)

        try:
            # Make sure the show folder exists
            os.makedirs(os.path.join(SAVE_PATH, name))
        except:
            pass

        q = 'high'  # fix me
        fp = self.file_path
        t = (url, q, fp)
        Downloader().add((url, q, fp))
        return t


class Episode(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        self.__dict__.update(data)
        self.ep_name = data.get('episodeNumberOrDate', '')
        self.full_title = '%s %s' % (self.name, self.ep_name)
        self.category = Category(data.get('category') if 'category' in data else None)
        self.id = data.get('programId')


class Season(Media):
    def __init__(self, season_number, id,
                 description,
                 series_id,
                 *args,
                 **kwargs):
        self.id = id
        self.season_number = season_number
        self.description = description
        self.series_id = series_id

    def episodes(self):
        return [Episode(d) for d in _fetch('series/%s' % self.series_id)['programs'] if self.id == d.get('seasonId')]


class Program(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        self.type = 'program'
        self.__dict__.update(data)
        self.programid = data.get('programId')
        self.full_title = self.name
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
        self.name = data['title'].strip()
        self.description = data.get('description', '')
        self.legal_age = data.get('legalAge') or data.get('aldersgrense')
        self.image_id = data.get('seriesImageId', data.get('imageId', None))
        self.available = data.get('isAvailable', False)
        self.media_url = data.get('mediaUrl') or get_media_url(data.get('programId'))
        self.category = Category(data.get('category') if 'category' in data else None)
        # series object can act as a ep
        if 'episodeNumberOrDate' in data:
            self.full_title = '%s %s' % (self.name, data.get('episodeNumberOrDate', ''))
        else:
            self.full_title = self.title

    def seasons(self):
        all_seasons = []  # the lowest seasonnumer in a show in the first season
        s_list = sorted([s['id'] for s in self.data['seasons']])
        for i, id in enumerate(s_list):
            s = Season(season_number=i,
                       id=id,
                       series_name=self.name,
                       description=self.description,
                       series_id=self.id)

            all_seasons.append(s)

        return all_seasons

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
        cls.files_to_download.append(media)

    @classmethod
    def start(cls):
        print('Downloads starting soon.. %s downloads to go' % len(cls.files_to_download))
        print(cls.files_to_download)
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
    # tested and works but slow.., add translate?
    all_subs = []

    #def __init__(self):
    #    pass
    #        # filename

    @classmethod
    def get_subtitles(cls, video_id, name=None, file_name=None, translate=False):
        html = session.get("http://v8.psapi.nrk.no/programs/%s/subtitles/tt" % video_id).text
        if not html:
            return None

        # make sure the show folder exist
        # incase someone just wants to download the sub
        try:
            os.makedirs(os.path.join(SAVE_PATH, name))
        except:
            pass

        content = cls._ttml_to_srt(html)
        file_name = '%s.srt' % file_name
        file_name = os.path.join(SAVE_PATH, name, file_name)

        with open(file_name, 'w') as f:
            f.write(content)
        return file_name

    @classmethod
    def translate(cls, text):
        # check this
        # from https://github.com/jashandeep-sohi/nrksub
        response = session.post('https://translate.googleusercontent.com/translate_f',
                                files={'file': ('trans.txt', '\r\r'.join(text), "text/plain")},
                                data={'sl': 'no',
                                      'tl': TRANSLATE,
                                      'js': 'y',
                                      'prev': '_t',
                                      'hl': 'en',
                                      'ie': 'UTF-8',
                                      'edit-text': '',
                                    },
                                headers={"Referer": "https://translate.google.com/"}
                                )
        return response.text


    @classmethod
    def add(cls):
        pass  # TODO

    @classmethod
    def clear(cls):
        pass  # TODO

    @classmethod
    def start(cls):
        pass  # TODO

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
            text = text.encode('utf8', 'ignore')

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
                        required=False, help='Search nrk for a show and download files')

    parser.add_argument('-e', '--encoding', default='latin-1',
                        required=False, help='Set encoding')

    parser.add_argument('-u', '--url', default=False,
                        required=False, help='"url1 url2 url3"')

    parser.add_argument('-b', '--browse', action='store_true', default=False,
                        required=False, help='Browse')

    parser.add_argument('-save', '--save_path', default=False,
                        required=False, help='Download to this folder')

    parser.add_argument('-dr', '--dry_run', action='store_true', default=False,
                        required=False, help='Dry run, dont download anything')

    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        required=False, help='Show ffmpeg output')

    parser.add_argument('-w', '--workers', action='store_true', default=WORKERS,
                        required=False, help='Number of thread pool workers')

    parser.add_argument('-st', '--subtitle', action='store_true', default=SUBTITLE,
                        required=False, help='Download subtitle for this media file?')

    parser.add_argument('-t', '--translate', action='store_true', default=False,
                        required=False, help='Translate')

    p = parser.parse_args()

    DRY_RUN = p.dry_run
    VERBOSE = p.verbose
    SUBTITLE = p.subtitle
    TRANSLATE = p.translate

    CLI = True
    ENCODING = p.encoding

    if p.workers:
        WORKERS = p.workers

    if p.save_path:
        SAVE_PATH = p.save_path

    if p.url:
        parse_url(p.url)

    elif p.search:
        c = NRK()._console(p.search)

    elif p.browse:
        c = NRK()._browse()



#Examples

#As a module:
"""
nrk = NRK()
search = nrk.search("skam", strict=True)
print(len(search))
for s in search:
    #print(len(s.episodes()))
    for e in s.episodes():
        print(e.id)
        #e.subtitle()
        #print(e.download())
    #for s in s.seasons():
    #    for e in s.episodes():
    #        print(e.id)
            #e.subtitle()

    #for e in s.episodes():
    #    e.download()
print('APICALLS used %s' % APICALLS)
all_downloads = nrk.downloads()

# How many files are we gonna download
print(len(all_downloads))
#all_downloads.start()
#"""

#sub = Subtitle().get_subtitles('msub19120116')