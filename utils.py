#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

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

#test()


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


def c_out(s, encoding='latin-1'):
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
                x = [c_out(getattr(stuff, x)) for x in print_args]
                x.insert(0, '{0:>3}:'.format(i))
                x = map((lambda x: x.decode('ISO-8859-1').encode(encoding)), x)                
                print(' '.join(x))
                #print ("episode=%s"%stuff.data['description'])
                if description_arg and not stuff.data is None and not stuff.data[description_arg] is None:
                    print("     {0}".format(c_out(stuff.data[description_arg])
                                            .decode('ISO-8859-1').encode(encoding)[:110]))
                    
            except Exception as e:
                print('some crap happend %s' % e)

        elif isinstance(stuff, tuple):  # unbound, used to build a menu
            x = [c_out(stuff[x]) for x in print_args if stuff[x]]
            x.insert(0, '{0:>3}:'.format(i))
            print(' '.join(x))

        else:
            # Normally a dict
            x = [c_out(stuff.get(k, '')) for k in print_args if stuff.get(k)]
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
