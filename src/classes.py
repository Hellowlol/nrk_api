#classes
import asyncio
from datetime import datetime
from operator import itemgetter
import os
import logging
import re

from helpers import clean_name
from subtitle import Subtitle



__all__ = ['build', 'Downloader', 'Program', 'Series', 'Episode', 'Category', 'Channel', 'Contributor']

"""
This module is kinda fucked up. We try build the classes with
many different http reponses. We want to use as little http requests as possible.
"""

LOG = logging.getLogger(__file__)

def build(item, nrk):
    """ Helper function that returns the correct class """

    if item is not None:
        hit_type = item.get('type')
        if hit_type is not None:
            item = item.get('hit')

        if hit_type == 'serie' and item.get('seriesId', '').strip():
            return Series(item, nrk=nrk)
        elif hit_type == 'episode':
            return Episode(item, nrk=nrk)
        else:
            return Program(item, nrk=nrk)


class Downloader:
    files_to_download = []

    def __init__(self, nrk):
        self._nrk = nrk

    def __len__(self):
        return len(self.files_to_download)

    @classmethod
    def add(cls, media):
        cls.files_to_download.append(media)

    async def start(self):
        LOG.debug('Downloads starting soon.. %s downloads to go' % len(self.files_to_download))
        print('Downloads starting soon.. %s downloads to go\n' % len(self.files_to_download))
        files = await self._nrk._download_all(self.files_to_download)
        return files

    def clear(cls):
        LOG.debug('Cleared downloads')
        cls.files_to_download = cls.files_to_download.clear()

    def __str__(cls):
        return str(cls.files_to_download)


class Base:
    def __init__(self, data, nrk=None, *args, **kwargs):
        self._data = data
        self._nrk = nrk
        self._image_url = "http://m.nrk.no/m/img?kaleidoId=%s&width=%d"
        self.image_id = data.get('seriesImageId', data.get('imageId'))
        if 'category' in data:
            self.category = Category(self._data.get('category'), nrk=self._nrk)
        else:
            self.category = None

    @property
    def thumb(self):
        return self._image_url % (self._image_id, 500) if self._image_id else None

    @property
    def fanart(self):
        return self._image_url % (self._image_id, 1920) if self._image_id else None

    async def reload(self, soft=False, force=False):
        await asyncio.sleep(0)
        return self


class Media(Base):
    """ Base class for Episode and Program."""

    def __init__(self, data, nrk=None, *args, **kwargs):
        super().__init__(data, nrk=nrk, *args, **kwargs)
        self._data = data
        self.name = data.get('name', '') or data.get('title', '')
        self._nrk = nrk or kwargs.get('nrk')
        self.name = self.name.strip()
        self.title = data.get('title', '')
        self.type = data.get('type')
        self.id = data.get('programId')
        self.description = data.get('description', '')
        self.legal_age = data.get('legalAge')
        self.has_subtitle = data.get('hasSubtitles')
        self.duration = data.get('duration')
        self.geo_blocked = data.get('usageRights', {}).get('geoblocked', False)
        self.available = data.get('isAvailable', False) or not data.get('usageRights', {}).get('hasNoRights', False)
        self._image_url = "http://m.nrk.no/m/img?kaleidoId=%s&width=%d"
        if self._data.get('episodeNumberOrDate'):
            self.full_title = '%s %s' % (self.name, self._fix_sn(self._data.get('seasonId'),
                                                                 season_ids=kwargs.get('seasonIds')))
        else:
            self.full_title = self.title

        self.file_name = self._filename(self.full_title)
        self.file_path = os.path.join(self._nrk.save_path, clean_name(self.name), self.file_name)
        self.relative_origin_url = data.get('relativeOriginUrl')

    def __hash__(self):
        return hash(repr(self))

    @property
    def available_to(self):
        """Returns a datetime.datetime"""
        try:
            r = datetime.fromtimestamp(int(self._data.get('usageRights', {}).get('availableTo', 0) / 1000), None)
        except (ValueError, OSError, OverflowError):
            r = datetime(year=1970, month=1, day=1)

        return r

    def _filename(self, name=None):
        name = clean_name('%s' % name or self.full_title)
        name = name.replace(' ', '.') + '.WEBDL-nrkdl'
        return name

    def _fix_sn(self, season_number=None, season_ids=None):
        lookup = {}
        stuff = season_ids or self._data.get('series', {}).get('seasonIds')

        # Since shows can have a date..
        # dateregex (\d+\.\s\w+\s\d+)
        not_date = re.search('(\d+:\d+)', self._data.get('episodeNumberOrDate', ''))
        if not_date is None:
            return self._data.get('episodeNumberOrDate', '')

        try:
            for i, d in enumerate(sorted(stuff, key=itemgetter('id')), start=1):
                lookup[str(d['id'])] = 'S%sE%s' % (str(i).zfill(2),
                                                   self._data.get('episodeNumberOrDate', '').split(':')[0].zfill(2))

            return lookup[str(self._data.get('seasonId'))]

        except:
            return self._data.get('episodeNumberOrDate', '')


    async def reload(self, soft=False, force=False):
        await asyncio.sleep(0)
        return self

    @property
    async def media_url(self):
        """ Allow mediaurl to be created manually """
        await asyncio.sleep(0)

        if self._data.get('mediaUrl'):
            return self._data.get('mediaUrl')

        get_it = await self._nrk.client('programs/%s' % self.id)
        return get_it.get('mediaUrl')

    async def download(self, path=None):
        LOG.debug('Adding %s to download que' % self.name)
        if self.available is False:
            LOG.debug('%s isnt available' % self.name)
            # print('Cant download %s' % c_ount(self.name))
            return

        url = await self.media_url
        if url is None:
            LOG.debug('Couldnt get a media url for %s' % self.name)
            return

        if path is None:
            path = self._nrk.save_path

        folder = clean_name(self.name)

        os.makedirs(os.path.join(path, folder), exist_ok=True)

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

    async def subtitle(self):
        return await Subtitle().get_subtitle(self.id, name=self.name,
                                             file_name=self.file_name,
                                             save_path=self._nrk.save_path)


class Episode(Media):
    def __init__(self, data, nrk=None, *args, **kwargs):
        super().__init__(data, nrk=nrk, *args, **kwargs)
        self.season_number = kwargs.get('season_number') or data.get('seasonId')  # fixme
        self.ep_name = data.get('episodeTitle', '') or data.get('episodeNumberOrDate', '')
        self.series_id = data.get('seriesId')
        self.type = 'episode'
        # Because of https://tvapi.nrk.no/v1/programs/MSUS27001913 has no title
        # This is very hacky but we dont want to make more http requests then we have to...
        self.name = kwargs.get('name') or data.get('series', {}).get('title', '') or data.get('seriesTitle') or data.get('title')
        self.full_title = '%s %s' % (self.name, self._fix_sn(self.season_number, season_ids=kwargs.get('seasonIds')))
        self.file_name = self._filename(self.full_title)

    async def episodes(self):
        """Get the episodes from the show."""
        LOG.debug('Fetching all episodes for %s' % self.name)
        parent = await self._nrk.series(self.series_id)
        return await parent.episodes()

    async def reload(self, soft=False, force=False):
        # Soft reload only reloaded if we have a change to get the sxxexx format
        LOG.debug('soft %s reloading %s' % (soft, self.full_title))

        if soft and re.search(r'(\d+:\d+)', self.full_title):
            return await self._nrk.program(self.id)
        elif force:
            return await self._nrk.program(self.id)

        await asyncio.sleep(0)
        return self

    @property
    def more(self):
        """Recommeded stuff based on this item."""
        return [build(i, nrk=self._nrk) for i in self._data.get('series', {}).get('more', [])]

    @property
    def contributors(self):
        return [Contributor(i) for i in self._data.get('series', {}).get('contributor', [])]


class Season:
    def __init__(self, season_number, id,
                 description,
                 series_id,
                 *args,
                 **kwargs):
        self.id = id
        self._nrk = kwargs.get('nrk')
        self.type = 'season'
        self.season_number = season_number
        self.full_title = 'season %s' % season_number
        self.description = description
        self.series_id = series_id

    async def episodes(self):
        """Build return all the Episodes in a list"""
        LOG.debug('Fetching all episodes')
        epdata = await self._nrk.client('series/%s' % self.series_id)
        if epdata:
            return [Episode(d, season_number=self.season_number, nrk=self._nrk) for d in
                    epdata['programs'] if self.id == d.get('seasonId')]
        return []


class Program(Media):
    """ Program is the media element of movies etc """

    def __init__(self, data, nrk=None, *args, **kwargs):
        super().__init__(data, nrk=nrk, *args, **kwargs)
        self.type = 'program'

    async def reload(self, soft=False, force=False):
        if soft:
            return self
        elif force:
            return await self._nrk.program(self.id)

    @property
    def more(self):
        """Recommeded stuff based on this item."""
        return [build(i, nrk=self._nrk) for i in self._data.get('more')]


class Series(Base):
    def __init__(self, data, nrk=None, *args, **kwargs):
        super().__init__(data, nrk=nrk, *args, **kwargs)
        self._data = data
        self._nrk = nrk
        self.type = 'serie'
        self.id = data.get('seriesId')
        self.title = data['title'].strip()
        self.name = data['title'].strip()
        self.full_title = self.name
        self.description = data.get('description', '')
        # self.image_id = data.get('seriesImageId', data.get('imageId'))
        self.category = Category(data.get('category'), nrk=self._nrk if 'category' in data else None)
        self.season_ids = self._data.get('seasons', []) or self._data.get('seasonIds', [])

    async def reload(self, soft=False, force=False):
        """Reload a Series"""

        LOG.debug('Reload %s soft %s' % (self.name, soft))
        await asyncio.sleep(0)
        if soft:
            return self
        elif force:
            return await self._nrk.series(self.id)
        return self

    def seasons(self):
        """Returns a list of sorted list of seasons."""

        all_seasons = []
        # If there isnt a seasons its from /serie/
        sea = self._data.get('seasons') or self._data.get('seasonIds')
        s_list = sorted([s['id'] for s in sea])
        for i, id in enumerate(s_list, 1):
            s = Season(season_number=i,
                       id=id,
                       series_name=self.name,
                       description=self.description,
                       series_id=self.id,
                       nrk=self._nrk)

            all_seasons.append(s)

        return all_seasons

    async def episodes(self):
        """Return a list off off the Episodes of the show."""
        LOG.debug('Fetching all episodes for %s' % self.name)
        # To silence the damn warnings.
        await asyncio.sleep(0)

        if self._data.get('programs', []):
            epdata = self._data.get('programs', [])
        else:
            e = await self._nrk.client('series/%s' % self.id)
            epdata = e.get('programs', [])

        if epdata:
            return [Episode(d, seasonIds=self.season_ids, nrk=self._nrk) for d in epdata]
        else:
            return []

    async def episode(self, season, episode_nr):
        """Get one episode.

           Args:
               season(int): 1
               episode_nr(int): 1

            Returns:
                a Episode

        """

        eps = await self.episodes()
        for ep in eps:
            if ep.season == season and ep.episode_nr == episode_nr:
                return ep

    @property
    def more(self):
        """Recommeded stuff based on this item."""
        return [build(i, nrk=self._nrk) for i in self._data.get('more')]

    @property
    def contributors(self):
        return [Contributor(i) for i in self._data.get('contributor')]


class Channel:
    def __init__(self, data, *args, **kwargs):
        self.channel_id = data.get('channelId')
        self.title = data.get('title').strip()
        self.id_live = data.get('isLive')
        self.has_epg = data.get('hasEpg')
        self.priority = data.get('priority')

    def epg(self):
        pass
        # pragma: no cover
        # TODO
        # guide = [(e.plannedStart, _build(e, nrk=self._nrk)) for e in self._data['epg']['liveBufferEpg']]
        # return sorted(guide, lambda v: v[0])


class Category:
    def __init__(self, data, nrk=None, *args, **kwargs):
        self.id = data.get('categoryId')
        self.name = data.get('displayValue')
        self.title = data.get('displayValue')
        self._nrk = nrk

    async def programs(self):
        eps = await self._nrk.programs(category_id=self.id)
        return eps

    async def reload(self, soft=False, force=False):
        await asyncio.sleep(0)
        return self


class Contributor:
    def __init__(self, data, nrk=None):
        self.name = data.get('name')
        self.rome = data.get('role')

    async def reload(self, soft=False, force=False):
        asyncio.sleep(0)
        return self


class Audio(Media):
    def __init__(self, data, nrk=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        # todo
