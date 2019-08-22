#!/usr/bin/env python3

import os
import sys


thisfile = os.path.realpath(__file__)
thisdir = os.path.dirname(thisfile)
parent_dir = os.path.dirname(thisdir)
pdistcc_pkg = os.path.join(parent_dir, 'pdistcc', '__init__.py')
if os.path.exists(pdistcc_pkg):
    new_path = [parent_dir]
    new_path.extend([d for d in sys.path if d != thisdir])
    sys.path = new_path


if __name__ == '__main__':
    from pdistcc.cli import server_main as main
    main()
