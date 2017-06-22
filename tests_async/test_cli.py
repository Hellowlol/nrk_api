from unittest import mock
import pytest

not_impl = pytest.mark.skip(reson='not implemented')


@not_impl
def test_parse(runner):
    pass


@not_impl
def test_search(runner):
    pass


@not_impl
def test_expire_at(runner):
    pass


@not_impl
def test_browse(runner):
    pass
