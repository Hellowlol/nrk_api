import os
import sys

import pytest
import asyncio


src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')

sys.path.insert(0, src_path)

import pytest
from api import NRK


@pytest.yield_fixture(scope="session")
def runner(request):
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)


        loop = asyncio.get_event_loop()
        yield loop.run_until_complete
        #loop.close()
    else:
        loop = asyncio.get_event_loop()
        yield loop.run_until_complete


@pytest.fixture(scope="function")
def nrk():
    return NRK(cli=True, dry_run=True)
