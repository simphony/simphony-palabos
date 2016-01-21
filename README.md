# simphony-palabos
A file-IO based wrapper for Palabos LB library

Install
-------
To install Palabos library for SimPhoNy use the install script
. install_palabos.sh
It will download version 1.5r1 and place it in /simphony-palabos/palabos/palabos-v1.5r1/. You will need 'wget' to use this script.

Compile Palabos engine for SimPhoNy
-----------------------------------
Running the script
. compile_palabos_engine.sh
will compile the Palabos engines and copies the executables into /usr/local/bin. You will need an MPI-implementation to compile the engines. Please refer to Palabos documentation at http://www.palabos.org/documentation/userguide
