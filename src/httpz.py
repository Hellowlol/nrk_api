# http
import sys
from asyncio import ensure_future

#for item in sys.path:
#    print(item)

import aiohttp


# Lets use all the "free" speedups we can.
try:
    import ujson as json
except ImportError:
    import json

API_URL = 'https://tvapi.nrk.no/v1/'
HEADERS = {'app-version-android': '999',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36'}

async def fetch(sess, url):
    async with sess.get(url, headers=HEADERS) as response:
        print(response.url)
        #print('\n')
        f = ensure_future(response.json())

        #print(f)
        return await f


async def httpclient(url, conn=None, session=None):
    # Roll your own client if you need to set any limits or disable
    # verify certs
    url = API_URL + url
    if session is None:
        session = aiohttp.ClientSession(connector=conn, json_serialize=json.dumps)

    async with session as sess:
        return await fetch(sess, url)
