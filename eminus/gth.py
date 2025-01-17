#!/usr/bin/env python3
'''Utilities to use Goedecker, Teter, and Hutter (GTH) pseudopotentials.'''
import numpy as np

from .logger import log
from .utils import Ylm_real


def init_gth_loc(scf):
    '''Initialize parameters to calculate local contributions of GTH pseudopotentials.

    Reference: Phys. Rev. B 54, 1703.

    Args:
        scf: SCF object.

    Returns:
        ndarray: Local GTH potential contribution.
    '''
    atoms = scf.atoms
    species = set(atoms.atom)
    omega = 1  # Normally this would be det(atoms.R), but Arias notation is off by this factor

    Vloc = np.zeros_like(atoms.G2)
    for isp in species:
        psp = scf.GTH[isp]
        rloc = psp['rloc']
        Zion = psp['Zion']
        c1 = psp['cloc'][0]
        c2 = psp['cloc'][1]
        c3 = psp['cloc'][2]
        c4 = psp['cloc'][3]

        rlocG2 = atoms.G2 * rloc**2
        # Ignore the division by zero for the first elements
        # One could do some proper indexing with [1:] but indexing is slow
        with np.errstate(divide='ignore', invalid='ignore'):
            Vsp = -4 * np.pi * Zion / omega * np.exp(-0.5 * rlocG2) / atoms.G2 + \
                np.sqrt((2 * np.pi)**3) * rloc**3 / omega * np.exp(-0.5 * rlocG2) * \
                (c1 + c2 * (3 - rlocG2) + c3 * (15 - 10 * rlocG2 + rlocG2**2) +
                 c4 * (105 - 105 * rlocG2 + 21 * rlocG2**2 - rlocG2**3))
        # Special case for G=(0,0,0), same as in QE
        Vsp[0] = 2 * np.pi * Zion * rloc**2 + \
            (2 * np.pi)**1.5 * rloc**3 * (c1 + 3 * c2 + 15 * c3 + 105 * c4)

        # Sum up the structure factor for every species
        Sf = np.zeros(len(atoms.Sf[0]), dtype=complex)
        for ia in range(len(atoms.atom)):
            if atoms.atom[ia] == isp:
                Sf += atoms.Sf[ia]
        Vloc += np.real(atoms.J(Vsp * Sf))
    return Vloc


# Adapted from https://github.com/f-fathurrahman/PWDFT.jl/blob/master/src/PsPotNL.jl
def init_gth_nonloc(scf):
    '''Initialize parameters to calculate non-local contributions of GTH pseudopotentials.

    Reference: Phys. Rev. B 54, 1703.

    Args:
        scf: SCF object.

    Returns:
        tuple[int, ndarray, ndarray]: NbetaNL, prj2beta, and betaNL.
    '''
    atoms = scf.atoms
    prj2beta = np.zeros((3, atoms.Natoms, 4, 7), dtype=int)
    prj2beta += -1  # Set to an invalid index

    NbetaNL = 0
    for ia in range(atoms.Natoms):
        psp = scf.GTH[atoms.atom[ia]]
        for l in range(psp['lmax']):
            for m in range(-l, l + 1):
                for iprj in range(psp['Nproj_l'][l]):
                    NbetaNL += 1
                    prj2beta[iprj, ia, l, m + psp['lmax'] - 1] = NbetaNL

    g = atoms.G[atoms.active]  # Simplified, would normally be G+k
    Gm = np.sqrt(atoms.G2c)

    ibeta = 0
    betaNL = np.empty((len(atoms.G2c), NbetaNL), dtype=complex)
    for ia in range(atoms.Natoms):
        # It is very important to transform the structure factor to make both notations compatible
        Sf = atoms.Idag(atoms.J(atoms.Sf[ia]))
        psp = scf.GTH[atoms.atom[ia]]
        for l in range(psp['lmax']):
            for m in range(-l, l + 1):
                for iprj in range(psp['Nproj_l'][l]):
                    betaNL[:, ibeta] = (-1j)**l * Ylm_real(l, m, g) * \
                        eval_proj_G(psp, l, iprj + 1, Gm, atoms.Omega) * Sf
                    ibeta += 1
    return NbetaNL, prj2beta, betaNL


# Adapted from https://github.com/f-fathurrahman/PWDFT.jl/blob/master/src/op_V_Ps_nloc.jl
def calc_Vnonloc(scf, W):
    '''Calculate the non-local pseudopotential, applied on the basis functions W.

    Reference: Phys. Rev. B 54, 1703.

    Args:
        scf: SCF object.
        W (ndarray): Expansion coefficients of unconstrained wave functions in reciprocal space.

    Returns:
        ndarray: Non-local GTH potential contribution.
    '''
    atoms = scf.atoms

    Vpsi = np.zeros_like(W, dtype=complex)
    if scf.NbetaNL > 0:  # Only calculate non-local potential if necessary
        betaNL_psi = (W.conj().T @ scf.betaNL).conj()

        for ia in range(atoms.Natoms):
            psp = scf.GTH[atoms.atom[ia]]
            for l in range(psp['lmax']):
                for m in range(-l, l + 1):
                    for iprj in range(psp['Nproj_l'][l]):
                        ibeta = scf.prj2beta[iprj, ia, l, m + psp['lmax'] - 1] - 1
                        for jprj in range(psp['Nproj_l'][l]):
                            jbeta = scf.prj2beta[jprj, ia, l, m + psp['lmax'] - 1] - 1
                            hij = psp['h'][l, iprj, jprj]
                            Vpsi += hij * betaNL_psi[:, jbeta] * scf.betaNL[:, ibeta][:, None]
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

    prefactor = 4 * np.pi**(5 / 4) * np.sqrt(2**(l + 1) * rrl**(2 * l + 3) / Omega)
    Vprj = prefactor * np.exp(-0.5 * Gr2)

    if l == 0:  # s-channel
        if iprj == 1:
            return Vprj
        elif iprj == 2:
            return 2 / np.sqrt(15) * (3 - Gr2) * Vprj
        elif iprj == 3:
            return (4 / 3) / np.sqrt(105) * (15 - 10 * Gr2 + Gr2**2) * Vprj
    elif l == 1:  # p-channel
        if iprj == 1:
            return 1 / np.sqrt(3) * Gm * Vprj
        elif iprj == 2:
            return 2 / np.sqrt(105) * Gm * (5 - Gr2) * Vprj
        elif iprj == 3:
            return (4 / 3) / np.sqrt(1155) * Gm * (35 - 14 * Gr2 + Gr2**2) * Vprj
    elif l == 2:  # d-channel
        if iprj == 1:
            return 1 / np.sqrt(15) * Gm**2 * Vprj
        elif iprj == 2:
            return (2 / 3) / np.sqrt(105) * Gm**2 * (7 - Gr2) * Vprj
    elif l == 3:  # f-channel
        # Only one projector
        return 1 / np.sqrt(105) * Gm**3 * Vprj

    log.error(f'No projector found for l={l}')
    return
