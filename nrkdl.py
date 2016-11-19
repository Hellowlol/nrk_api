#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

from datetime import datetime
import locale
import logging
import os
import re
import subprocess
import sys
from io import StringIO
from multiprocessing.dummy import Pool as ThreadPool

from utils import _console_select, clean_name, compat_input, which, parse_datestring, parse_skole

from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
import requests
import tqdm

"""
I take no credit for this. Pretty much everything is stolen from
https://github.com/tamland/xbmc-addon-nrk/blob/master/nrktv.py

"""

if sys.version_info >= (3, 0):
    PY3 = True
    xrange = range
else:
    PY3 = False

try:
    from urllib import quote_plus as qp
except ImportError as e:
    from urllib.parse import quote_plus as qp

API_URL = 'https://tvapi.nrk.no/v1/'
SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')

session = requests.Session()
session.headers['app-version-android'] = '999'
session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36'

#cached_session = CacheControl(session,
#                              cache=FileCache(os.path.join(SAVE_PATH, '.webcache')))

# Try to set some sane defaults

APICALLS = 0
logging.basicConfig(level=logging.DEBUG)

try:
    os.makedirs(SAVE_PATH)
except OSError as e:
    if not os.path.isdir(SAVE_PATH):
        raise

# Disable log spam
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("cachecontrol").setLevel(logging.WARNING)


def get_encoding(gui=False):
    try:
        if not gui:
            locale.setlocale(locale.LC_ALL, "")
        return locale.getpreferredencoding()
    except (locale.Error, IOError):
        return 'utf-8'

# Feels very dirty
ENCODING = get_encoding()


def c_out(s, encoding=ENCODING):  # fix me
    if not PY3:
        return s.encode(encoding, 'ignore')
    else:
        return s


def _fetch(path, cache=False, **kwargs):  # fix me
    # global APICALLS
    # APICALLS += 1
    #print('fetch %s' % path)
    try:
        """
        if cache:
            r = cached_session.get(API_URL + path, **kwargs)
        else:
            r = session.get(API_URL + path, **kwargs)
        """
        r = session.get(API_URL + path, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.exception('Failed to %s %s' % (path, e))
        return {}


def get_media_url(media_id):
    """ returns the media urls, if we want more details we
        could use this response to populate the class as it
        yields more info
    """
    #  print('get_media_url called %s media_id' % media_id)
    try:
        response = _fetch('programs/%s' % media_id)
        return response.get('mediaUrl', '')
    except Exception as e:
        logging.exception('Failed to %s' % e)
        return {}


def _build(item):
    """ Helper function that returns the correct class """
    if item is not None:
        hit_type = item.get('type')
        if hit_type is not None:
            item = item.get('hit')

        if hit_type == 'serie' or item.get('seriesId', '').strip():
            return Series(item)
        elif hit_type == 'episode':
            return Episode(item)
        else:
            return Program(item)


def parse_uri(urls):
    obs = []
    for s in urls:
        u = s.split('/')
        programid = None
        try:
            t = u[3]
            if t == 'serie':
                programid = u[5]
            elif t == 'program':
                programid = u[4]
            elif t == 'skole':
                programid = parse_skole(s)

            if programid:
                obs.append(programid)

        except IndexError:
            # try to parse the webpage
            pass

    return [i for i in obs if i is not None or i is not '']


class NRK(object):
    """ Useless class """

    def __init__(self,
                 dry_run=False,
                 encoding=None,
                 workers=4,
                 verbose=False,
                 save_path=None,
                 subtitle=False,
                 cli=False,
                 gui=False,
                 chunks=1,
                 *args,
                 **kwargs):

        self.dry_run = dry_run
        self.workers = workers
        self.verbose = verbose
        self.subs = subtitle
        self.cli = cli
        self.chunks = chunks

        # Allow override # fix me
        global SAVE_PATH
        if save_path is None:
            self.save_path = SAVE_PATH
        else:
            SAVE_PATH = save_path
            self.save_path = save_path

        if encoding is None:
            self.encoding = get_encoding(gui=gui)
        else:
            self.encoding = encoding

        global ENCODING
        ENCODING = self.encoding

    def dl(self, item, *args, **kwargs):
        """Downloads a media file

           ('url', 'high', 'filepath')

        """

        url, quality, filename = item

        if self.dry_run:
            print(c_out('Should have downloaded %s because but didnt because of -dry_run\n' % filename))
            return

        # encode to the consoles damn charset...
        if not PY3 and os.name == 'nt':
            # subprocess and py2 dont like unicode on windows
            url = url.encode(self.encoding)
            filename = filename.encode(self.encoding, 'ignore')

        q = '' if self.verbose else '-loglevel quiet '
        cmd = 'ffmpeg %s-i %s -n -vcodec copy -acodec ac3 "%s.mkv" \n' % (q, url, filename)
        process = subprocess.Popen(cmd,
                                   shell=True,
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=None)

        o, e = process.communicate()
        process.stdin.close()

        return 1

    def _download_all(self, items):
        """Async download of the files.

           Example: [(url, quality, file_path)]

        """
        # Don't start more workers then 1:1
        if self.workers >= len(items):
            self.workers = len(items)

        pool = ThreadPool(self.workers)
        chunks = self.chunks  # TODO
        # 1 ffmpeg is normally 10x- 20x * 2500kbits ish
        # so depending on how many items you download and
        # your bandwidth you might need to tweak chunk

        results = pool.imap_unordered(self.dl, items, chunks)

        try:
            if self.cli:
                for j in tqdm.tqdm(results, total=len(items)):
                    pass
        finally:
            pool.close()
            pool.join()

    @staticmethod
    def search(q, raw=False, strict=False):
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
                return list(filter(None, map(_build, s['hits'])))
            else:
                return s
        else:
            return []

    @staticmethod
    def programs(category_id='all-programs'):
        items = _fetch('categories/%s/programs' % category_id)
        items = [item for item in items
                 if item.get('title', '').strip() != '' and
                 item['programId'] != 'notransmission']

        return map(_build, items)

    @staticmethod
    def program(program_id):
        """ Get details about a program/series """
        item = _fetch('programs/%s' % program_id)
        if item.get('seriesId', '').strip():
            return [Episode(item)]
        else:
            return [Program(item)]

    @staticmethod
    def series(series_id):
        return [Series(_fetch('series/%s' % series_id))]

    @staticmethod
    def channels():
        return [Channel(data) for data in _fetch('channels/')]

    @staticmethod
    def site_rip():  # pragma: no cover
        """ Dont run this.. """
        added_ids = []
        programs = []
        series = []
        total = 0
        for category in _fetch('categories'):
            if category.get('categoryId') != 'all-programs':  # useless shit...
                cat = _fetch('categories/%s/programs' % category.get('categoryId'))
                for i in cat:
                    if i.get('seriesId', '').strip() != '':
                        if i.get('seriesId', '') not in added_ids:
                            added_ids.append(i.get('seriesId', ''))
                            try:
                                s = NRK.series(i.get('seriesId', ''))
                                series += s
                            except:
                                # CRAPS out if json is shit. IDK
                                pass
                    else:
                        if i.get('programId') not in added_ids:
                            added_ids.append(i.get('programId'))

                            # Note series with the category tegnspraak will
                            # still count as program as they have no seriesId
                            try:
                                p = NRK.program(i.get('programId'))
                                programs += p
                            except:
                                # CRAPS out if json is shit. IDK
                                pass

        print('Found:\n')
        print('%s series' % len(series))
        for s in series:
            total += len(s.episodes())

        print('%s episodes' % total)
        print('%s programs' % len(programs))
        print('%s media files in total' % (total + len(programs)))
        return series + programs

    def parse_url(self, s):
        """ parse a url from super and/or nrk and download the video """

        urls = [u.strip() for u in s.split(' ')]
        to_dl = []
        p_ids = []

        # Lets try to get the program id from the uri
        p_ids = parse_uri(urls)

        # Fallback to parsing html of that url if we didnt find them all
        if not p_ids or len(p_ids) < len(urls):
            logging.info('Couldnt extract programid/seriesid from the url '
                         'fallback to parsing the site')
            # grouped regex for the meta tag
            regex = re.compile(r'<meta\sname="(.*?)"\scontent="(.*?)"\s/>')

            for s in urls:
                r = requests.get(s)
                html = r.text

                meta_tags = regex.findall(html)

                # only add it to the dict if the value exist
                meta = dict((k, v) for k, v in meta_tags if len(v))
                if meta.get('programid'):
                    p_ids.append(meta.get('programid'))
                else:
                    logging.debug('The url has no programid')

        if p_ids:
            p_ids = set(p_ids)
            for i in p_ids:
                media = NRK.program(i)[0]
                if self.subs is True:
                    media.subtitle()
                to_dl.append(media.download())
        else:
            logging.warning('Couldnt find a url parsing the site or via urls')

        if to_dl:
            self._download_all(to_dl)

        return to_dl

    @staticmethod
    def categories():
        return [Category(item) for item in _fetch('categories/')]

    @staticmethod
    def recent_programs(category_id='all-programs'):
        r = []
        for item in _fetch('categories/%s/recentlysentprograms' % category_id):
            obj = _fetch('programs/%s' % item.get('programId'))
            if obj:
                r.append(_build(obj))

        return r

    @staticmethod
    def popular_programs(category_id='all-programs'):
        r = []
        for item in _fetch('categories/%s/popularprograms' % category_id):
            obj = _fetch('programs/%s' % item.get('programId'))
            if obj:
                r.append(_build(obj))

        return r

    @staticmethod
    def recommended_programs(category_id='all-programs'):
        """ We need to call programs since the title is wrong in recommendedprograms"""
        r = []
        for item in _fetch('categories/%s/recommendedprograms' % category_id):
            obj = _fetch('programs/%s' % item.get('programId'))
            if obj:
                r.append(_build(obj))

        return r

    def downloads(self):
        return Downloader(self)

    def _from_file(self, f):
        try:
            urls = []
            with open(f, 'r') as f:
                urls = [ff.strip('\n') for ff in f.readlines() if ff]

            if urls:
                return self.parse_url(' '.join(urls))
            else:
                logging.warning('No urls in the file')
                return []

        except Exception as e:
            logging.exception('%s' % e)
            return []

    def _console(self, q):
        """ Used by CLI """
        to_download = []
        all_stuff = []

        response = self.search(q, raw=True)

        if response['hits'] is None:
            logging.info('Didnt find anything')
            return
        else:
            # use reverse since 0 is the closest match and i dont want to scoll
            for i, hit in reversed(list(enumerate(response['hits']))):
                print('{0:>3}: {1}'.format(i, c_out(hit['hit']['title'])))

            # If there are more then one result, the user should pick a show
            if len(response['hits']) > 1:

                grab = compat_input('\nSelect a number or use slice notation\n')
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
                    print(show['title'])

                    # if we select a show, we should be able to choose all eps.
                    if 'programs' in show:
                        # Fix me, try to search for kash an it returns the wrong title.
                        all_stuff = [Episode(e, name=show['title'], seasonIds=show['seasonIds']) for e in show['programs'] if e['isAvailable']]

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
                    if self.subs is True:
                        d.subtitle()

            if self.downloads():
                self.downloads().start()
                return self.downloads()
            else:
                print('Nothing to download')

    def _browse(self):
        """ Browse the shows from nrk/super """

        categories = _console_select(NRK.categories(), ['title'])
        what_programs = [('Popular ' + categories[0].name, NRK.popular_programs),
                         ('Recommended ' + categories[0].name, NRK.recommended_programs),
                         ('Recent ' + categories[0].name, NRK.recent_programs)
                         ]

        x = _console_select(what_programs, [0])
        # this does not report S01E01 as it would require a extra apicall
        media_element = _console_select(x[0][1](categories[0].id), ['full_title'])
        # type_list should be a media object
        print('Found %s media elements' % len(media_element))
        dl_all = False
        for m_e in media_element:
            if self.subs is True:
                m_e.subtitle()
            if dl_all is True:
                m_e.download()
                continue
            print(c_out('%s\n' % m_e.name))
            print(c_out('%s\n' % m_e.description))
            a = compat_input('Do you wish to download this? y/n/c/all\n')
            if a == 'y':
                m_e.download()
            elif a == 'all':
                m_e.download()
                dl_all = True
            elif a == 'c':
                break

        if self.downloads():
            aa = compat_input('Download que is %s do you wish to download everything now? y/n\n' % len(self.downloads()))
            d = self.downloads()
            if aa == 'y':
                d.start()
            else:
                d.clear()
            return d
        else:
            return []

    def expires_at(self, date=None, category=None, media_type=None):
        new = None
        if date is None:
            date = datetime.now().date()
        else:
            old, new = parse_datestring(date)
            if new is None:
                date = old.date()

        expires_soon = []

        all_programs = self.site_rip()

        for media in all_programs:
            if media.type == 'serie' and media_type is None or media_type == 'serie':
                for ep in media.episodes():
                    if category and category != ep.category.name:
                        continue

                    if new:
                        # We need to check ep is available because
                        # it still be available_to but we cant download it..
                        if old <= ep.available_to <= new and ep.available:
                            expires_soon.append(ep)

                    elif ep.available_to.date() == date and ep.available:
                        expires_soon.append(ep)
            else:
                if category and category != media.category.name:
                    continue

                if media_type and media_type != media.type:
                    continue

                if new:
                    if old <= media.available_to <= new and media.available:
                        expires_soon.append(media)
                elif media.available_to.date() == date and media.available:
                    expires_soon.append(media)

        if expires_soon:
            print('%s expires today' % len(expires_soon))
            eps = _console_select(expires_soon, ['full_title'])
            [m.download(os.path.join(self.save_path, str(date))) for m in eps]
            ip = compat_input('Download que is %s do you wish to download everything now? y/n\n' % len(self.downloads()))
            if ip == 'y':
                self.downloads().start()


class Media(object):
    """ Base class for all the media elements """

    def __init__(self, data, *args, **kwargs):
        self.data = data
        self.name = data.get('name', '') or data.get('title', '')
        self.name = self.name.strip()
        self.title = data.get('title', '')
        self.type = data.get('type')
        self.id = data.get('id')
        self.available = data.get('isAvailable', False)
        self._image_url = "http://m.nrk.no/m/img?kaleidoId=%s&width=%d"

        if self.data.get('episodeNumberOrDate'):
            self.full_title = '%s %s' % (self.name, self._fix_sn(self.data.get('seasonId'), season_ids=kwargs.get('seasonIds')))
        else:
            self.full_title = self.title

        self.file_name = self._filename(self.full_title)
        self.file_path = os.path.join(SAVE_PATH, clean_name(self.name), self.file_name)
        self._image_id = data.get('imageId') or kwargs.get('imageId')

    @property
    def thumb(self):
        return self._image_url % (self._image_id, 500) if self._image_id else None

    @property
    def available_to(self):
        try:
            r = datetime.fromtimestamp(int(self.data.get('usageRights', {}).get('availableTo', 0) / 1000), None)
        except (ValueError, OSError, OverflowError):
            r = datetime.fromtimestamp(0)

        return r

    @property
    def fanart(self):
        return self._image_url % (self._image_id, 1920) if self._image_id else None

    def _filename(self, name=None):
        name = clean_name('%s' % name or self.full_title)
        name = name.replace(' ', '.') + '.WEBDL-nrkdl'
        return name

    def _fix_sn(self, season_number=None, season_ids=None):
        lookup = {}
        stuff = season_ids or self.data.get('series', {}).get('seasonIds')

        # Since shows can have a date..
        # dateregex (\d+\.\s\w+\s\d+)
        not_date = re.search('(\d+:\d+)', self.data.get('episodeNumberOrDate', ''))
        if not_date is None:
            return self.data.get('episodeNumberOrDate', '')

        try:
            for d in stuff:
                sn = d.get('name', '').replace('Sesong ', '')

                lookup[str(d['id'])] = 'S%sE%s' % (sn.zfill(2), self.data.get('episodeNumberOrDate', '').split(':')[0].zfill(2))

            return lookup[str(self.data.get('seasonId'))]

        except:
            return self.data.get('episodeNumberOrDate', '')

    def as_dict(self):
        """ raw response """
        return self.data

    def subtitle(self):
        """ download a subtitle """
        return Subtitle().get_subtitles(self.id, name=self.name, file_name=self.file_name)

    @property
    def media_url(self):
        """ Allow mediaurl to be created manually """
        return get_media_url(self.id if self.type != 'serie' else self.data.get('programId'))

    def download(self, path=None):
        if self.available is False:
            # print('Cant download %s' % c_ount(self.name))
            return

        url = self.media_url
        if url is None:
            return

        if path is None:
            path = SAVE_PATH

        folder = clean_name(self.name)

        try:
            # Make sure the show folder exists
            os.makedirs(os.path.join(path, folder))
        except OSError as e:
            if not os.path.isdir(os.path.join(path, folder)):
                raise

        fp = os.path.join(path, folder, self.file_name)
        q = 'high'  # fix me
        t = (url, q, fp)
        Downloader(self).add((url, q, fp))
        return t

    def __eq__(self, other):
        return (self.id == other.id and
                self.title == other.title and
                self.type == other.type and
                self.full_title == other.full_title and
                self.file_path == other.file_path and
                self.file_name == other.file_name and
                self.available == other.available)

    def __repr__(self):
        return '%s %s %s' % (self.__class__.__name__,
                             self.type,
                             self.full_title)


class Episode(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        self.season_number = kwargs.get('season_number') or data.get('seasonId')  # fixme
        self.ep_name = data.get('episodeNumberOrDate', '')
        self.category = Category(data.get('category') if 'category' in data else None)
        self.id = data.get('programId')
        self.type = 'episode'
        # Because of https://tvapi.nrk.no/v1/programs/MSUS27001913 has no title
        # Prefer name as kwargs,
        self.name = kwargs.get('name') or data.get('series', {}).get('title', '') or data.get('title')
        self.full_title = '%s %s' % (self.name, self._fix_sn(self.season_number, season_ids=kwargs.get('seasonIds')))
        # Fix for shows like zoom og kash
        self.file_name = self._filename(self.full_title)


class Season(Media):
    def __init__(self, season_number, id,
                 description,
                 series_id,
                 *args,
                 **kwargs):
        self.id = id
        self.type = 'season'
        self.season_number = season_number
        self.full_title = 'season %s' % season_number
        self.description = description
        self.series_id = series_id

    def episodes(self):
        return [Episode(d, season_number=self.season_number) for d in
                _fetch('series/%s' % self.series_id)['programs']
                if self.id == d.get('seasonId')]


class Program(Media):
    """ Program is the media element of movies etc """

    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        self.data = data
        self.type = 'program'
        self.__dict__.update(data)
        self.programid = data.get('programId')
        self.id = data.get('programId')
        self.description = data.get('description', '')
        self.available = data.get('isAvailable', False)
        if 'category' in data:
            self.category = Category(data.get('category'))
        else:
            self.category = None


class Series(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        self.type = 'serie'
        self.id = data.get('seriesId')
        self.title = data['title'].strip()
        self.name = data['title'].strip()
        self.description = data.get('description', '')
        self.legal_age = data.get('legalAge') or data.get('aldersgrense')
        self.image_id = data.get('seriesImageId', data.get('imageId'))
        self.available = data.get('isAvailable', False)
        self.category = Category(data.get('category') if 'category' in data else None)
        self.season_ids = self.data.get('seasons', []) or self.data.get('seasonIds', [])

    def seasons(self):
        """Returns a list of sorted list of seasons """

        all_seasons = []  # the lowest seasonnumer in a show in the first season
        # If there isnt a seasons its from /serie/
        sea = self.data.get('seasons') or self.data.get('seasonIds')
        s_list = sorted([s['id'] for s in sea])
        for i, id in enumerate(s_list):
            i += 1  # season 0 is usually specials we dont want that
            s = Season(season_number=i,
                       id=id,
                       series_name=self.name,
                       description=self.description,
                       series_id=self.id)

            all_seasons.append(s)

        return all_seasons

    def episodes(self):
        eps = _fetch('series/%s' % self.id)
        if 'programs' in eps:
            return [Episode(d, seasonIds=self.data.get('seasonIds', [])) for d in _fetch('series/%s' % self.id).get('programs', [])]
        else:
            return []


class Channel(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        self.channel_id = data.get('channelId')
        self.title = data.get('title').strip()
        self.id_live = data.get('isLive')
        self.has_epg = data.get('hasEpg')
        self.priority = data.get('priority')

    def epg(self):
        # pragma: no cover
        # TODO
        guide = [(e.plannedStart, _build(e)) for e in self.data['epg']['liveBufferEpg']]
        return sorted(guide, lambda v: v[0])


class Downloader(object):
    files_to_download = []

    def __init__(self, nrk):
        self.nrk = nrk

    def __len__(self):
        return len(self.files_to_download)

    @classmethod
    def add(cls, media):
        cls.files_to_download.append(media)

    def start(self):
        print('Downloads starting soon.. %s downloads to go' % len(self.files_to_download))
        return self.nrk._download_all(self.files_to_download)

    @classmethod
    def clear(cls):
        print('Cleared downloads')
        cls.files_to_download = []


class Category(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        self.id = data.get('categoryId')
        self.name = data.get('displayValue')
        self.title = data.get('displayValue')


class Audio(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        pass  # todo


class Subtitle(object):
    # tested and works but slow.., add translate?
    all_subs = []

    @classmethod
    def get_subtitles(cls, video_id, name=None, file_name=None, translate=False):
        html = session.get("http://v8.psapi.nrk.no/programs/%s/subtitles/tt" % video_id).text
        if not html:
            return None

        # make sure the show folder exist
        # incase someone just wants to download the sub
        try:
            os.makedirs(os.path.join(SAVE_PATH, name))
        except OSError as e:
            if not os.path.isdir(os.path.join(SAVE_PATH, name)):
                raise

        content = cls._ttml_to_srt(html)
        file_name = '%s.srt' % file_name
        file_name = os.path.join(SAVE_PATH, name, file_name)

        with open(file_name, 'w') as f:
            if not PY3:
                content = content.encode('utf-8', 'ignore')
            f.write(content)
        return file_name

    @classmethod
    def translate(cls, text):  # pragma: no cover
        # check this
        # from https://github.com/jashandeep-sohi/nrksub

        response = session.post('https://translate.googleusercontent.com/translate_f',
                                files={'file': ('trans.txt', '\r\r'.join(text), "text/plain")},
                                data={'sl': 'no',
                                      #'tl': TRANSLATE,
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
    def add(cls):  # pragma: no cover
        pass  # TODO

    @classmethod
    def clear(cls):  # pragma: no cover
        pass  # TODO

    @classmethod
    def start(cls):  # pragma: no cover
        pass  # TODO

    @staticmethod
    def _time_to_str(time):
        return '%02d:%02d:%02d,%03d' % (time / 3600, (time % 3600) / 60, time % 60, (time % 1) * 1000)

    @staticmethod
    def _str_to_time(txt):
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

        output = StringIO()
        for i, (start, end, text) in enumerate(subtitles):
            text = text.replace('<span style="italic">', '<i>') \
                .replace('</span>', '</i>') \
                .replace('&amp;', '&') \
                .split()
            text = ' '.join(text)
            text = re.sub('<br />\s*', '\n', text)

            output.write(u'%s' % (i + 1))
            output.write(u'\n%s' % cls._time_to_str(start))
            output.write(u' --> %s\n' % cls._time_to_str(end))
            output.write(text)
            output.write(u'\n\n')

        return output.getvalue()


def main(): # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('-s', '--search', default=False,
                        required=False, help='Search nrk for a show and download files')

    parser.add_argument('-e', '--encoding', default=None,
                        required=False, help='Set encoding')

    parser.add_argument('-ex', '--expires_at', default=None,
                        required=False, help='Download in all between todays date and 01.01.2020 or just 01-01-2020')

    parser.add_argument('-ce', '--cache', default=None,
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

    parser.add_argument('-w', '--workers', default=None,
                        required=False, help='Number of thread pool workers, if your downloading \
                                              many items you might have edit the chuck')

    parser.add_argument('-st', '--subtitle', action='store_true', default=False,
                        required=False, help='Download subtitle for this media file?')

    parser.add_argument('-if', '--input_file', default=False,
                        required=False, help='Download to this folder')

    parser.add_argument('-c', '--chunks', default=False,
                        required=False, help='')

    # parser.add_argument('-t', '--translate', action='store_true', default=False,
    #                    required=False, help='Translate')

    p = parser.parse_args()

    kw = {'cli': True}

    if p.dry_run:
        kw['dry_run'] = p.dry_run

    if p.workers:
        kw['workers'] = int(p.workers)

    if p.save_path:
        kw['save_path'] = p.save_path

    if p.verbose:
        kw['verbose'] = p.verbose

    if p.subtitle:
        kw['subtitle'] = p.subtitle

    if p.encoding:
        kw['encoding'] = p.encoding

    if p.chunks:
        kw['chunks'] = p.chunks

    nrk = NRK(**kw)

    if p.input_file:
        nrk._from_file(p.input_file)

    if p.url:
        nrk.parse_url(p.url)

    elif p.search:
        nrk._console(p.search)

    elif p.browse:
        nrk._browse()

    elif p.expires_at:
        nrk.expires_at(p.expires_at)


if __name__ == '__main__':  # pragma: no cover
    #if which('ffmpeg') is None:
    #    print('ffmpeg is not installed')
    #    sys.exit(0)
    main()
