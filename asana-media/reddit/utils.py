# The contents of this file are subject to the Common Public Attribution
# License Version 1.0. (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://code.reddit.com/LICENSE. The License is based on the Mozilla Public
# License Version 1.1, but Sections 14 and 15 have been added to cover use of
# software over a computer network and provide for limited attribution for the
# Original Developer. In addition, Exhibit A has been modified to be consistent
# with Exhibit B.
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License for
# the specific language governing rights and limitations under the License.
#
# The Original Code is reddit.
#
# The Original Developer is the Initial Developer.  The Initial Developer of
# the Original Code is reddit Inc.
#
# All portions of the code written by reddit are Copyright (c) 2006-2015 reddit
# Inc. All Rights Reserved.
###############################################################################

import codecs
import re


from BeautifulSoup import BeautifulSoup
from urllib2 import urlopen, Request


def get_title(url):
    """Fetch the contents of url and try to extract the page's title."""
    if not url or not url.startswith(('http://', 'https://')):
        return None

    try:
        req = Request(url)
        opener = urlopen(req, timeout=15)

        # determine the encoding of the response
        for param in opener.info().getplist():
            if param.startswith("charset="):
                param_name, sep, charset = param.partition("=")
                codec = codecs.getreader(charset)
                break
        else:
            codec = codecs.getreader("utf-8")

        with codec(opener, "ignore") as reader:
            # Attempt to find the title in the first 1kb
            data = reader.read(1024)
            title = extract_title(data)

            # Title not found in the first kb, try searching an additional 10kb
            if not title:
                data += reader.read(10240)
                title = extract_title(data)
    except:
        return None

    return title


def extract_title(data):
    """Try to extract the page title from a string of HTML.

    An og:title meta tag is preferred, but will fall back to using
    the <title> tag instead if one is not found. If using <title>,
    also attempts to trim off the site's name from the end.
    """
    bs = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)
    if not bs or not bs.html.head:
        return
    head_soup = bs.html.head

    title = None

    # try to find an og:title meta tag to use
    og_title = (head_soup.find("meta", attrs={"property": "og:title"}) or
                head_soup.find("meta", attrs={"name": "og:title"}))
    if og_title:
        title = og_title.get("content")

    # if that failed, look for a <title> tag to use instead
    if not title and head_soup.title and head_soup.title.string:
        title = head_soup.title.string

        # remove end part that's likely to be the site's name
        # looks for last delimiter char between spaces in strings
        # delimiters: |, -, emdash, endash,
        #             left- and right-pointing double angle quotation marks
        reverse_title = title[::-1]
        to_trim = re.search(u'\s[\u00ab\u00bb\u2013\u2014|-]\s',
                            reverse_title,
                            flags=re.UNICODE)

        # only trim if it won't take off over half the title
        if to_trim and to_trim.end() < len(title) / 2:
            title = title[:-(to_trim.end())]

    if not title:
        return

    # get rid of extraneous whitespace in the title
    title = re.sub(r'\s+', ' ', title, flags=re.UNICODE)

    return title.encode('utf-8').strip()
