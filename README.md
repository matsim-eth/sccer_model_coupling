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

