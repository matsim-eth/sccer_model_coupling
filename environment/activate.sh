#!/bin/bash

environment_directory=$(realpath "$1")

if [ ! -f ${environment_directory}/miniconda_installed ]; then
    echo "Miniconda is not installed properly."
    exit 1
else
    PATH=${environment_directory}/miniconda3/bin:$PATH

    echo "Testing Miniconda ..."
    conda -V
fi

if [ ! -f ${environment_directory}/python_installed ]; then
    echo "Python environment is not installed properly."
    exit 1
else
    source activate ${environment_directory}/venv

    echo "Testing Python ..."
    python3 --version
fi

echo "Environment is set up."
