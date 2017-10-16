# -*- coding: utf-8 -*-
#! /usr/bin/env python3

MOMENT_COMPONENT_JSON_URL = (
    "https://raw.githubusercontent.com/moment/moment/develop/component.json")

REQUEST_TIMEOUT = 6
REQUEST_MAX_RETRIES = 5


def retry_urlopen(request, timeout=REQUEST_TIMEOUT, n_retries=REQUEST_MAX_RETRIES):
    from six.moves.urllib.request import urlopen
    i = 0
    while True:
        try:
            result =  urlopen(request, timeout=timeout).read()
            return result
        except Exception as e:
            from six.moves.urllib.error import URLError
            from socket import timeout as TimeoutError
            if not isinstance(e, (URLError, TimeoutError)):
                raise e
            if not "timed out" in str(e).lower():
                raise e
            i += 1
            if i > n_retries:
                raise e
            print("\rRequest timed out, retry (%s/%s). " % (
                i, n_retries), flush=True, end="")
            import time
            time.sleep(0.1)


def get_names():
    from six.moves.urllib.request import Request
    import json
    request = Request(MOMENT_COMPONENT_JSON_URL)
    moment_component_files = json.loads(retry_urlopen(request).decode())["files"]
    moment_supported_langs_set = set([name.replace("locale/", "").replace(".js", "")
                              for name in moment_component_files
                              if name.startswith("locale/")])

    from django.conf.locale import LANG_INFO
    django_supported_langs = set(list(LANG_INFO.keys()))

    moment_already_supported = (
        moment_supported_langs_set.intersection(django_supported_langs))

    known_fallbacks = {
        # For Chinese
        'zh-hans': "zh-cn",
        'zh-my': "zh-cn",
        'zh-sg': "zh-cn",
        'zh-hant': "zh-tw",  # or 'zh-hk'
        'zh-mo': "zh-tw",

        # For Spanish
        'es-ar': "es",
        'es-co': "es",
        'es-mx': "es",
        'es-ni': "es",
        'es-ve': "es",
    }

    for l in known_fallbacks.keys():
        try:
            assert l not in moment_already_supported
        except:
            raise ValueError("'%s' is now supported by moment.js, "
                             "please remove it from known_fallbacks" % l)

    not_supported = (
        django_supported_langs
            .difference(moment_supported_langs_set)
            .difference(set(list(known_fallbacks.keys())))
            .difference({"en", "en-us"}))

    print(repr(known_fallbacks))
    print(repr(sorted(list(not_supported))))


if __name__ == "__main__":
    get_names()
