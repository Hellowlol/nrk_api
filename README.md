# nrkdl
Simple commandline tool to download all episodes of a show from nrk/nrk super with py2/3 (tested with 2.7 and 3.5)

## Search
```
> python nrkdl.py -s "lille jack"
  4: Når lysene tennes...
  3: Visittid
  2: Frieren
  1: På kino i kveld
  0: Lille Jack

Select a number or use slice notation
0

  2: Lille Jack 29:52
  1: Lille Jack 31:52
  0: Lille Jack 32:52

Select a number or use slice notation
::

Downloads starting soon.. 3 downloads to go
100%|############################################################################| 3/3 [03:57<00:00, 79.09s/it]

```

## URL
```
> python nrkdl.py -u "http://tv.nrksuper.no/serie/bernt-og-erling-paa-nye-eventyr http://tv.nrksuper.no/serie/bertine-paa-besoek"
100%|####################################################################################| 2/2 [00:21<00:00, 13.63s/it]
```

## Module
```
s = NRK.search("lille jack", strict=True)[0]
for e in s.episodes():
    e.download()

all_downloads = nrk.downloads()

# How many files are we gonna download
print(len(nrk.downloads()))
# Start downloading
all_downloads.start()

```
See example and source file for more examples

## Other tools
If you prefer a gui you should give https://bitbucket.org/snippsat/wx_nrk a go.
CLI: https://github.com/kvolden/nrk_download