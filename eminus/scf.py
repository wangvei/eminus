#!/usr/bin/env python3
'''SCF class definition.'''
import copy
import logging
import time

import numpy as np

from .dft import guess_gaussian, guess_pseudo, guess_random
from .energies import Energy, get_Eewald, get_Esic
from .gth import init_gth_loc, init_gth_nonloc
from .io import read_gth
from .logger import create_logger, get_level
from .minimizer import cg, lm, pccg, pclm, sd  # noqa: F401
from .potentials import init_pot
from .version import info
from .xc import XC_MAP


class SCF:
    '''Perform direct minimizations.

    Args:
        atoms: Atoms object.

    Keyword Args:
        xc (str): Comma-separated exchange-correlation functional description (case insensitive).

            Adding 'libxc:' before a functional will try to use the LibXC interface.

            Example: 'lda,pw'; 'lda,'; ',vwn'; ','; 'libxc:LDA_X,libxc:7',
            Default: 'lda,vwn'
        pot (str): Type of pseudopotential (case insensitive).

            Example: 'GTH'; 'harmonic'; 'Coulomb'; 'Ge',
            Default: 'gth'
        guess (str): Initial guess method for the basis functions (case insensitive).

            Example: 'Gauss'; 'gaussian'; 'random'; 'rand',
            Default: 'gaussian'
        etol (float): Convergence tolerance of the total energy.

            Default: 1e-7
        cgform (int): Conjugated-gradient form for the pccg minimization.

            1 for Fletcher-Reeves, 2 for Polak-Ribiere, and 3 for Hestenes-Stiefel.

            Default: 1
        min (dict | None): Dictionary to set the order and number of steps per minimization method.

            Example: {'sd': 10, 'pccg': 100}; {'pccg': 10, 'lm': 25, 'pclm': 50},
            Default: None (will default to {'pccg': 250})
        sic (bool): Calculate the Kohn-Sham Perdew-Zunger SIC energy at the end of the SCF step.

            Default: False
        verbose (int | str): Level of output (case insensitive).

            Can be one of 'CRITICAL', 'ERROR', 'WARNING', 'INFO', or 'DEBUG'.
            An integer value can be used as well, where larger numbers mean more output, starting
            from 0.

            Default: 'info'
    '''
    def __init__(self, atoms, xc='lda,vwn', pot='gth', guess='gaussian', etol=1e-7, cgform=1,
                 sic=False, min=None, verbose=None):
        self.atoms = copy.copy(atoms)  # Atoms object
        self.xc = xc.lower()           # Exchange-correlation functional
        self.pot = pot.lower()         # Used pseudopotential
        self.guess = guess             # Initial wave functions guess
        self.etol = etol               # Total energy convergence tolerance
        self.cgform = cgform           # Conjugate gradient form
        self.sic = sic                 # Calculate the sic energy
        self.min = min                 # Minimization methods

        # Set min here, better not use mutable data types in signatures
        if self.min is None:
            # For systems with bad convergence throw in some sd steps
            self.min = {'sd': 25, 'pccg': 250}

        # Initialize logger
        self.log = create_logger(self)
        if verbose is None:
            self.verbose = atoms.verbose
        else:
            self.verbose = verbose

        # Set up final and intermediate results
        self.W = None             # Basis functions
        self.n = None             # Electronic density
        self.energies = Energy()  # Energy object that holds energy contributions
        self.clear()

        # Parameters that will be built out of the inputs
        self.GTH = {}             # Dictionary of GTH parameters per atom species
        self.Vloc = None          # Local pseudopotential contribution
        self.NbetaNL = 0          # Number of projector functions for the non-local gth potential
        self.prj2beta = None      # Index matrix to map to the correct projector function
        self.betaNL = None        # Atomic-centered projector functions
        self.print_precision = 6  # Precision of the energy in the minimizer logger
        self.initialize()

    def clear(self):
        '''Initialize and clear intermediate results.'''
        self.Y = None       # Orthogonal wave functions
        self.n_spin = None  # Electronic densities per spin
        self.phi = None     # Hartree field
        self.exc = None     # Exchange-correlation energy density
        self.vxc = None     # Exchange-correlation potential
        return self

    def initialize(self):
        '''Validate inputs, update them and build all necessary parameters.'''
        if not self.atoms.is_built:
            self.atoms.build()
        self._set_potential()
        self._init_W()
        self.print_precision = int(abs(np.log10(self.etol))) + 1
        return self

    def run(self, **kwargs):
        '''Run the self-consistent field (SCF) calculation.'''
        if self.log.level <= logging.DEBUG:
            info()
        self.log.debug(f'--- System information ---\n{self.atoms}\n'
                       f'Spin handling: {"un" if self.atoms.Nspin == 1 else ""}polarized\n'
                       f'Number of states: {self.atoms.Nstate}\n'
                       f'Occupation per state:\n{self.atoms.f}\n'
                       f'\n--- Cell information ---\nSide lengths: {self.atoms.a} Bohr\n'
                       f'Sampling per axis: {self.atoms.s}\n'
                       f'Cut-off energy: {self.atoms.ecut} Hartree\n'
                       f'Compression: {len(self.atoms.G2) / len(self.atoms.G2c):.5f}\n'
                       f'\n--- Calculation information ---\n{self}\n\n--- SCF data ---')

        # Calculate Ewald energy that only depends on the system geometry
        self.energies.Eewald = get_Eewald(self.atoms)

        exch, corr = self.xc.split(',')
        try:
            if 'libxc' not in exch:
                XC_MAP[exch]
        except KeyError:
            self.log.warning('Use a mock functional for the exchange part.')
        try:
            if 'libxc' not in corr:
                XC_MAP[corr]
        except KeyError:
            self.log.warning('Use a mock functional for the correlation part.')

        # Start minimization procedures
        Etots = []
        minimizer_log = {}
        for imin in self.min:
            try:
                self.log.info(f'Start {eval(imin).__name__}...')
            except NameError:
                self.log.exception(f'No minimizer found for "{imin}"')
                raise
            start = time.perf_counter()
            Elist = eval(imin)(self, self.min[imin], **kwargs)  # Call minimizer
            end = time.perf_counter()
            minimizer_log[imin] = {}  # Create an entry for the current minimizer
            minimizer_log[imin]['time'] = end - start  # Save time in dictionary
            minimizer_log[imin]['iter'] = len(Elist)  # Save iterations in dictionary
            Etots += Elist  # Append energies from minimizer
            # Do not start other minimizations if one converged
            if len(Etots) > 1 and abs(Etots[-2] - Etots[-1]) < self.etol:
                break
        if len(Etots) > 1 and abs(Etots[-2] - Etots[-1]) < self.etol:
            self.log.info(f'SCF converged after {len(Etots)} iterations.')
        else:
            self.log.warning('SCF not converged!')

        # Print SCF data
        self.log.debug('\n--- SCF results ---')
        t_tot = 0
        for imin in minimizer_log:
            N = minimizer_log[imin]['iter']
            t = minimizer_log[imin]['time']
            t_tot += t
            self.log.debug(f'Minimizer: {imin}'
                           f'\nIterations:\t{N}'
                           f'\nTime:\t\t{t:.5f} s'
                           f'\nTime/Iteration:\t{t / N:.5f} s')
        self.log.info(f'Total SCF time: {t_tot:.5f} s')

        # Calculate SIC energy if desired
        if self.sic:
            self.energies.Esic = get_Esic(self, self.Y)

        # Print energy data
        if self.log.level <= logging.DEBUG:
            self.log.debug(f'\n--- Energy data ---\n{self.energies}')
        else:
            self.log.info(f'Total energy: {self.energies.Etot:.9f} Eh')
        return self.energies.Etot

    kernel = run

    def _set_potential(self):
        '''Build the potential.'''
        atoms = self.atoms
        if self.pot == 'gth':
            for ia in range(atoms.Natoms):
                self.GTH[atoms.atom[ia]] = read_gth(atoms.atom[ia], atoms.Z[ia])
            # Set up the local and non-local part
            self.Vloc = init_gth_loc(self)
            self.NbetaNL, self.prj2beta, self.betaNL = init_gth_nonloc(self)
        else:
            self.Vloc = init_pot(self)
        return

    def _init_W(self):
        '''Initialize wave functions.'''
        if self.guess in ('gauss', 'gaussian'):
            # Start with gaussians at atom positions
            self.W = guess_gaussian(self, complex=True)
        elif self.guess in ('rand', 'random'):
            # Start with randomized, complex basis functions with a random seed
            self.W = guess_random(self, complex=True)
        elif self.guess in ('pseudo'):
            # Start with pseudo-random numbers, mostly to compare with SimpleDFT
            self.W = guess_pseudo(self, seed=1234)
        else:
            self.log.error(f'No guess found for "{self.guess}"')
        return

    def __repr__(self):
        '''Print the parameters stored in the SCF object.'''
        return f'XC functionals: {self.xc}\n' \
               f'Potential: {self.pot}\n' \
               f'Starting guess: {self.guess}\n' \
               f'Convergence tolerance: {self.etol}\n' \
               f'Non-local contribution: {self.NbetaNL > 0}'

    @property
    def verbose(self):
        '''Verbosity level.'''
        return self._verbose

    @verbose.setter
    def verbose(self, level):
        '''Verbosity setter to sync the logger with the property.'''
        self._verbose = get_level(level)
        self.log.setLevel(self._verbose)
        return


class RSCF(SCF):
    '''SCF class for spin-paired systems. '''  # noqa: D210
    __doc__ += SCF.__doc__

    def initialize(self):
        '''Validate inputs, update them and build all necessary parameters.'''
        super().initialize()
        self.atoms._set_states(Nspin=1)
        return self


class USCF(SCF):
    '''SCF class for spin-polarized systems. '''  # noqa: D210
    __doc__ += SCF.__doc__

    def initialize(self):
        '''Validate inputs, update them and build all necessary parameters.'''
        super().initialize()
        self.atoms._set_states(Nspin=2)
        return self
