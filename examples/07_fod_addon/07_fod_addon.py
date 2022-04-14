from eminus import Atoms, SCF, read_xyz, write_xyz, write_cube
from eminus.addons import get_fods, remove_core_fods, FLO
from eminus.localizer import get_FLOs
from eminus.scf import get_psi

# Start by with a calculation for methane
atoms = Atoms(*read_xyz('CH4.xyz'), center=True)
SCF(atoms)

# Calculate all FODs
fods_all = get_fods(atoms)
print(f'\nAll FODs:\n{fods_all}')

# Remove core FODs, since the calculation uses the GTH pseudopotential
fods = remove_core_fods(atoms, fods_all)
print(f'\nCore FODs:\n{fods}')

# The quality from the FOD guess can vary, but you can use these for as a solid guess
# import numpy as np
# fods = np.array([[10.71617803, 10.75510917, 10.73689087],
#                  [10.82635834,  9.25127336,  9.25068483],
#                  [ 9.24857483, 10.79169744,  9.24052496],
#                  [ 9.25441172,  9.25005662, 10.82402898]])

# Write the FODs to a xyz file to view them
write_xyz(atoms, 'CH4_fods.xyz', fods)

# Generate the Kohn-Sham orbitals
psi = get_psi(atoms, atoms.W)

# Calculate the FLOs
FLOs = get_FLOs(atoms, psi, fods)

# Write all FLOs to cube files
print('\nWrite cube files:')
for i in range(atoms.Ns):
    print(f'{i + 1} of {atoms.Ns}')
    write_cube(atoms, FLOs[:, i], f'CH4_FLO_{i + 1}.cube')

# All of the functionality above can be achieved with the following workflow function
# FLOs = FLO(atoms, write_cubes=True)
