import asyncio
import os
import sys

import pytest


src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')

sys.path.insert(0, src_path)


from api import NRK


def pytest_addoption(parser):
    parser.addoption("--slow", action="store_true",
                     help="run slow tests")


def pytest_runtest_setup(item):
    if 'slow' in item.keywords and not item.config.getvalue("slow"):
        pytest.skip("need --slow option to run")


@pytest.yield_fixture(scope="session")
def runner(request):
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)

        loop = asyncio.get_event_loop()
        yield loop.run_until_complete
        loop.close()  # We dont add this since it emits warnings when running pytest
    else:
        loop = asyncio.get_event_loop()
        yield loop.run_until_complete
        loop.close()


@pytest.fixture(scope="function")
def nrk():
    return NRK(cli=True, dry_run=True)
