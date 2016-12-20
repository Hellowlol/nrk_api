# nrkdl [![Build Status](https://travis-ci.org/Hellowlol/nrkdl.svg?branch=master)](https://travis-ci.org/Hellowlol/nrkdl)  [![Coverage Status](https://coveralls.io/repos/github/Hellowlol/nrkdl/badge.svg?branch=master)](https://coveralls.io/github/Hellowlol/nrkdl?branch=master) ![Supports python 2.6, 2.7, 3.3, 3.4, 3.5](https://img.shields.io/badge/python-2.6%2C%202.7%2C%203.3%2C%203.4%2C%203.5-brightgreen.svg "Logo Title Text 1")
Simple commandline tool to download any/all episodes of a show from nrk/nrk super with python.

## Search
```
> python nrkdl.py -s "brannma"
  2: Brannmann i seks knop
  1: Brannmann
  0: Brannmann Sam

Select a number or use slice notation
0

 22: Brannmann Sam S03E06
 21: Brannmann Sam S03E12
 20: Brannmann Sam S03E13
 19: Brannmann Sam S03E14
 18: Brannmann Sam S03E15
 17: Brannmann Sam S03E16
 16: Brannmann Sam S03E17
 15: Brannmann Sam S03E18
 14: Brannmann Sam S03E19
 13: Brannmann Sam S03E20
 12: Brannmann Sam S03E21
 11: Brannmann Sam S03E22
 10: Brannmann Sam S03E23
  9: Brannmann Sam S03E24
  8: Brannmann Sam S03E25
  7: Brannmann Sam S03E26
  6: Brannmann Sam S03E27
  5: Brannmann Sam S03E28
  4: Brannmann Sam S03E29
  3: Brannmann Sam S03E30
  2: Brannmann Sam S03E32
  1: Brannmann Sam S03E33
  0: Brannmann Sam S05E25

Select a number or use slice notation
::

Downloads starting soon.. 23 downloads to go
100%|############################################################################| 23/23 [03:57<00:00, 79.09s/it]

```

## URL
```
> python nrkdl.py -u "http://tv.nrksuper.no/serie/bernt-og-erling-paa-nye-eventyr http://tv.nrksuper.no/serie/bertine-paa-besoek"
100%|####################################################################################| 2/2 [00:21<00:00, 13.63s/it]
```

## Module
```
nrk = NRK()
s = nrk.search("lille jack", strict=True)[0]
for e in s.episodes():
    e.download()

all_downloads = nrk.downloads()

# How many files are we gonna download
print(len(nrk.downloads()))
# Start downloading
all_downloads.start()

```
See example and source file for more examples

## Why should you use this library?
- Easy to download entire shows
- Browsing features
- Fixes up tvshows fucked up naming so it can be parsed by kodi/plex/emby
- Pretty fast, maxes my 500 mbit connection.

## Similar tools
- [If you need a gui](https://bitbucket.org/snippsat/wx_nrk "snippsats wx_nrk")
- [Other cli tool](https://github.com/kvolden/nrk_download "nrk_download")
- [nrk written in php](https://github.com/AndKe/nrk)
- [nrk-tv-downloader written in bash](https://github.com/odinuge/nrk-tv-downloader)
- Use the search there is loads of nrk options.
