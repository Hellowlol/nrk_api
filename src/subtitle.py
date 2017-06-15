#
import logging
import os
import re
from io import StringIO

from aiohttp import ClientSession
import aiofiles


LOG = logging.getLogger(__name__)



class Subtitle(object):

    async def get_subtitle(cls, programid, name=None, file_name=None, save_path=None):
        url = 'http://v8.psapi.nrk.no/programs/%s/subtitles/tt' % programid
        path = os.path.join(save_path, name)
        fullpath = os.path.join(path, '%s.srt' % file_name)
        LOG.debug('Fetching subtitle for %s from %s' % (fullpath, url))

        async with ClientSession() as session:
            async with session.get(url) as resp:
                html = await resp.text()
                srt = cls.convert_ttml_to_srt(html)
                os.makedirs(path, exist_ok=True)

                async with aiofiles.open(fullpath, 'w') as f:
                    await f.write(srt)

                return fullpath

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

    def convert_ttml_to_srt(cls, ttml):
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
        for i in range(0, len(subtitles) - 1):
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

            output.write('%s' % (i + 1))
            output.write('\n%s' % cls._time_to_str(start))
            output.write(' --> %s\n' % cls._time_to_str(end))
            output.write('%s' % text)
            output.write('\n\n')

        return output.getvalue()
