#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division, print_function

import datetime
from functools import wraps
from json import load, loads
import logging
import os
from os.path import dirname, abspath, join
import re
import sys
import time

import requests

c_dir = dirname(abspath(__file__))

if sys.version_info >= (3, 0):
    PY3 = True
    xrange = range
else:
    PY3 = False


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


def ppatch(ff=None):
    def outer(function):
        def inner(*args, **kwargs):
            j = None

            if ff:
                argument = join(dirname(abspath(__file__)), 'responses', ff)

            try:
                with open(argument, 'r') as f:
                    j = load(f)
            except:
                try:
                    j = loads(argument)
                except:
                    pass

            if j is None:
                # default to file path
                j = argument

            return function(j, *args, **kwargs)
        return inner
    return outer

#@ppatch('C:\Users\admin\Documents\GitHub\nrkdl\responses\search_lille_jack.json')
#@ppatch('C:\Users\admin\Desktop\search_lille_jack.json')
def test(data, *args, **kwargs):
    print(data)

def make_responses():
    apiurl = 'https://tvapi.nrk.no/v1/'

    d = {'search': 'search/brannman+sam',
         'series': 'series/brannman-sam',
         'program': 'programs/msui22009314',
         'programs': 'categories/all-programs/programs',
         'categories': 'categories/',
         'all_programs': 'categories/all-programs/programs',
         'channels': 'channels',
         'popular_programs': 'categories/all-programs/popularprograms',
         'recommanded_programs': 'categories/all-programs/recommendedprograms'
         }

    rp = join(c_dir, 'responses')

    try:

        os.makedirs(rp)
    except OSError as e:
        if not os.path.isdir(rp):
            raise

    for k, v in d.items():
        try:
            r = requests.get(apiurl + v, headers={'app-version-android': '999'})

            if r.content:
                with open(os.path.join(rp, k + '.json'), 'w') as f:
                    f.write(r.content)

            print('Updated the response of %s' % k)
        except Exception as e:
            print(e)


def timeme(func):
    @wraps(func)
    def inner(*args, **kwargs):
        start = time.time()
        res = func(*args)
        logging.info('\n\n%s took %s' % (func.__name__, time.time() - start))
        return res
    return inner


def c_out(s, encoding='utf-8'):
    if not PY3:
        return s.encode(encoding, 'ignore')
    else:
        return s


def compat_input(s=''):
    try:
        return raw_input(s)
    except NameError:
        return input(s)


def clean_name(s):
    """ remove all illegal chars for ffmpeg"""
    s = re.sub(r'[-/\\\?%\*|"<>]', '', s).replace(':', '_')
    s = ' '.join(s.split()).strip()
    return s


def _console_select(l, print_args=None, encoding="UTF-8", description_arg=None):
    """ Helper function to allow grab dicts/objects from list with ints and slice. """
    print('\n')

    if isinstance(l, dict):
        l = [l]

    if print_args is None:
        print_args = []

    for i, stuff in reversed(list(enumerate(l))):

        if not isinstance(stuff, (list, dict, tuple)):  # classes, functions
            try:
                x = [c_out(getattr(stuff, x), encoding=encoding) for x in print_args]
                x.insert(0, '{0:>3}:'.format(i))
                print(' '.join(x))
                if description_arg and stuff.data is not None and stuff.data[description_arg] is not None:
                    print("     {0}".format(c_out(stuff.data[description_arg], encoding=encoding)[:110].replace("\r", " ").replace("\n", " ")))

            except Exception as e:
                print('some crap happend %s' % e)

        elif isinstance(stuff, tuple):  # unbound, used to build a menu
            x = [c_out(stuff[x], encoding=encoding) for x in print_args if stuff[x]]
            x.insert(0, '{0:>3}:'.format(i))
            print(' '.join(x))

        else:
            # Normally a dict
            x = [c_out(stuff.get(k, ''), encoding=encoding) for k in print_args if stuff.get(k)]
            x.insert(0, '{0:>3}:'.format(i))
            print(' '.join(x))

    # select the grab...
    grab = compat_input('\nSelect a number or use slice notation\n')
    # Check if was slice..
    if any(s in grab for s in (':', '::', '-')):
        grab = slice(*map(lambda x: int(x.strip()) if x.strip() else None, grab.split(':')))
        l = l[grab]
    else:
        l = l[int(grab)]

    if not isinstance(l, list):
        l = [l]

    return l


def which(program):
    # http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    def ext_candidates(fpath):
        for ext in os.environ.get("PATHEXT", "").split(os.pathsep):
            yield fpath + ext

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            for candidate in ext_candidates(exe_file):
                if is_exe(candidate):
                    return candidate


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

def to_ms(s=None, des=None, **kwargs):
    if s:
        hour = int(s[0:2])
        minute = int(s[3:5])
        sec = int(s[6:8])
        ms = int(s[10:11])
    else:
        hour = int(kwargs.get('hour', 0))
        minute = int(kwargs.get('min', 0))
        sec = int(kwargs.get('sec', 0))
        ms = int(kwargs.get('ms'))

    result = (hour * 60 * 60 * 1000) + (minute * 60 * 1000) + (sec * 1000) + ms
    if des and isinstance(des, int):
        return round(result, des)
    return result


def multi_progress_thread(func=None, tasks=None, workers=None):
    """ tqdm nested helper if we dont know the range of the iterable and using treads.

        The idea is pretty simple. Each task reports the progress to the queue
        We read the queue and increment the progress bars.

        tasks (list): of tuples, used as args for func
        func: Teh function to execute in the threads, func must yield a progress in int

    """
    from functools import partial

    try:
        from queue import Queue as queue
    except ImportError:
        from Queue import Queue as queue

    import workerpool
    import tqdm

    class JOBZ(workerpool.Job):
        def __init__(self, q, task_number, func=None):
            """Args:
            q: queue
            n: tasknumber
            func: function to execute

            """
            self.q = q
            self.n = task_number
            self.func = func

        def run(self):
            for i in self.func():
                self.q.put((self.n, i))

            # Set check done.
            self.q.put((self.n, 'done'))

    assert callable(func)

    q = queue()
    len_tasks = len(tasks)
    if workers is None:
        workers = len_tasks

    pool = workerpool.WorkerPool(size=workers)
    bars = []
    bar_format = '{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'

    main_bar = tqdm.tqdm(total=len_tasks, position=0,
                         mininterval=0.02, dynamic_ncols=True,
                         smoothing=1, desc='Total',
                         bar_format=bar_format)

    for i, task in enumerate(tasks):

        # Increment the position since we want the
        # main_bar to be on top.
        pos = i + 1

        wrap_func = partial(func, task)
        j = JOBZ(q, i, wrap_func)
        pool.put(j)
        dl_name = os.path.basename(task[2])

        f = partial(tqdm.tqdm, total=100, mininterval=0.02,
                    position=pos, miniters=1, dynamic_ncols=True,
                    leave=True, smoothing=1, bar_format=bar_format,
                    desc='%s' % dl_name)
        bars.append(f())

    exit = 0
    progress = {}
    while True:
        try:
            # Check if we should exit the thread and update the bars
            if exit == len_tasks:

                # Update sub-bars because of the exit
                for bb in bars:
                    bb.n = 100
                    bb.update(100)

                    # Update main bar.
                    main_bar.n = 0
                    main_bar.update(len_tasks)
                break

            item = q.get()
            if item is not None:
                t, i = item
                #print(i)

                if i == 'done':
                    exit += 1
                    b = bars[t]
                    b.n = 100
                    b.update(100)
                    continue

                b = bars[t]
                b.n = 0
                b.update(i)

                # Add current progress to a dict
                # since it can only hold the last value
                progress[str(t)] = i

                main_bar_progress = round(sum(progress.values()) / 100, 2)
                main_bar.n = 0
                main_bar.update(main_bar_progress)

        except KeyboardInterrupt:
            break

    pool.shutdown()
    pool.join()
