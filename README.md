# nrkdl [![Build Status](https://travis-ci.org/Hellowlol/nrkdl.svg?branch=master)](https://travis-ci.org/Hellowlol/nrkdl)  [![Coverage Status](https://coveralls.io/repos/github/Hellowlol/nrkdl/badge.svg?branch=master)](https://coveralls.io/github/Hellowlol/nrkdl?branch=master) ![Supports python 3.5, 3.6](https://img.shields.io/badge/python-3%2C5%203.6-green.svg "3.5, 3.6")
API for NRK. (Norsk rikskringkasting)

## Install
pip install nrk_api

The api was made to support to create a cli tool.

Simple commandline tool to download any/all episodes of a show from nrk/nrk super with python.


#CLI

In addition you will need [`ffmpeg`](https://ffmpeg.org/), e.g. `apt-get install ffmpeg` (Ubuntu), `brew install ffmpeg` (macOs)

## Usage

    usage: nrkdl [-h] [-s keyword] [-d] [-b] [-sub] [-dr] [-sp SAVE_PATH] [-u URL]
             [-ea EXPIRES_AT]

    CLI tool to download video from NRK.

    optional arguments:
      -h, --help            show this help message and exit

      -s keyword, --search keyword
                            Search nrk for a show and download files

      -d, --description     Print verbose program description in console
      -b, --browse          Builds a menu where you can choose popular categories
      -sub, --subtitle      Download subtitle for this program too.
      -dr, --dry_run        Dry run, dont download any files.
      -sp SAVE_PATH, --save_path SAVE_PATH
                        Set a save path
      -u URL, --url URL     Use NRK URL as source. Comma separated e.g. "url1, url2"
      -ea EXPIRES_AT, --expires_at EXPIRES_AT
                        Get all files that looses access rights between two
                        dates or a date


## Search
```
> python nrkdl.py -s "brannma"
  2: Brannmann i seks knop
  1: Brannmann
  0: Brannmann Sam

Select a number or use slice notation
0

  .....
  .....
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
> nrkdl -u "http://tv.nrksuper.no/serie/bernt-og-erling-paa-nye-eventyr http://tv.nrksuper.no/serie/bertine-paa-besoek"
100%|####################################################################################| 2/2 [00:21<00:00, 13.63s/it]
```

## Module
```
nrk = NRK()
s = await nrk.search("lille jack", strict=True)[0]
for e in await s.episodes():
    await e.download()

all_downloads = nrk.downloads()

# How many files are we gonna download
print(len(nrk.downloads()))
# Start downloading
await all_downloads.start()

```
See example and source file for more examples

## Using Docker

To use `nrkdl` in a self-contained docker container, the provieded `Dockerfile` should get you going for a minimalistic install.
If you want to combine this into a standalone command, something like this will be what you want.
```sh
#!/bin/sh

# export DATA="/mnt/multimedia/tmp" # Set if you don't want downloads to go to your ${HOME}/downloads
cd ${HOME}/Projects/programming/nrkdl  # Path where we can find a checkout of this repository
docker run -it -v ${DATA:-${HOME}/downloads}:/nrkdl/downloads $(docker build -q .) $*

# Open data-path if we are on osx
# [[ $? == 0 ]] && ( open ${DATA} )
```

You can now run it using example `nrkdl -s "brannma"`.

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
- [nrk-download cli tool](https://github.com/marhoy/nrk-download)
- Use the search there is loads of nrk options.

