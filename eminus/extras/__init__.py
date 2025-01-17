#!/usr/bin/env python3
'''Extra functions that need additional dependencies to work.

To also install all additional dependencies, use::

    pip install eminus[all]

Alternativle, you can only install selected extras using the respective name:

* :mod:`~eminus.extras.fods`
* :mod:`~eminus.extras.libxc`
* :mod:`~eminus.extras.viewer`
'''
from .fods import get_fods, remove_core_fods, split_fods
from .libxc import libxc_functional
from .viewer import view_grid, view_mol

__all__ = ['get_fods', 'libxc_functional', 'remove_core_fods', 'split_fods', 'view_grid',
           'view_mol']
