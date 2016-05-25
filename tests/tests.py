from os.path import dirname, abspath
import sys

sys.path.append(dirname(dirname(abspath(__file__))))

from nrkdl import NRK


def search_live_test():
    r = NRK.search('brannman-sam')
    assert r[0].name == 'Brannmann Sam'


def program_live_test():
    pass


def series_live_test():
    pass


def categories_live_test():
    pass


def programs_live_test():
    r = NRK.programs()
    print(r)

#search_live_test()