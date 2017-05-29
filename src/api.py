import os
import re
import sys
from urllib.parse import quote_plus

#for item in sys.path:
#    print(item)


#import nrkdl
from httpz import httpclient
from helpers import clean_name


SAVE_PATH = os.path.expanduser('~/nrkdl')


def _build(item, nrk):
    """ Helper function that returns the correct class """
    if item is not None:
        hit_type = item.get('type')
        if hit_type is not None:
            item = item.get('hit')

        if hit_type == 'serie' or item.get('seriesId') is not None and item.get('seriesId', '').strip():
            return Series(item, nrk=nrk)
        elif hit_type == 'episode':
            return Episode(item, nrk=nrk)
        else:
            return Program(item, nrk=nrk)


class NRK(object):
    """ Main object"""

    def __init__(self,
                 dry_run=False,
                 client=None,
                 verbose=False,
                 save_path=None,
                 subtitle=False,
                 cli=False,
                 include_description=False,
                 *args,
                 **kwargs):

        self.dry_run = dry_run
        self.verbose = verbose
        self.client = client or httpclient
        self.subs = subtitle
        self.cli = cli
        self.include_description = include_description

        # Set a default ssl path
        self.save_path = save_path or SAVE_PATH

        # Make sure the save_path exist
        os.makedirs(self.save_path, exist_ok=True)

    async def series(self, series_id):
        return Series(await self.client('series/%s' % series_id), nrk=self)


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
                    If raw is false it will return a Program, Episode or series,
                    else json
        """

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


    async def site_rip(self):  # pragma: no cover
        """ Dont run this.. """
        added_ids = []
        program_ids = []
        series_ids = []
        series = []
        programs = []
        total = 0
        for category in await self.client('categories'):
            await asyncio.sleep(0)
            if category.get('categoryId') != 'all-programs':  # useless shit...
                cat = await self.client('categories/%s/programs' % category.get('categoryId'))
                for i in cat:
                    await asyncio.sleep(0)
                    #print(i)
                    if i.get('seriesId', '').strip() != '':
                        if i.get('seriesId', '') not in added_ids:
                            series_ids.append(i.get('seriesId', ''))
                            try:
                                s = asyncio.ensure_future(self.series(i.get('seriesId', '')))
                                series.append(s)
                            except:
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
                            except:
                                # CRAPS out if json is shit. IDK
                                pass
        #print(type(programs))
        print('Found:\n')


        sss = await asyncio.gather(*series)
        progs = await asyncio.gather(*programs)
        #print('%s series' % len(series))
        for s in sss:
            eps = await s.episodes()
            total += len(eps)

        #print('%s episodes' % total)
        print('%s programs' % len(programs))
        print('%s media files in total' % (total + len(programs)))
        return sss + programs


class Media(object):
    """ Base class for all the media elements """

    def __init__(self, data, nrk=None, *args, **kwargs):
        self.data = data
        self.name = data.get('name', '') or data.get('title', '')
        self._nrk = nrk or kwargs.get('nrk')
        self.name = self.name.strip()
        self.title = data.get('title', '')
        self.type = data.get('type')
        self.id = data.get('id')
        self.available = data.get('isAvailable', False)
        self._image_url = "http://m.nrk.no/m/img?kaleidoId=%s&width=%d"
        if self.data.get('episodeNumberOrDate'):
            self.full_title = '%s %s' % (self.name, self._fix_sn(self.data.get('seasonId'),
                                                                 season_ids=kwargs.get('seasonIds')))
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
            for i, d in enumerate(sorted(stuff, key=lambda k: k['id']), start=1):
                lookup[str(d['id'])] = 'S%sE%s' % (str(i).zfill(2), self.data.get('episodeNumberOrDate', '').split(':')[0].zfill(2))

            return lookup[str(self.data.get('seasonId'))]

        except:
            return self.data.get('episodeNumberOrDate', '')

    def as_dict(self):
        """ raw response """
        return self.data

    def subtitle(self):
        """ download a subtitle """
        return Subtitle().get_subtitles(self.id, name=self.name, file_name=self.file_name)

    async def __media_url(self, media_id):
        resp = await self.client('programs/%s' % media_id)
        return resp.get('mediaUrl', '')

    @property
    async def media_url(self):
        """ Allow mediaurl to be created manually """
        media_id = self.self.data('seriesId') if self.type != 'serie' else self.data.get('programId')
        return await self.__media_url(media_id)
        #return get_media_url(self.id if self.type != 'serie' else self.data.get('programId'))

    async def download(self, path=None):
        if self.available is False:
            # print('Cant download %s' % c_ount(self.name))
            return

        url = await self.media_url
        if url is None:
            return

        if path is None:
            path = self.save_path

        folder = clean_name(self.name)

        os.makedirs(self.save_path, exist_ok=True)

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
        super().__init__(data, *args, **kwargs)
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
        self.available = data.get('isAvailable', False) or not data.get('usageRights', {}).get('hasNoRights', False)
        if 'category' in data:
            self.category = Category(data.get('category'))
        else:
            self.category = None


class Series(Media):
    def __init__(self, data, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
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
        # since the damn warnings
        await asyncio.sleep(0)

        if self.data.get('programs', []):
            epdata = self.data.get('programs', [])
        else:
            e = await self._nrk.client('series/%s' % self.id)
            epdata = e.get('programs', [])

        if epdata:
            return [Episode(d, seasonIds=self.season_ids) for d in epdata]
        else:
            return []



    #def episodes(self):
    #    return self._episodes()
        #eps = await self._nrk.client('series/%s' % self.id)
        #if 'programs' in eps:
        #    return [Episode(d, seasonIds=self.data.get('seasonIds', [])) for d in _fetch('series/%s' % self.id).get('programs', [])]
        #else:
        #    return []


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


class Category(Media):
    def __init__(self, data, *args, **kwargs):
        super(self.__class__, self).__init__(data, *args, **kwargs)
        self.id = data.get('categoryId')
        self.name = data.get('displayValue')
        self.title = data.get('displayValue')












if __name__ == '__main__':
    import asyncio
    import sys

    nrk = NRK()

    async def lol():
        search_result = await nrk.search('skam', strict=True)
        for item in search_result:
            if item.type == 'serie':
                for ep in await item.episodes():
                    print(ep.full_title)


        #mu = await f[0].media_url
        #print(mu)
        return

    async def sr():
        r = await nrk.site_rip()
        return r

    loop = asyncio.get_event_loop()
    loop.run_until_complete(sr())
