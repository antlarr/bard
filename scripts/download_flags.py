#!/usr/bin/env python3

# Copyright 2013 Luca Wehrstedt
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation 
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import re
import json
from urllib.parse import quote
from urllib.request import urlopen, Request

def get_contents(l):
    url = "http://en.wikipedia.org/w/api.php?action=query&prop=revisions&format=json&rvprop=content&redirects=&titles="
    url += "|".join(quote(i) for i in l)

    data = json.loads(urlopen(url).read().decode('utf-8'))

    normalized = {i: i for i in l}
    if "normalized" in data["query"]:
        normalized.update({n["from"]: n["to"] for n in data["query"]["normalized"]})
    redirects = {i: i for i in normalized.values()}
    if "redirects" in data["query"]:
        redirects.update({r["from"]: r["to"] for r in data["query"]["redirects"]})
    contents = {p["title"]: p["revisions"][0]["*"] for p in data["query"]["pages"].values()}

    return {i: contents[redirects[normalized[i]]] for i in l}


def get_flag_pages(l):
    d = get_contents(["Template:Country data %s" % i for i in l])

    result = dict()
    for k, v in d.items():
        result[k[22:]] = re.findall("\|[ \t\r\n]*flag alias[ \t\r\n]*=[ \t\r\n]*(.*?)[ \t\r\n]*\|", v)[0]

    return result


def get_download_urls(l):
    url = "http://en.wikipedia.org/w/api.php?action=query&prop=imageinfo&format=json&iiprop=url&iilimit=1&titles="
    url += "|".join(quote(i) for i in l)

    data = json.loads(urlopen(url).read().decode('utf-8'))

    normalized = {i: i for i in l}
    if "normalized" in data["query"]:
        normalized.update({n["from"]: n["to"] for n in data["query"]["normalized"]})
    redirects = {i: i for i in normalized.values()}
    if "redirects" in data["query"]:
        redirects.update({r["from"]: r["to"] for r in data["query"]["redirects"]})
    contents = {p["title"]: p["imageinfo"][0]["url"] for p in data["query"]["pages"].values()}

    return {i: contents[redirects[normalized[i]]] for i in l}


def do(l):
    d = get_flag_pages(l)
    urls = get_download_urls(["File:%s" % i for i in d.values()])

    for k, v in {k: urls["File:%s" % v] for k, v in d.items()}.items():
        s = urlopen(Request(v, headers={'User-agent': 'Mozilla/5.0'})).read()
        name = "%s%s" % (k, v[v.rindex('.'):])
        open(name, "wb").write(s)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Retrieve country flags from Wikipedia.')
    parser.add_argument('code', nargs='+',
                       help='a country name or code (either ISO, IOC, etc.)')
    args = parser.parse_args()
    for i in range(0, len(args.code), 50):
        do(args.code[i:i+50])