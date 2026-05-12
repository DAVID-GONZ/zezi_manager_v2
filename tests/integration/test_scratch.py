import pytest
pytest_plugins = ["tests.conftest"]

def test_dummy(db_conn):
    assert True
