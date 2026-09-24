import pytest


@pytest.mark.req("REQ-FIX-10")
def test_marker_form():
    assert True


def test_REQ_FIX_11_name_token():
    assert True


# covers REQ-FIX-16
def test_comment_only_does_not_count():
    assert True
