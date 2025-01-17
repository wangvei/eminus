#!/usr/bin/env python3
'''Collection of constants and unit conversion functions.

For more about atomic units, see: https://en.wikipedia.org/wiki/Hartree_atomic_units
'''
# Ha in eV (https://en.wikipedia.org/wiki/Hartree)
electronvolt = eV = 27.211386245988
# Ha in kcal/mol (https://en.wikipedia.org/wiki/Hartree)
kcalmol = 627.5094740631
# a0 in Å (https://en.wikipedia.org/wiki/Bohr_radius)
Angstrom = A = 0.529177210903
# e * a0 in D (https://en.wikipedia.org/wiki/Hartree_atomic_units)
Debye = D = 2.541746473


def ha2ev(E):
    '''Convert Hartree to electronvolt.

    Args:
        E (float | ndarray): Energy in Hartree.

    Returns:
        float | ndarray: Energy in electronvolt.
    '''
    return E * electronvolt


def ev2ha(E):
    '''Convert electronvolt to Hartree.

    Args:
        E (float | ndarray): Energy in electronvolt.

    Returns:
        float | ndarray: Energy in Hartree.
    '''
    return E / electronvolt


def ha2kcalmol(E):
    '''Convert Hartree to kcal/mol.

    Args:
        E (float | ndarray): Energy in Hartree.

    Returns:
        float | ndarray: Energy in kcal/mol.
    '''
    return E * kcalmol


def kcalmol2ha(E):
    '''Convert kcal/mol to Hartree.

    Args:
        E (float | ndarray): Energy in kcal/mol.

    Returns:
        float | ndarray: Energy in Hartree.
    '''
    return E / kcalmol


def ev2kcalmol(E):
    '''Convert electronvolt to kcal/mol.

    Args:
        E (float | ndarray): Energy in electronvolt.

    Returns:
        float | ndarray: Energy in kcal/mol.
    '''
    return ha2kcalmol(ev2ha(E))


def kcalmol2ev(E):
    '''Convert kcal/mol to electronvolt.

    Args:
        E (float | ndarray): Energy in kcal/mol.

    Returns:
        float | ndarray: Energy in electronvolt.
    '''
    return ha2ev(kcalmol2ha(E))


def ha2ry(E):
    '''Convert Hartree to Rydberg.

    Args:
        E (float | ndarray): Energy in Hartree.

    Returns:
        float | ndarray: Energy in Rydberg.
    '''
    return 2 * E


def ry2ha(E):
    '''Convert Rydberg to Hartree.

    Args:
        E (float | ndarray): Energy in Rydberg.

    Returns:
        float | ndarray: Energy in Hartree.
    '''
    return E / 2


def ang2bohr(r):
    '''Convert Angstrom to Bohr.

    Args:
        r (float | ndarray): Length in Angstrom.

    Returns:
        float | ndarray: Length in Bohr.
    '''
    return r / Angstrom


def bohr2ang(r):
    '''Convert Bohr to Angstrom.

    Args:
        r (float | ndarray): Length in Bohr.

    Returns:
        float | ndarray: Length in Angstrom.
    '''
    return r * Angstrom


def ebohr2d(p):
    '''Convert e * Bohr to Debye.

    Args:
        p (float | ndarray): Electric dipole moment in e * Bohr.

    Returns:
        float | ndarray: Electric dipole moment in Debye.
    '''
    return p * Debye


def d2ebohr(p):
    '''Convert Debye to e * Bohr.

    Args:
        p (float | ndarray): Electric dipole moment in Debye.

    Returns:
        float | ndarray: Electric dipole moment in e * Bohr.
    '''
    return p / Debye
