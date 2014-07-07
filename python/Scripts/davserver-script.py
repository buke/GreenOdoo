#!C:\Python27\python.exe
# EASY-INSTALL-ENTRY-SCRIPT: 'PyWebDAV==0.9.8','console_scripts','davserver'
__requires__ = 'PyWebDAV==0.9.8'
import sys
from pkg_resources import load_entry_point

sys.exit(
   load_entry_point('PyWebDAV==0.9.8', 'console_scripts', 'davserver')()
)
