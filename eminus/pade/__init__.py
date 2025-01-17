#!/usr/bin/env python3
'''GTH pseudopotential files.

Reference: Phys. Rev. B 54, 1703.
'''

if __name__ == '__main__':
    import inspect
    import pathlib
    import shutil
    import urllib.request
    import zipfile

    psp_path = pathlib.Path(inspect.getfile(inspect.currentframe())).parent
    file = 'master.zip'
    # Download files
    url = f'https://github.com/cp2k/cp2k-data/archive/refs/heads/{file}'
    urllib.request.urlretrieve(url, file)
    # Unpack files
    with zipfile.ZipFile(file, 'r') as fzip:
        fzip.extractall()
    # Move files
    pade_path = psp_path.joinpath('cp2k-data-master/potentials/Goedecker/cp2k/pade')
    for f in pade_path.iterdir():
        shutil.move(f, psp_path.joinpath(f.name))
    # Cleanup
    psp_path.joinpath(file).unlink()
    shutil.rmtree('cp2k-data-master')
