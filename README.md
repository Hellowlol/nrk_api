# nrkdl [![Build Status](https://travis-ci.org/Hellowlol/nrkdl.svg?branch=master)](https://travis-ci.org/Hellowlol/nrkdl)  [![Coverage Status](https://coveralls.io/repos/github/Hellowlol/nrkdl/badge.svg?branch=master)](https://coveralls.io/github/Hellowlol/nrkdl?branch=master) ![Supports python 2.6, 2.7, 3.3, 3.4, 3.5](https://img.shields.io/badge/python-2.6%2C%202.7%2C%203.3%2C%203.4%2C%203.5-brightgreen.svg "Logo Title Text 1")
Simple commandline tool to download any/all episodes of a show from nrk/nrk super with python.

## Install

The program has a set of dependencies that must be installed before first use:

    pip install -r requirements.txt

In addition you will need [`ffmpeg`](https://ffmpeg.org/), e.g. `apt-get install ffmpeg` (Ubuntu), `brew install ffmpeg` (macOs)

## Usage

    $ python nrkdl.py -h
    usage: nrkdl.py [-h] [-s keyword] [-e ENCODING] [-ex date] [-u URL] [-b]
                    [-save SAVE_PATH] [-dr] [-v] [-w WORKERS] [-st]
                    [-if INPUT_FILE] [-c CHUNKS] [-d]

    optional arguments:
      -h, --help            show this help message and exit
      -s keyword, --search keyword
                            Search nrk for a show and download files
      -e ENCODING, --encoding ENCODING
                            Set encoding (default=UTF-8)
      -ex date, --expires_at date
                            Download in all between todays date and 01.01.2020 or
                            just 01-01-2020
      -u URL, --url URL     Use NRK URL as sorce. Comma separated e.g. "url1 url2"
      -b, --browse          Browse
      -save SAVE_PATH, --save_path SAVE_PATH
                            Download to this folder (default=./downloads)
      -dr, --dry_run        Dry run, dont download anything
      -v, --verbose         Show ffmpeg output
      -w WORKERS, --workers WORKERS
                            Number of thread pool workers, if your downloading
                            many items you might have edit the chuck
      -st, --subtitle       Download subtitle for this media file?
      -if INPUT_FILE, --input_file INPUT_FILE
                            Use local file as source
      -c CHUNKS, --chunks CHUNKS
      -d, --description     Print verbose program description in lists


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
- Use the search there is loads of nrk options.
