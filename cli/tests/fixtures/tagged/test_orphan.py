import pytest


@pytest.mark.req("REQ-FIX-99")
def test_points_at_an_unknown_requirement():
    assert True
