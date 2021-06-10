#!/usr/bin/env python3
'''
Calculate the non-local potential with GTH pseudopotentials. Phys. Rev. B 54, 1703
'''
import numpy as np
from .utils import Ylm_real


# Adopted from https://github.com/f-fathurrahman/PWDFT.jl/blob/master/src/op_V_Ps_nloc.jl
def calc_Vnonloc(atoms, W):
    '''Calculate the non-local pseudopotential, applied on the basis functions W.'''
    Npoints = len(W)
    Nstates = atoms.Ns
    Vpsi = np.zeros([Npoints, Nstates], dtype=complex)
    if atoms.NbetaNL > 0:  # Only calculate non-local potential if necessary
        # Parameters of the non-local pseudopotential
        prj2beta = atoms.prj2beta
        betaNL = atoms.betaNL

        Natoms = len(atoms.X)

        betaNL_psi = np.dot(W.T.conj(), betaNL).conj()

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
        # We have to multiply with the cell volume, because of different orthogonalization
    return Vpsi * atoms.CellVol


# Adopted from https://github.com/f-fathurrahman/PWDFT.jl/blob/master/src/PsPotNL.jl
def init_gth_nonloc(atoms):
    '''Initialize parameters to calculate non-local contributions.'''
    Natoms = len(atoms.X)
    Npoints = len(atoms.active[0])
    CellVol = atoms.CellVol

    prj2beta = np.zeros([3, Natoms, 4, 7], dtype=int)
    prj2beta[:] = -1  # Set to invalid index

    NbetaNL = 0
    for ia in range(Natoms):
        psp = atoms.GTH[atoms.atom[ia]]
        for l in range(psp['lmax']):
            for m in range(-l, l + 1):
                for iprj in range(psp['Nproj_l'][l]):
                    NbetaNL += 1
                    prj2beta[iprj, ia, l, m + psp['lmax'] - 1] = NbetaNL

    # TODO: remove me
    # Sort G-vectors by their magnitude
    # PWDFT.jl uses sortperm, for compareabilty we need to sort with mergesort
    # idx = np.argsort(atoms.G2c, kind='mergesort')
    # g = atoms.Gc[idx]
    # Gm = np.sqrt(atoms.G2c[idx])
    g = atoms.Gc  # Simplified, would normally be G+k
    Gm = np.sqrt(atoms.G2c)

    ibeta = 0
    betaNL = np.zeros([Npoints, NbetaNL], dtype=complex)
    for ia in range(Natoms):
        Sf = atoms.Idag(atoms.J(atoms.Sf[ia]))
        psp = atoms.GTH[atoms.atom[ia]]
        for l in range(psp['lmax']):
            for m in range(-l, l + 1):
                for iprj in range(psp['Nproj_l'][l]):
                    betaNL[:, ibeta] = (-1j)**l * Ylm_real(l, m, g) * \
                                       eval_proj_G(psp, l, iprj + 1, Gm, CellVol) * Sf
                    ibeta += 1
    if atoms.verbose > 5:
        for ibeta in range(NbetaNL):
            norm = betaNL[:, ibeta].conj() @ betaNL[:, ibeta]
            print(f'Norm of betaNL(ibeta={ibeta}): {norm}')
    return NbetaNL, prj2beta, betaNL


# Adopted from https://github.com/f-fathurrahman/PWDFT.jl/blob/master/src/PsPot_GTH.jl
def eval_proj_G(psp, l, iproj, Gm, CellVol):
    '''Evaluate GTH projector function in G-space.'''
    rrl = psp['rc'][l]
    Gr2 = (Gm * rrl)**2

    if l == 0:  # s-channel
        if iproj == 1:
            Vprj = np.exp(-0.5 * Gr2)
        elif iproj == 2:
            Vprj = 2 / np.sqrt(15) * np.exp(-0.5 * Gr2) * (3 - Gr2)
        elif iproj == 3:
            Vprj = (4 / 3) / np.sqrt(105) * np.exp(-0.5 * Gr2) * (15 - 10 * Gr2 + Gr2**2)
    elif l == 1:  # p-channel
        if iproj == 1:
            Vprj = (1 / np.sqrt(3)) * np.exp(-0.5 * Gr2) * Gm
        elif iproj == 2:
            Vprj = (2 / np.sqrt(105)) * np.exp(-0.5 * Gr2) * Gm * (5 - Gr2)
        elif iproj == 3:
            Vprj = (4 / 3) / np.sqrt(1155) * np.exp(-0.5 * Gr2) * Gm * (35 - 14 * Gr2 + Gr2**2)
    elif l == 2:  # d-channel
        if iproj == 1:
            Vprj = (1 / np.sqrt(15)) * np.exp(-0.5 * Gr2) * Gm**2
        elif iproj == 2:
            Vprj = (2 / 3) / np.sqrt(105) * np.exp(-0.5 * Gr2) * Gm**2 * (7 - Gr2)
    elif l == 3:  # f-channel
        # Only one projector
        Vprj = Gm**3 * np.exp(-0.5 * Gr2) / np.sqrt(105)
    else:
        print(f'ERROR: No projector found for l={l}')

    pre = 4 * np.pi**(5 / 4) * np.sqrt(2**(l + 1) * rrl**(2 * l + 3) / CellVol)
    return pre * Vprj
