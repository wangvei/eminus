#!/usr/bin/env python3
'''
Package version number and version info function.
'''
from sys import version

__version__ = '1.0.1'
dependencies = ('numpy', 'scipy')
addons = ('notebook', 'vispy', 'nglview', 'jupyter_rfb', 'pyflosic_dev')


def info():
    '''Print version numbers and availability of used packages.'''
    print('--- Version infos ---')
    print(f'python       : {version.split()[0]}')
    print(f'eminus       : {__version__}')
    for pkg in dependencies + addons:
        try:
            exec(f'import {pkg}')
            print(f'{pkg.ljust(13)}: {eval(pkg).__version__}')
        except ModuleNotFoundError:
            if pkg in dependencies:
                print(f'{pkg.ljust(13)}: Dependency not installed')
            elif pkg in addons:
                print(f'{pkg.ljust(13)}: Addon not installed')
    return
