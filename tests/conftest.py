import pytest

def pytest_addoption(parser):
    parser.addoption("--slow", action="store_true",
                     help="run slow tests")


def pytest_runtest_setup(item):
    if 'slow' in item.keywords and not item.config.getvalue("slow"):
        pytest.skip("need --slow option to run")
