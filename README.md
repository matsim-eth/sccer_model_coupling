# SCCER Model Coupling
Code for the coupling of MATSim with various energy-related models

## Structure of the repository
The repository contains 3 main sub-directories:
- a Java project, for all MATSim processing
- a Python project, for data analysis and transformation
- a data directory, containing 3 subdirectories: raw data (external), interim (transformed from raw but unusable as such) and final (to be shared)

A Makefile automates the transformation from raw to final data.
For the moment, the only way to run on euler is to clone the repository there,
and submit a job containing a make task (eg bsub make target/smth).

A special make target sets up all that needs to be setup to submit jobs on euler.

## Running on Euler
To run the computations on ETHZ's Euler Cluster, run

```
./setup_euler.sh
make all_euler
```

simply submitting a `make` job unfortunately does not work properly, as the compilers (python and java) need access to the Internet,
which I did not manage from the compute nodes.
The "setup euler" stage could not be included in a make target either, because make targets are executed in a sub-shell
and do not change the environment of later targets.
