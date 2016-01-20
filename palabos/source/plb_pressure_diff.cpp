#include "palabos3D.h"
#include "palabos3D.hh"
#include <vector>
#include <cmath>

using namespace plb;
using namespace std;

typedef double T;
#define DESCRIPTOR descriptors::D3Q19Descriptor

// This function object returns a zero velocity, and a pressure which decreases
//   linearly in x-direction. It is used to initialize the particle populations.
class PressureGradient {
public:
        PressureGradient(T deltaP_, plint nx_) : deltaP(deltaP_), nx(nx_)
        { }
        void operator() (plint iX, plint iY, plint iZ, T& density, Array<T,3>& velocity) const
        {
                velocity.resetToZero();
                density = 1. - deltaP*DESCRIPTOR<T>::invCs2 / (T)(nx-1) * (T)iX;
        }
private:
        T deltaP;
        plint nx;
};

void setupPressureDifferenceProblem( MultiBlockLattice3D<T,DESCRIPTOR>& lattice,
                       OnLatticeBoundaryCondition3D<T,DESCRIPTOR>* boundaryCondition,
                       MultiScalarField3D<int>& geometry, T deltaP)
{
        const plint nx = lattice.getNx();
        const plint ny = lattice.getNy();
        const plint nz = lattice.getNz();

        Box3D inlet (0,0,      1,ny-2, 1,nz-2);
        boundaryCondition->addPressureBoundary0N(inlet, lattice);
        setBoundaryDensity(lattice, inlet, (T) 1.);

        Box3D outlet(nx-1,nx-1, 1,ny-2, 1,nz-2);
        boundaryCondition->addPressureBoundary0P(outlet, lattice);
        setBoundaryDensity(lattice, outlet, (T) 1. - deltaP*DESCRIPTOR<T>::invCs2);

        // Where "geometry" evaluates to 1 (solid boundary), use bounce-back.
        defineDynamics(lattice, geometry, new BounceBack<T,DESCRIPTOR>(), 1);
        // Where "geometry" evaluates to 2 (solid), use no-dynamics (which does nothing).
        defineDynamics(lattice, geometry, new NoDynamics<T,DESCRIPTOR>(), 2);

        initializeAtEquilibrium( lattice, lattice.getBoundingBox(), PressureGradient(deltaP, nx) );

        lattice.initialize();
        delete boundaryCondition;
}

void writeVTK_velocity(MultiBlockLattice3D<T,DESCRIPTOR>& lattice, string fname)
{
        VtkImageOutput3D<T> vtkOut(fname.c_str(), 1.);
        vtkOut.writeData<3,float>(*computeVelocity(lattice), "velocity", 1.);
}

void writeVTK_density(MultiBlockLattice3D<T,DESCRIPTOR>& lattice, string fname)
{
        VtkImageOutput3D<T> vtkOut(fname.c_str(), 1.);
        vtkOut.writeData<float>(*computeDensity(lattice), "density", 1.);
}

int main(int argc, char **argv)
{
        plbInit(&argc, &argv);
        global::directories().setOutputDir("./");

        if (argc < 2) {
            pcout << "SimPhoNy-Palabos file-IO wrapper" << endl;
            pcout << "Usage: plb_pressure_diff.exe input_fname" << endl;
            return -1;
        }

        string geomFile, den_out_fname, vel_out_fname;
        string periodicity;
        plint nx, ny, nz, tSteps;
        T deltaP, nu=1.0;

        try {
            // Open the XML file.
            XMLreader xmlFile(argv[1]);

            xmlFile["SimPhoNy-Palabos"]["geometry"]["inputFile"].read(geomFile);
            xmlFile["SimPhoNy-Palabos"]["geometry"]["size"]["nx"].read(nx);
            xmlFile["SimPhoNy-Palabos"]["geometry"]["size"]["ny"].read(ny);
            xmlFile["SimPhoNy-Palabos"]["geometry"]["size"]["nz"].read(nz);
            xmlFile["SimPhoNy-Palabos"]["configuration"]["pressureDifference"].read(deltaP);
            xmlFile["SimPhoNy-Palabos"]["configuration"]["kinematicViscosity"].read(nu);
            xmlFile["SimPhoNy-Palabos"]["configuration"]["timeSteps"].read(tSteps);
            xmlFile["SimPhoNy-Palabos"]["configuration"]["periodicity"].read(periodicity);
            xmlFile["SimPhoNy-Palabos"]["output"]["density"].read(den_out_fname);
            xmlFile["SimPhoNy-Palabos"]["output"]["velocity"].read(vel_out_fname);
        }
        catch (PlbIOException& exception) {
            pcout << exception.what() << endl;
            return -1;
        }

        T omega = (T)1/(nu*DESCRIPTOR<T>::invCs2 + 0.5);
        MultiBlockLattice3D<T,DESCRIPTOR> lattice(nx,ny,nz, new BGKdynamics<T,DESCRIPTOR>(omega));

        if (periodicity == "non-periodic")
            lattice.periodicity().toggleAll(false);

        plb_ifstream geometryFile(geomFile.c_str());
        if (!geometryFile.is_open()){
            pcout << "Error: could not open the geometry file " << geomFile << endl;
            return -1;
        }

        MultiScalarField3D<int> geometry(nx,ny,nz);
        geometryFile >> geometry;

        setupPressureDifferenceProblem(lattice, createLocalBoundaryCondition3D<T,DESCRIPTOR>(), geometry, deltaP);

        for (plint iT=0;iT<tSteps;++iT)
                lattice.collideAndStream();

        writeVTK_velocity(lattice, vel_out_fname);
        writeVTK_density(lattice, den_out_fname);
}
