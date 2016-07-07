#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import requests
import os
from os.path import dirname, abspath, join
from json import load, loads
import logging
import sys
import re

c_dir = dirname(abspath(__file__))

if sys.version_info >= (3, 0):
    PY3 = True
    xrange = range
else:
    PY3 = False


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

#@ppatch('C:\Users\admin\Documents\GitHub\nrkdl\responses\search_lille_jack.json')
#@ppatch('C:\Users\admin\Desktop\search_lille_jack.json')
def test(data, *args, **kwargs):
    print(data)

#test()


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
    s = re.sub(r'[-/\\\?%\*|"<>]', '', s).replace(':', '_')
    return s


def _console_select(l, print_args=None):
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
                print(' '.join(x))

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