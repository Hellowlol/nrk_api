import os
import sys

import pytest
import asyncio




src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
#print(src_path)

sys.path.insert(0, src_path)

import pytest
#import pytest_asyncio.plugin

from api import NRK


@pytest.yield_fixture
def runner(request):
    if sys.platform == 'win32':
        print('fuck mann')
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)


    loop = asyncio.get_event_loop()
    print(loop)
    yield loop.run_until_complete
    loop.close()



@pytest.fixture
def nrk():
    return NRK(cli=True, dry_run=True)
