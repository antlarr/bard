from urllib.parse import urlparse, urljoin
from flask import request, url_for


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc


def get_redirect_target(default='', use_referrer=False):
    print('args:', request.args)
    print('default:', default)
    urls = [request.args.get('next')]
    if use_referrer:
        urls.append(request.referrer)
    for target in urls:
        print('target', target)
        if not target:
            continue
        if is_safe_url(target):
            print('NEXT', target)
            return target
    print('default', default)
    return url_for('catch_all', path=default)
