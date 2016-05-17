# nrkdl
Simple commandline tool to download all episodes of a show from nrk/nrk super with py2/py3

## Search
```
> python nrkdl.py -s "Lille jack"
4: Når lysene tennes...
3: Visittid
2: Frieren
1: På kino i kveld
0: Lille Jack

Pick a show or use slice notation
0


1 Lille Jack 27:52
0 Lille Jack 28:52

Pick a show or use slice notation
::
100%|####################################################################################| 2/2 [01:03<00:00, 43.64s/it]
```

## URL
```
> python nrkdl.py -u "http://tv.nrksuper.no/serie/bernt-og-erling-paa-nye-eventyr, http://tv.nrksuper.no/serie/bertine-paa-besoek"
100%|####################################################################################| 2/2 [00:21<00:00, 13.63s/it]
```

## Module
```
nrk = NRK()
s = nrk.search("lille jack", strict=True)
for e in s.episodes():
    e.download()

all_downloads = nrk.downloads()

# How many files are we gonna download
print(len(nrk.downloads()))
# Start downloading
all_downloads.start()
```
