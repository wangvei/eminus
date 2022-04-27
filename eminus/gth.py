#!/usr/bin/env python3
'''Utilities to use Goedecker, Teter, and Hutter (GTH) pseudopotentials.

Reference: Phys. Rev. B 54, 1703.
'''
from glob import glob
from os.path import basename

import numpy as np

from . import __path__
from .logger import log
from .utils import Ylm_real


def init_gth_loc(atoms):
    '''Initialize parameters to calculate local contributions of GTH pseudopotentials.

    Reference: Phys. Rev. B 54, 1703.

    Args:
        atoms: Atoms object.

    Returns:
        ndarray: Local GTH potential contribution.
    '''
    G2 = atoms.G2
    atom = atoms.atom
    species = set(atom)
    omega = 1  # Normally this would be det(atoms.R), but Arias notation is off by this factor

    Vloc = np.zeros(len(G2))
    for isp in species:
        psp = atoms.GTH[isp]
        rloc = psp['rloc']
        Zion = psp['Zion']
        c1 = psp['cloc'][0]
        c2 = psp['cloc'][1]
        c3 = psp['cloc'][2]
        c4 = psp['cloc'][3]

        rlocG2 = G2 * rloc**2
        # Ignore the division by zero for the first elements
        # One could do some proper indexing with [1:] but indexing is slow
        with np.errstate(divide='ignore', invalid='ignore'):
            Vsp = -4 * np.pi * Zion / omega * np.exp(-0.5 * rlocG2) / G2 + \
                  np.sqrt((2 * np.pi)**3) * rloc**3 / omega * np.exp(-0.5 * rlocG2) * \
                  (c1 + c2 * (3 - rlocG2) + c3 * (15 - 10 * rlocG2 + rlocG2**2) +
                  c4 * (105 - 105 * rlocG2 + 21 * rlocG2**2 - rlocG2**3))
        # Special case for G=(0,0,0), same as in QE
        Vsp[0] = 2 * np.pi * Zion * rloc**2 + \
                 (2 * np.pi)**1.5 * rloc**3 * (c1 + 3 * c2 + 15 * c3 + 105 * c4)

        # Sum up the structure factor for every species
        Sf = np.zeros(len(atoms.Sf[0]), dtype=complex)
        for ia in range(len(atom)):
            if atom[ia] == isp:
                Sf += atoms.Sf[ia]
        Vloc += np.real(atoms.J(Vsp * Sf))
    return Vloc


# Adapted from https://github.com/f-fathurrahman/PWDFT.jl/blob/master/src/PsPotNL.jl
def init_gth_nonloc(atoms):
    '''Initialize parameters to calculate non-local contributions of GTH pseudopotentials.

    Reference: Phys. Rev. B 54, 1703.

    Args:
        atoms: Atoms object.

    Returns:
        tuple[int, ndarray, ndarray]: NbetaNL, prj2beta, and betaNL.
    '''
    Natoms = atoms.Natoms
    Npoints = len(atoms.G2c)
    Omega = atoms.Omega

    prj2beta = np.zeros([3, Natoms, 4, 7], dtype=int)
    prj2beta[:] = -1  # Set to an invalid index

    NbetaNL = 0
    for ia in range(Natoms):
        psp = atoms.GTH[atoms.atom[ia]]
        for l in range(psp['lmax']):
            for m in range(-l, l + 1):
                for iprj in range(psp['Nproj_l'][l]):
                    NbetaNL += 1
                    prj2beta[iprj, ia, l, m + psp['lmax'] - 1] = NbetaNL

    g = atoms.G[atoms.active]  # Simplified, would normally be G+k
    Gm = np.sqrt(atoms.G2c)

    ibeta = 0
    betaNL = np.zeros([Npoints, NbetaNL], dtype=complex)
    for ia in range(Natoms):
        # It is very important to transform the structure factor to make both notations compatible
        Sf = atoms.Idag(atoms.J(atoms.Sf[ia]))
        psp = atoms.GTH[atoms.atom[ia]]
        for l in range(psp['lmax']):
            for m in range(-l, l + 1):
                for iprj in range(psp['Nproj_l'][l]):
                    betaNL[:, ibeta] = (-1j)**l * Ylm_real(l, m, g) * \
                                       eval_proj_G(psp, l, iprj + 1, Gm, Omega) * Sf
                    ibeta += 1
    return NbetaNL, prj2beta, betaNL


# Adapted from https://github.com/f-fathurrahman/PWDFT.jl/blob/master/src/op_V_Ps_nloc.jl
def calc_Vnonloc(atoms, W):
    '''Calculate the non-local pseudopotential, applied on the basis functions W.

    Reference: Phys. Rev. B 54, 1703.

    Args:
        atoms: Atoms object.
        W (ndarray): Expansion coefficients of unconstrained wave functions in reciprocal space.

    Returns:
        ndarray: Non-local GTH potential contribution.
    '''
    Npoints = len(W)
    Nstates = atoms.Ns

    Vpsi = np.zeros([Npoints, Nstates], dtype=complex)
    if atoms.NbetaNL > 0:  # Only calculate non-local potential if necessary
        Natoms = atoms.Natoms
        prj2beta = atoms.prj2beta
        betaNL = atoms.betaNL

        betaNL_psi = (W.conj().T @ betaNL).conj()

        for ist in range(Nstates):
            for ia in range(Natoms):
                psp = atoms.GTH[atoms.atom[ia]]
                for l in range(psp['lmax']):
                    for m in range(-l, l + 1):
                        for iprj in range(psp['Nproj_l'][l]):
                            ibeta = prj2beta[iprj, ia, l, m + psp['lmax'] - 1] - 1
                            for jprj in range(psp['Nproj_l'][l]):
                                jbeta = prj2beta[jprj, ia, l, m + psp['lmax'] - 1] - 1
                                hij = psp['h'][l, iprj, jprj]
                                Vpsi[:, ist] += hij * betaNL[:, ibeta] * betaNL_psi[ist, jbeta]
    # We have to multiply with the cell volume, because of different orthogonalization methods
    return Vpsi * atoms.Omega


# Adapted from https://github.com/f-fathurrahman/PWDFT.jl/blob/master/src/PsPot_GTH.jl
def eval_proj_G(psp, l, iprj, Gm, Omega):
    '''Evaluate GTH projector functions in G-space.

    Reference: Phys. Rev. B 54, 1703.

    Args:
        psp (dict): GTH parameters.
        l (int): Angular momentum number.
        iprj (int): Nproj_l index.
        Gm (ndarray): Magnitude of G-vectors.
        Omega (float): Unit cell volume.

    Returns:
        ndarray: GTH projector.
    '''
    rrl = psp['rp'][l]
    Gr2 = (Gm * rrl)**2

    if l == 0:  # s-channel
        if iprj == 1:
            Vprj = np.exp(-0.5 * Gr2)
        elif iprj == 2:
            Vprj = 2 / np.sqrt(15) * np.exp(-0.5 * Gr2) * (3 - Gr2)
        elif iprj == 3:
            Vprj = (4 / 3) / np.sqrt(105) * np.exp(-0.5 * Gr2) * (15 - 10 * Gr2 + Gr2**2)
    elif l == 1:  # p-channel
        if iprj == 1:
            Vprj = (1 / np.sqrt(3)) * np.exp(-0.5 * Gr2) * Gm
        elif iprj == 2:
            Vprj = (2 / np.sqrt(105)) * np.exp(-0.5 * Gr2) * Gm * (5 - Gr2)
        elif iprj == 3:
            Vprj = (4 / 3) / np.sqrt(1155) * np.exp(-0.5 * Gr2) * Gm * (35 - 14 * Gr2 + Gr2**2)
    elif l == 2:  # d-channel
        if iprj == 1:
            Vprj = (1 / np.sqrt(15)) * np.exp(-0.5 * Gr2) * Gm**2
        elif iprj == 2:
            Vprj = (2 / 3) / np.sqrt(105) * np.exp(-0.5 * Gr2) * Gm**2 * (7 - Gr2)
    elif l == 3:  # f-channel
        # Only one projector
        Vprj = Gm**3 * np.exp(-0.5 * Gr2) / np.sqrt(105)
    else:
        log.error(f'No projector found for l={l}')

    pre = 4 * np.pi**(5 / 4) * np.sqrt(2**(l + 1) * rrl**(2 * l + 3) / Omega)
    return pre * Vprj


def read_gth(system, charge=None, psp_path=None):
    '''Read GTH files for a given system.

    Args:
        system (str): Atom name.

    Keyword Args:
        charge (int): Valence charge.
        psp_path (str): Path to GTH pseudopotential files. Defaults to installation_path/pade_gth/.

    Returns:
        dict: GTH parameters.
    '''
    if psp_path is None:
        psp_path = f'{__path__[0]}/pade_gth/'

    if charge is not None:
        f_psp = f'{psp_path}{system}-q{charge}.gth'
    else:
        files = glob(f'{psp_path}{system}-q*')
        files.sort()
        try:
            f_psp = files[0]
        except IndexError:
            log.exception(f'There is no GTH pseudopotential in {psp_path} for "{system}"')
        if len(files) > 1:
            log.info(f'Multiple pseudopotentials found for "{system}". '
                     f'Continue with "{basename(f_psp)}".')

    psp = {}
    cloc = np.zeros(4)
    rp = np.zeros(4)
    Nproj_l = np.zeros(4, dtype=int)
    h = np.zeros([4, 3, 3])
    try:
        with open(f_psp, 'r') as fh:
            # Skip the first line, since we don't need the atom symbol here. If needed, use
            # psp['atom'] = fh.readline().split()[0]  # Atom symbol
            fh.readline()
            N_all = fh.readline().split()
            N_s, N_p, N_d, N_f = int(N_all[0]), int(N_all[1]), int(N_all[2]), int(N_all[3])
            psp['Zion'] = N_s + N_p + N_d + N_f  # Ionic charge
            # Skip the number of local coefficients, since we don't need it. If needed, use
            # rloc, n_c_local = fh.readline().split()
            # psp['n_c_local'] = int(n_c_local)  # Number of local coefficients
            rloc = fh.readline().split()[0]
            psp['rloc'] = float(rloc)  # Range of local Gaussian charge distribution
            for i, val in enumerate(fh.readline().split()):
                cloc[i] = float(val)
            psp['cloc'] = cloc  # Coefficients for the local part
            lmax = int(fh.readline().split()[0])
            psp['lmax'] = lmax  # Maximal angular momentum in the non-local part
            for iiter in range(lmax):
                rp[iiter], Nproj_l[iiter] = [float(i) for i in fh.readline().split()]
                for jiter in range(Nproj_l[iiter]):
                    tmp = fh.readline().split()
                    for iread, kiter in enumerate(range(jiter, Nproj_l[iiter])):
                        h[iiter, jiter, kiter] = float(tmp[iread])
            psp['rp'] = rp  # Projector radius for each angular momentum
            psp['Nproj_l'] = Nproj_l  # Number of non-local projectors
            for k in range(3):
                for i in range(2):
                    for j in range(i + 1, 2):
                        h[k, j, i] = h[k, i, j]
            psp['h'] = h  # Projector coupling coefficients per AM channel
    except FileNotFoundError:
        log.exception(f'There is no GTH pseudopotential for "{basename(f_psp)}"')
    return psp
