import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

for path in sys.path:
    print(path)
from src.api import Nrk


@gogo
def test_search():
    sr = Nrk().search('skam')
