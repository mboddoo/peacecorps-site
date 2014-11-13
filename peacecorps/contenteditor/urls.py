from django.apps import apps
from django.core.urlresolvers import RegexURLPattern, RegexURLResolver
from django.conf import settings
from django.conf.urls import patterns, url
from django.http import HttpResponseRedirect
from django.utils import timezone

from .forms import StrictPasswordChangeForm


def _wrap(callback):
    """Wrap an url callback with a test for password expiration"""
    def inner(request, *args, **kwargs):
        if (request.path in settings.PASSWORD_EXPIRATION_WHITELIST
                or (not request.user.is_authenticated())    # deferring
                or (request.path ==
                    '/admin/auth/user/%d/password/' % request.user.id)
                or (request.user.extra.password_expires > timezone.now())):
            return callback(request, *args, **kwargs)
        else:   # Password expired and not in whitelist
            # @todo: it makes more sense to not hard-code this, but we need to
            # change password validation first
            return HttpResponseRedirect(
                '/admin/auth/user/%d/password/' % request.user.id)
            # return HttpResponseRedirect(reverse('admin:password_change'))
    return inner


def _wrap_patterns(pattern):
    """Modify all elements of a url pattern to wrap them with the _wrap
    function above. This *MUTATES* the patterns in place."""
    if isinstance(pattern, RegexURLPattern):
        pattern._callback = _wrap(pattern.callback)
    elif isinstance(pattern, RegexURLResolver):
        for p in pattern.url_patterns:
            _wrap_patterns(p)
    return pattern


if apps.is_installed('django.contrib.admin'):
    from django.contrib import admin
    altered = [_wrap_patterns(u) for u in admin.site.get_urls()]
    urlpatterns = patterns(
        '',
        #   Override this url, which would appear later in the list
        url(r'^password_change/$',
            'django.contrib.auth.views.password_change',
            {'password_change_form': StrictPasswordChangeForm},
            name='password_change'),
        url(r'^password_change/done/$',
            'django.contrib.auth.views.password_change_done',
            name='password_change_done'),
        url('', (altered, 'admin', 'admin')))
else:
    urlpatterns = []
