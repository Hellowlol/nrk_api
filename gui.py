import os
import sys
from gooey import Gooey, GooeyParser
from nrkdl import NRK


nonbuffered_stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
sys.stdout = nonbuffered_stdout


"""
See https://github.com/chriskiehl/Gooey#installation-instructions
This gui does only work with py2

"""


@Gooey(monospace_display=True,
       advanced=True,
       default_size=(900, 600),
       program_description='Download tvshows/movies from NRK/Super')
def main():

    NRK = NRK(gui=True)

    parser = GooeyParser()

    parser.add_argument('-u', '--url', action='store', default=False,
                        required=False, widget='TextField', help='"url1 url2 url3"')

    parser.add_argument('-e', '--encoding', default='latin-1',
                        required=False, help='Set encoding')

    parser.add_argument('-save', '--save_path', default=False,
                        required=False, help='Download to this folder', widget='DirChooser')

    parser.add_argument('-dr', '--dry_run', action='store_true', default=False,
                        required=False, help='Dry run, dont download anything')

    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        required=False, help='Show ffmpeg output')

    parser.add_argument('-w', '--workers', default=2,
                        required=False, help='Number of thread pool workers')

    parser.add_argument('-st', '--subtitle', action='store_true', default=False,
                        required=False, help='Download subtitle for this media file?')

    parser.add_argument('-if', '--input_file', default=False,
                        required=False, help='List of files to download', widget='FileChooser')

    p = parser.parse_args()

    NRK.dry_run = p.dry_run
    NRK.verbose = p.verbose
    NRK.subtitle = p.subtitle

    NRK.cli = False
    NRK.encoding = p.encoding
    NRK.workers = int(p.workers)

    if p.save_path:
        NRK.SAVE_PATH = p.save_path

    if p.input_file:
        NRK._from_file(p.input_file)

    if p.url:
        NRK.parse_url(p.url)

main()
