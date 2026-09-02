"""ass_reader/__init__.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ass_reader.reader import ASSFileReader
from ass_reader.reader import *
from ass_reader.pysubs_utils import *
