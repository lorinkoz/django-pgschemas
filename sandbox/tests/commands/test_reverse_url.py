import pytest
from django.core import management
from django.urls.exceptions import NoReverseMatch


def test_urls_for_main_error(db):
    with pytest.raises(NoReverseMatch):
        management.call_command("reverse_url", "entries", schemas=["www"])


def test_urls_for_main_success(stdout, db):
    management.call_command("reverse_url", "register", schemas=["www"], stdout=stdout)
    stdout.seek(0)
    assert stdout.read().strip() == "/register/"


def test_urls_for_blog_error(db):
    with pytest.raises(NoReverseMatch):
        management.call_command("reverse_url", "register", schemas=["blog"])


def test_urls_for_blog_success(stdout, db):
    management.call_command("reverse_url", "entries", schemas=["blog"], stdout=stdout)
    stdout.seek(0)
    assert stdout.read().strip() == "/entries/"
