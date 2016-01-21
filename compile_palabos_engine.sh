#!/bin/bash
# compiling palabos engine files for SimPhoNy
cur_dir=$PWD
cd $cur_dir/palabos/source
make

# copy executables to a folder in PATH
cp *.exe /usr/local/bin
cd $cur_dir

