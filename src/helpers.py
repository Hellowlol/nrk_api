# helpers

import re

def clean_name(s):
    """ remove all illegal chars for ffmpeg"""
    s = re.sub(r'[-/\\\?%\*|"<>]', '', s).replace(':', '_')
    s = ' '.join(s.split()).strip()
    return s


def console_select(something):
    pass
