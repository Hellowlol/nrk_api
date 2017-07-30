import logging
from asyncio import ensure_future

import aiohttp


# Lets use all the "free" speedups we can.
try:
    import ujson as json
except ImportError:
    import json

LOG = logging.getLogger(__name__)

API_URL = 'https://tvapi.nrk.no/v1/'
HEADERS = {'app-version-android': '999',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36'}

APICALLS = 0


async def fetch(sess, url, rtype='json'):
    async with sess.get(url, headers=HEADERS) as response:
        try:
            if rtype == 'json':
                return await response.json(loads=json.loads)
            else:
                return await response.text()
        except Exception as e:
            LOG.exception(e)

            return {}


async def httpclient(url, conn=None, session=None, rtype='json'):
    # Roll your own client if you need to set any limits or disable
    # verify certs
    if rtype == 'json':
        url = API_URL + url

    if session is None:
        session = aiohttp.ClientSession(connector=conn, json_serialize=json.dumps)

    async with session as sess:
        return await ensure_future(fetch(sess, url, rtype=rtype))
