import math
from simphony.core.cuba import CUBA
from simpalabos.cuba_extension import CUBAExtension
from simphony.cuds.abc_lattice import ABCLattice
from simphony.cuds.lattice import make_cubic_lattice
from simphony.testing.abc_check_engine import LatticeEngineCheck


class PalabosEngineCheck(LatticeEngineCheck):

    """ Common parameters for Palabos engine test cases """

    def _setup_test_problem(self, engine):
        """ Set up parameters for Poiseuille flow problem

        """
        self.test_lattice_name = "lattice1"
        self.nx = 5
        self.ny = 3
        self.nz = 4
        self.dr = 1.0
        self.dt = 1.0
        self.tsteps = 1000

        self.gx = 0.0
        self.gy = 0.0
        self.gz = 1.0e-5
        self.kvisc = 0.1
        self.rden = 1.0

        self.ext_frc = False

        self.channel_h = 0.5*(self.nx-2.0)
        self.max_vel = 0.5*self.gz*self.channel_h*self.channel_h/self.kvisc

        # Computational Method data
        engine.CM[CUBAExtension.COLLISION_OPERATOR] = self.coll_oper
        engine.CM[CUBA.TIME_STEP] = self.dt
        engine.CM[CUBA.NUMBER_OF_TIME_STEPS] = self.tsteps

        # System Parameters data
        engine.SP[CUBAExtension.REFERENCE_DENSITY] = self.rden
        engine.SP[CUBA.KINEMATIC_VISCOSITY] = self.kvisc
        engine.SP[CUBAExtension.GRAVITY] = (self.gx, self.gy, self.gz)
        engine.SP[CUBAExtension.EXTERNAL_FORCING] = self.ext_frc

        # Boundary Conditions data
        engine.BC[CUBA.VELOCITY] = {'open': 'periodic',
                                    'wall': 'noSlip'}

        engine.BC[CUBA.DENSITY] = {'open': 'periodic',
                                   'wall': 'noFlux'}

        # Configure a lattice
        lat = make_cubic_lattice(self.test_lattice_name, self.dr,
                                 (self.nx, self.ny, self.nz))

        # Set geometry for a Poiseuille channel
        for node in lat.iter_nodes():
            if node.index[0] == 0 or node.index[0] == self.nx-1:
                node.data[CUBA.MATERIAL_ID] = self.solid_enum
            else:
                node.data[CUBA.MATERIAL_ID] = self.fluid_enum
            lat.update_nodes([node])

        # Initialize flow variables at fluid lattice nodes
        for node in lat.iter_nodes():
            if node.data[CUBA.MATERIAL_ID] == self.fluid_enum:
                node.data[CUBA.VELOCITY] = (0, 0, 0)
                node.data[CUBA.DENSITY] = 1.0
            lat.update_nodes([node])

        # Add lattice to the engine
        engine.add_dataset(lat)

    def _analyse_test_problem_results(self, engine):
        proxy_lat = engine.get_dataset(self.test_lattice_name)

        # Compute the relative L2-error norm
        tot_diff2 = 0.0
        tot_ana2 = 0.0
        tot_ux = 0.0
        tot_uy = 0.0
        for node in proxy_lat.iter_nodes():
            if node.data[CUBA.MATERIAL_ID] == self.fluid_enum:
                sim_ux = node.data[CUBA.VELOCITY][0]
                sim_uy = node.data[CUBA.VELOCITY][1]
                sim_uz = node.data[CUBA.VELOCITY][2]
                ana_uz = self._calc_poiseuille_vel(node.index[0])
                diff = ana_uz - sim_uz
                tot_diff2 = tot_diff2 + diff*diff
                tot_ana2 = tot_ana2 + ana_uz*ana_uz
                tot_ux = tot_ux + sim_ux
                tot_uy = tot_uy + sim_uy

        rel_l2_error = math.sqrt(tot_diff2/tot_ana2)
        print ('Relative L2-error norm = %e\n' % (rel_l2_error))

        self.assertTrue(rel_l2_error < 1.0e-10)
        self.assertTrue(math.fabs(tot_ux) < 1.0e-10)
        self.assertTrue(math.fabs(tot_uy) < 1.0e-10)

    def _calc_poiseuille_vel(self, index):
        wall_dist = (float(index-1) + 0.5)
        centerl = (wall_dist) - self.channel_h
        d = (centerl/self.channel_h)*(centerl/self.channel_h)
        return self.max_vel*(1.0 - d)

    def create_dataset(self, name):
        """ This method is overriden, because Palabos requires that certain
        CUBA keys are always defined on ProxyLattice objects.

        """
        lat = make_cubic_lattice(name, 1.0, (2, 3, 4))
        for node in lat.iter_nodes():
            node.data = {CUBA.MATERIAL_ID: self.fluid_enum,
                         CUBA.DENSITY: 0, CUBA.VELOCITY: [0, 0, 0]}
            lat.update_nodes([node])
        return lat

    def check_instance_of_dataset(self, ds):
        self.assertIsInstance(ds, ABCLattice,
                              "Error: Dataset must be ABCLattice!")

    def create_dataset_items(self):
        """ Not applicable to Palabos
        """
        pass
