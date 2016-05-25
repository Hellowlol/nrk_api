#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import requests
import os

def ppatch(argument):
    def outer(function):
        def inner(*args, **kwargs):
            import json
            j = None

            try:
                with open(argument, 'r') as f:
                    j = json.load(f)
            except OSError as e:
                print('load failed %s' % e)

                try:
                    j = json.loads(argument)
                except:
                    print('loads failed %s' % e)

            return function(j, *args, **kwargs)
        return inner
    return outer


def make_responses():
    apiurl = 'https://tvapi.nrk.no/v1/'

    d = {'search': 'search/brannman+sam',
         'series': 'series/brannman-sam',
         'program': 'programs/MSUI22009414',
         'programs': 'categories/all-programs/programs',
         'categories': 'categories/',
         'all_programs': 'categories/all-programs/programs',
         'channels': 'channels',
         'popular_programs': 'categories/all-programs/popularprograms',
         'recommanded_programs': 'categories/all-programs/recommendedprograms'
        }

    rp = os.path.join(os.getcwd(), 'responses')

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


make_responses()

#@ppatch('C:\Users\admin\Documents\GitHub\nrkdl\responses\search_lille_jack.json')
@ppatch('C:\Users\admin\Desktop\search_lille_jack.json')
def test(data, *args, **kwargs):
    print(data)

#test()