#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

from os.path import dirname, abspath
import sys

sys.path.append(dirname(dirname(abspath(__file__))))

if sys.version_info >= (3, 0):
    PY3 = True
else:
    PY3 = False

from nrkdl import NRK

def c_out(s):
    if not PY3:
        return s.encode('latin-1', 'ignore')
    else:
        return s


def search_live_test():
    r = NRK.search('brannman-sam')
    assert r[0].name == 'Brannmann Sam'


def program_live_test():
    r = NRK.program('msui22009314')
    assert r[0].full_title == 'Brannmann Sam 23:26'

def download_live_test():
    r = NRK.program('msui22009314')
    url, q, fp = r[0].download(path='test') # fix path
    assert url == 'http://nordond26c-f.akamaihd.net/i/no/open/12/12e45a2be69e24cb072f9d92a9c30727224ddd0e/7595713e-ee38-4325-8d05-c0ac2e2fd53c_,141,316,563,1266,2250,.mp4.csmil/master.m3u8?cc1=uri%3Dhttps%3a%2f%2fundertekst.nrk.no%2fprod%2fMSUI22%2f00%2fMSUI22009314AA%2fTMP%2fmaster.m3u8%7Ename%3DNorsk%7Edefault%3Dyes%7Eforced%3Dno%7Elang%3Dnb'
    assert q == 'high'
    assert fp.endswith('Brannmann Sam\Brannmann Sam 23_26')
    assert len(NRK.downloads()) == 1


def series_live_test():
    r = NRK.series('brannman-sam')
    pass


def categories_live_test():
    pass


def programs_live_test():
    r = NRK.programs()

def site_rip_live_test():
    r = NRK.site_rip()
    all_names = []
    for i in r:
        print(i.name.encode('latin-1'))


#download_live_test()
#search_live_test()
#program_live_test()
#series_live_test()
#site_rip_live_test()
