from simpalabos.fileio.common.proxy_lattice import ProxyLattice
from simphony.cuds.abc_lattice import ABCLattice
from simphony.cuds.primitive_cell import BravaisLattice
from simphony.cuds.abc_modeling_engine import ABCModelingEngine
from simpalabos.cuba_extension import CUBAExtension
from simphony.core.cuba import CUBA
import numpy as np
import subprocess
import os
import lxml.etree as et
import struct
import base64



class PalabosEngine(ABCModelingEngine):

    """File-IO wrapper for the Palabos Isothermal 3D flow modeling engine.

    Only a single lattice can be added for configuring the simulation;
    the wrapper does not accept meshes or particle containers.

    The following CUBA keywords are acknowledged in lattice node data:
    MATERIAL_ID

    Some values for the configuration parameters are enumerated:
    BGK for COLLISION_OPERATOR.

    Attributes
    ----------
    BC : dict
        container of attributes related to the boundary conditions.
    CM : dict
        container of attributes related to the computational method:
        collision operator, number of time steps, and time step.
    SP : dict
        container of attributes related to the system parameters/conditions:
        kinematic viscosity, pressure difference
    """

    BGK_ENUM = 0

    def __init__(self):
        """Initialize and set default parameters for CM, SP, and BC."""
        # Definition of CM, SP, and BC data components
        self._data = {}
        self._proxy_lattice = None
        self.CM = {}
        self.SP = {}
        self.BC = {}

        # Default Computational Method data
        self.CM[CUBAExtension.COLLISION_OPERATOR] = PalabosEngine.BGK_ENUM
        self.CM[CUBA.NUMBER_OF_TIME_STEPS] = 1000
        self.base_fname = 'palabos_engine'

        # Default System Parameters data
        self.SP[CUBA.PRESSURE] = 0.00001
        self.SP[CUBA.KINEMATIC_VISCOSITY] = 0.5

        # Default Boundary Condition data
        self.BC[CUBA.VELOCITY] = {'open': 'non-periodic',
                                  'wall': 'noSlip'}

        self.BC[CUBA.DENSITY] = {'open': 'non-periodic',
                                 'wall': 'noFlux'}

    def run(self):
        """Run the modeling engine using the configured settings.

        Raises
        ------
        RuntimeError
           if a lattice has not been added or
           if execution of the modeling engine fails.
        """
        if self._proxy_lattice is None:
            message = 'A lattice is not added before run in PalabosEngine'
            raise RuntimeError(message)

        # Define input/output file names
        input_script_fname = self.base_fname + '.xml'
        geom_write_fname = self.base_fname + '.geom.in.raw'
        den_read_fname = self.base_fname + '.den.out.vti'
        vel_read_fname = self.base_fname + '.vel.out.vti'

        # Write configuration data to files
        self._data[CUBA.MATERIAL_ID].tofile(geom_write_fname," ")
        self._write_input_script(input_script_fname)

        # Run the modeling engine
        run_command = 'mpirun -np 4 plb_pressure_diff.exe ' + input_script_fname

        p = subprocess.Popen(run_command, shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)

        output = p.communicate()
        print output[0]

        if p.returncode < 0:
            message = 'Execution of the Palabos engine failed'
            raise RuntimeError(message)

        den_data = self._data[CUBA.DENSITY]
        vel_data = self._data[CUBA.VELOCITY]

        # Copy data from the files into the given arrays
        den_data[:] = self._read_palabos_vtk_output(den_read_fname)
        vel_data[:] = self._read_palabos_vtk_output(vel_read_fname)

        # Clean up
        os.remove(input_script_fname)
        os.remove(geom_write_fname)
        os.remove(den_read_fname)
        os.remove(vel_read_fname)

    def add_dataset(self, container):
        """Add a CUDS Lattice container

        The following CUBA keywords are acknowledged in node data:
        MATERIAL_ID, DENSITY, VELOCITY, and FORCE.

        Parameters
        ----------
        container : {ABCLattice}
            The CUDS Lattice container to add to the engine.

        Raises
        ------
        TypeError:
            If the container type is not supported by the engine.
        ValueError:
            If there is already a dataset with the given name.
        ValueError:
            If the lattice type of the container is not cubic.

        """
        if not isinstance(container, ABCLattice):
            message = 'Only lattice containers are supported in PalabosEngine'
            raise TypeError(message)
        if bool(self._proxy_lattice):
            message = 'A lattice container already exists in PalabosEngine'
            raise ValueError(message)
        lat_type = container.primitive_cell.bravais_lattice
        if lat_type is not BravaisLattice.CUBIC:
            message = 'Lattice type is not cubic'
            raise ValueError(message)

        # Copy lattice attributes
        name = container.name
        pc = container.primitive_cell
        org = container.origin

        # Allocate arrays for lattice data
        geom = np.zeros(container.size, dtype=np.uint8)
        den = np.zeros(container.size, dtype=np.float64)
        vel = np.zeros(container.size+(3,), dtype=np.float64)

        self._data[CUBA.MATERIAL_ID] = geom
        self._data[CUBA.DENSITY] = den
        self._data[CUBA.VELOCITY] = vel

        # Create a proxy lattice
        self._proxy_lattice = ProxyLattice(name, pc, container.size,
                                           org, self._data)

        self._proxy_lattice.update_nodes(container.iter_nodes())

        self._proxy_lattice.data = container.data

    def remove_dataset(self, name):
        """Delete a lattice.

        Parameters
        ----------
        name : str
            name of the lattice to be deleted.

        Raises
        ------
        ValueError
            if name is not equal to the ProxyLattice name
            if no lattices are added in PalabosEngine

        """
        if self._proxy_lattice is not None:
            if self._proxy_lattice.name is not name:
                message = 'Container does not exist in PalabosEngine'
                raise ValueError(message)
            else:
                self._data = {}
                self._proxy_lattice._data = None
                self._proxy_lattice = None
        else:
            message = 'No lattices added in PalabosEngine'
            raise ValueError(message)

    def get_dataset(self, name):
        """ Get a lattice.

        The returned lattice can be used to query and update the state of the
        lattice inside the modeling engine.

        Parameters
        ----------
        name : str
            name of the lattice to be retrieved.

        Returns
        -------
        ABCLattice

        Raises
        ------
        ValueError
            if any one of the names is not equal to the ProxyLattice name
            if no lattices are added in PalabosEngine

        """
        if self._proxy_lattice is not None:
            if self._proxy_lattice.name is not name:
                message = 'Container does not exists in PalabosEngine'
                raise ValueError(message)
            else:
                return self._proxy_lattice
        else:
            message = 'No lattices added in PalabosEngine'
            raise ValueError(message)

    def get_dataset_names(self):
        """ Returns the names of the all the datasets in the engine workspace.

        """
        if self._proxy_lattice is not None:
            return [self._proxy_lattice.name]
        else:
            return []

    def iter_datasets(self, names=None):
        """Iterate over a subset or all of the lattices.

        Parameters
        ----------
        names : sequence of str, optional
            names of specific lattices to be iterated over. If names is not
            given, then all lattices will be iterated over.

        Returns
        -------
        A generator of ABCLattice objects

        Raises
        ------
        ValueError
            if any one of the names is not equal to the ProxyLattice name
            if no lattices are added in PalabosEngine
        """
        if self._proxy_lattice is not None:
            if names is None:
                yield self._proxy_lattice
            else:
                for name in names:
                    if self._proxy_lattice.name is not name:
                        message = 'State data does not contain requested item'
                        raise ValueError(message)
                    yield self._proxy_lattice
        else:
            message = 'No lattices added in PalabosEngine'
            raise ValueError(message)

    def _write_input_script(self, fname):
        """Write an input script xml file for the modeling engine.

        Parameters
        ----------
        fname : str
            name of the script file.
        """

        sp = et.Element("SimPhoNy-Palabos")
        geom = et.SubElement(sp, "geometry")

        et.SubElement(geom, "inputFile").text = self.base_fname+'.geom.in.raw'
        size = et.SubElement(geom, "size")
        et.SubElement(size, "nx").text = str(self._proxy_lattice.size[0])
        et.SubElement(size, "ny").text = str(self._proxy_lattice.size[1])
        et.SubElement(size, "nz").text = str(self._proxy_lattice.size[2])

        config = et.SubElement(sp, "configuration")
        et.SubElement(config, "pressureDifference").text = str(
            self.SP[CUBA.PRESSURE])
        et.SubElement(config, "kinematicViscosity").text = str(
            self.SP[CUBA.KINEMATIC_VISCOSITY])
        et.SubElement(config, "timeSteps").text = str(
            self.CM[CUBA.NUMBER_OF_TIME_STEPS])
        et.SubElement(config, "periodicity").text = str(
            self.BC[CUBA.VELOCITY]['open'])

        output = et.SubElement(sp, "output")
        et.SubElement(output, "velocity").text = self.base_fname+'.vel.out'
        et.SubElement(output, "density").text = self.base_fname+'.den.out'

        tree = et.ElementTree(sp)
        tree.write(fname, pretty_print=True)

    def _read_palabos_vtk_output(self, fname):
        """Read VTK based output file from the Palabos engine.

        Parameters
        ----------
        fname : str
            name of the file containing field data

        Returns
        -------
        numpy.ndarray
            Field data

        """
        p = et.XMLParser(huge_tree=True)
        vtkout = et.parse(fname, p)
        root = vtkout.getroot()

        image_data = root.find('.//ImageData')
        array_size = image_data.get('WholeExtent')
        dim = np.fromstring(array_size, dtype=int, sep=" ")
        dim += 1
        data_array = root.find('.//DataArray')

        num_comp = data_array.get('NumberOfComponents')
        if num_comp is None:
            array_shape = tuple(dim[1::2])
        else:
            array_shape = tuple(dim[1::2]) + (int(num_comp),)
        num_elem = np.prod(array_shape)
        b64data = base64.standard_b64decode(data_array.text[7:-1])
        fdata = struct.unpack('<{0}f'.format(num_elem), b64data)
        return np.asarray(fdata).reshape(array_shape)
