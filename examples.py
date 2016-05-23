from nrkdl import NRK


def example_search():
    nrk = NRK()
    search_results = nrk.search('Brannman Sam')
    for search in search_results:
        for season in search.seasons():
            for episode in season.episodes():
                episode.download()
                episode.subtitle()

    print('We found %s episodes to download' % len(nrk.downloads()))

def site_rip():
    """ Please, dont do this.. """
    nrk = NRK()

    all_programs = nrk.programs()
    print('We found %s' % len(all_programs))

    would_have_downloaded = 0
    for program in all_programs:
        if program.type == 'program':
            would_have_downloaded += 1
            #program.download()
        elif program.type == 'serie':
            would_have_downloaded += len(program.episodes())
            #for e in program.episodes():
            #    e.download()

    print('If we where to download everything we would download %s' % would_have_downloaded)

site_rip()
