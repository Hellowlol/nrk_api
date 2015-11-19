#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function


import os
import subprocess
import sys
import time
from functools import wraps
import locale
import argparse

import requests

if sys.version_info >= (3, 0):
    PY3 = True
    raw_input = input
else:
    PY3 = False

session = requests.Session()
session.headers['User-Agent'] = 'xbmc.org'
session.headers['app-version-android'] = '51'


def progressbar(count, total, suffix=''):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '#' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s %s\r' % (bar, percents, '%', suffix))
    sys.stdout.flush()

def timeme(func):
    @wraps(func)
    def inner(*args, **kwargs):
        start = time.time()
        res = func(*args)
        print('\n\n%s took %s' % (func.__name__, time.time() - start))
        return res
    return inner

def dl(item):
    url, quality, filename = item
    #print('\nStarted to download %s\n' % filename)
    # encode to the consoles damn charset...
    filename = filename.encode(params.console_encoding)
    cmd = 'ffmpeg -i %s -loglevel quiet -vcodec copy -acodec ac3 "%s.mkv" \n' % (url, filename)
    process = subprocess.Popen(cmd,
                               shell=True,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=None)

    o, e = process.communicate()
    process.stdin.close()
    return 1

def _get_id(id):
    response = _get('/programs/' + id)
    return response.get('mediaUrl')

@timeme
def download_threads(items):
    from multiprocessing.dummy import Pool as ThreadPool
    pool = ThreadPool(10)
    pool.map(dl, items, 1)
    pool.close()
    pool.join()

@timeme
def download_futures_process(items):
    import concurrent.futures as futures
    fut = {}
    n = 0
    with futures.ProcessPoolExecutor(max_workers=8) as executor:
        fut = {executor.submit(dl, item): item for item in items}
        for j in futures.as_completed(fut):
            res = j.result()
            n += res
            progressbar(n, len(items), 'episodes')

@timeme
def download_futures_threads(items):
    import concurrent.futures as futures
    fut = {}
    n = 0
    with futures.ThreadPoolExecutor(max_workers=8) as executor:
        fut = {executor.submit(dl, item): item for item in items}
        for j in futures.as_completed(fut):
            res = j.result()
            n += res
            progressbar(n, len(items), 'episodes')


def _search(query):
    if not PY3:
        q = query.decode(locale.getdefaultlocale()[1])
    else:
        q = query

    response = _get('/search/' + q)

    if response['hits'] is None:
        print('Didnt find shit')
        return
    else:
        # use reverse since 0 is the closest match and i dont want to scoll
        for i, hit in reversed(list(enumerate(response['hits']))):
            print('%s: %s' % (i, hit['hit']['title']))

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

        if isinstance(search_res, dict):
            search_res = [search_res]

        for sr in search_res:
            episodenr = sr['hit']['episodeNumberOrDate']
            showname = sr['hit']['title']
            showid = sr['hit']['seriesId']

            try:
                os.makedirs(showname)
            except:
                pass

            base_folder = os.path.join(os.getcwd(), showname)
            # list all episodes
            show = _get('/series/' + showid)

            if 'programs' in show:
                all_eps = [episode for episode in show['programs'] if episode['isAvailable']]
            else:
                print('There are no available episodes for %s' % showname)
                return

            # Find all the stream urls:
            all_streams = []
            for ep in all_eps:
                has_url = _get_id(ep['programId'])
                if has_url:
                    filename = '%s_%s' % (ep['title'], ep['episodeNumberOrDate'].replace(':', '_'))
                    f_path = os.path.join(base_folder, filename)
                    # set quality # TODO
                    t = (has_url, 'high', f_path)
                    all_streams.append(t)

            print('\n%s files to download\n' % len(all_streams))

            if len(all_streams):
                progressbar(0, len(all_streams), 'Episodes')
                download_futures_threads(all_streams)



def _get(path):
    r = session.get("http://m.nrk.no/tvapi/v1" + path)
    r.raise_for_status()
    return r.json()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--search', default=False, required=True,
                        help='Search nrk for a show and download all available eps')
    parser.add_argument('--url', default=False,
                        help='url')
    parser.add_argument('--console_encoding', default='cp850',
                        help='Run chcp in your console to find your encoding')
    params = parser.parse_args()
    if params.url:
        pass # TODO
    elif params.search:
        _search(params.search)


    '''
        This script will download every available episode

        ## Usage ##
        python nrkdownload.py --search "Øisteins Blyant"
        3 Lille Øisteins Blyant
        2 Øisteins Blyant ABC
        1 Øisteins Blyant
        0 Øisteins Jule Blyant

        Enter the shownumber or use a slice notation
        -2::
    '''
