#!python.exe
# EASY-INSTALL-ENTRY-SCRIPT: 'Babel==0.9.6','console_scripts','pybabel'
__requires__ = 'Babel==0.9.6'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('Babel==0.9.6', 'console_scripts', 'pybabel')()
    )
