import argparse
import asyncio
import os
import sys
import shutil

from prompt_toolkit.shortcuts import PromptSession

from nrk_api.api import NRK
from nrk_api.helpers import console_select

prompt = PromptSession()
prompt_async = prompt.prompt_async


# Required for subprocesses to work on windows.
if sys.platform == 'win32':  # pragma: no cover
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)


async def search(nrk, q, description=False):
    """Search for a episode or program.description

       Args:
            nrk: NRK()
            q(str): query
            description(bool): Include description.

    """
    to_dl = []
    response = await nrk.search(q)
    select = await console_select(response, ['full_title'], description=description)

    for item in select:
        if item.type == 'serie':
            all_eps = await item.episodes()

            ans = await console_select(all_eps, ['full_title'])
            to_dl += ans
        elif item.type in ('program', 'episode'):
            to_dl.append(item)

    ans = await prompt_async('\nDownload queue is %s do you wish to download everything now? y/n\n> ' % len(to_dl))
    if ans == 'y':
        if nrk.subs:
            for item in to_dl:
                await item.subtitle()
        # Add to download q
        for f in to_dl:
            await f.download()
        return await nrk.downloads().start() if ans == 'y' else nrk.downloads().clear()


async def parse(nrk, q):
    f = await nrk.parse_url(q)
    if nrk.subs:
        for ff in f:
            await ff.subtitle()
    return f


async def expires_at(nrk, date, description=False):
    """Find all videos that expires on a date or in a date range.
       Displays and propts for download.
    """
    items = await nrk.expires_at(date)
    eps = await console_select(items, ['full_title'], description=description)
    [await m.download(os.path.join(nrk.save_path, str(date))) for m in eps]
    ip = await prompt_async('Download que is %s do you wish to download everything now? y/n\n> ' % len(eps))
    await nrk.downloads().start()


async def browse(nrk, description=False):
    """Make interactive menu where you can select and download stuff."""

    categories = await console_select(await nrk.categories(), ['title'])

    # Lets build a menu
    what_programs = [('Popular ' + categories[0].name, nrk.popular_programs),
                     ('Recommended ' + categories[0].name, nrk.recommended_programs),
                     ('Recent ' + categories[0].name, nrk.recent_programs)
                    ]

    x = await console_select(what_programs, [0])
    func = x[0][1]
    result = await func(categories[0].id)
    media_element = await console_select(result, ['full_title'])

    select_all = False
    for element in media_element:
        if nrk.subs is True:
            await element.subtitle()

        if select_all is True:
            await element.download()
            continue

        print('\n%s\n' % element.full_title)
        print('%s\n' % element.description)

        ans = await prompt_async('Do you wish to download this? y/n/c/all\n> ')
        if ans == 'y':
            await element.download()
        elif ans == 'all':
            await element.download()
            select_all = True
        elif ans == 'n':
            continue
        elif ans == 'c':
            break

    if nrk.downloads():
        ans = await prompt_async('Download que is %s do you wish to download everything now? y/n\n> ' % len(nrk.downloads()))
        return await nrk.downloads().start() if ans == 'y' else nrk.downloads().clear()
    return []


def start():  # pragma: no cover

    loop = asyncio.get_event_loop()

    parser = argparse.ArgumentParser(description='CLI tool to download video(s) from NRK.')

    parser.add_argument('-s', '--search', default=False, metavar='keyword',
                        required=False, help='Search nrk for a show and download files')

    parser.add_argument('-d', '--description', action='store_true', default=False,
                        required=False, help='Print verbose program description in console')

    parser.add_argument('-b', '--browse', action='store_true', default=False,
                        required=False, help='Builds a menu where you can choose popular categories')

    # parser.add_argument('-l', '--limit', default=False,
    #                    required=False, help='Limit the download speed to xxx kbs')  # not in use atm

    parser.add_argument('-sub', '--subtitle', action='store_true', default=False,
                        required=False, help='Download subtitle for this program too.')

    parser.add_argument('-dr', '--dry_run', action='store_true', default=False,
                        required=False, help='Dry run, dont download any files.')

    parser.add_argument('-sp', '--save_path', default=False,
                        required=False, help='Set a save path')

    parser.add_argument('-u', '--url', default=False,
                        required=False, help='Use NRK URL as source. Comma separated e.g. "url1, url2"')

    parser.add_argument('--debug', action='store_true', default=False,
                        required=False, help='Enable logging.')

    parser.add_argument('-ea', '--expires_at', default=False,
                        required=False, help='Get all files that looses access rights between two dates or a date')

    parser = parser.parse_args()

    nrk = NRK(cli=True,
              dry_run=parser.dry_run,
              subtitle=parser.subtitle,
              save_path=parser.save_path)

    if parser.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG, filename=os.path.join(nrk.save_path, 'log.txt'))

    if parser.search:
        data = loop.run_until_complete(search(nrk, parser.search, description=parser.description))

    elif parser.browse:
        data = loop.run_until_complete(browse(nrk, description=parser.description))

    elif parser.url:
        data = loop.run_until_complete(parse(nrk, parser.url))

    elif parser.expires_at:
        data = loop.run_until_complete(expires_at(nrk, parser.expires_at, description=parser.description))


if __name__ == '__main__':  # pragma: no cover
    if sys.version_info <= (3, 6, 0):
        print('You need atleast python 3.6.0')
        sys.exit(1)

    if not shutil.which('ffmpeg'):
        print('You need ffmpeg to use the CLI. See https://ffmpeg.org/download.html')
        sys.exit(1)

    start()
