from asyncio import ensure_future

import aiohttp


# Lets use all the "free" speedups we can.
try:
    import ujson as json
except ImportError:
    import json

API_URL = 'https://tvapi.nrk.no/v1/'
HEADERS = {'app-version-android': '999',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36'}

APICALLS = 0


async def fetch(sess, url, type='json'):
    async with sess.get(url, headers=HEADERS) as response:
        #print(response.url)
        #global APICALLS
        #APICALLS += 1
        #print(APICALLS) # remove this later..

        try:
            if type == 'json':
                return await response.json(loads=json.loads)
            else:
                return await response.text()
        except:
                return {}


async def httpclient(url, conn=None, session=None, type='json'):
    # Roll your own client if you need to set any limits or disable
    # verify certs
    url = API_URL + url
    if session is None:
        session = aiohttp.ClientSession(connector=conn, json_serialize=json.dumps)

    async with session as sess:
        return await ensure_future(fetch(sess, url, type=type))
