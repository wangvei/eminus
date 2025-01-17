from eminus import Atoms

# # The only necessary parameters are `atom` and `X`
# # `atom` holds the atom symbols, and `X` holds the atom positions
# # Please note that atomic units will be used
atom = 'N2'
X = [[0, 0, 0], [2.074, 0, 0]]

# # Create an object for dinitrogen and display it
atoms = Atoms(atom, X)
print(f'Atoms object:\n{atoms}\n')

# # Optional parameters with examples are listed as follows
# # Cell size or vacuum size
a = 20

# # Cut-off energy
ecut = 20

# # Valence charge per atom, the charges should not differ for the same species
# # `None` will use valence charges from GTH pseudopotentials
Z = [5, 5]

# # Real-space sampling of the cell using an equidistant grid
s = 40

# # Number of spin channels
Nspin = 1

# # Occupation numbers per state
# # `None` will assume occupations of 2
# # The last state will be adjusted if the sum of `f` is not equal to the sum of `Z`
f = [2, 2, 2, 2, 2]

# # Number of states
# # `None` will get the number of states from `f` or assume occupations of 2
Nstate = 5

# # Center the system inside the box by its geometric center of mass and rotate it such that its geometric moment of inertia aligns with the coordinate axes
center = True

# # Level of output, larger numbers mean more output
verbose = 4

# # Create an `Atoms` object for dinitrogen and display it
atoms = Atoms(atom=atom, X=X, a=a, ecut=ecut, Z=Z, s=s, center=center, Nspin=Nspin, f=f,
              Nstate=Nstate, verbose=verbose)
print(f'New Atoms object:\n{atoms}\n')

# # You can always manipulate the object freely by displaying or editing properties
# # To display the calculated cell volume
print(f'Cell volume = {atoms.Omega} a0^3')

# # If you edit properties of an existing object dependent properties can be updated by rebuilding the `Atoms` object
# # The `atoms.build` function is used to generate cell parameters for an SCF calculation, but an SCF object will call the function if necessary
# # Edit the cell size, rebuild the object, and display the new cell volume
atoms.a = 3
atoms.build()
print(f'New cell volume = {atoms.Omega} a0^3')

# # More information are always available in the respective docstring
# print(f'\nAtoms docstring:\n{Atoms.__doc__}')
# # or:
# help(Atoms)
