#!/bin/bash
set -e

# Define Miniconda3
miniconda_version="4.6.14"
miniconda_url="https://repo.anaconda.com/miniconda/Miniconda3-${miniconda_version}-Linux-x86_64.sh"
miniconda_md5="718259965f234088d785cad1fbd7de03"

python_version="3.6"

# Define Python requirements
python_requirements=$(cat <<EOF
attrs
Click
click-plugins
cligj
cycler
Fiona
geopandas
joblib
kiwisolver
matplotlib
munch
numpy
pandas
pyparsing
pyproj
python-dateutil
pytz
Rtree
scikit-learn
scipy
seaborn
Shapely
six
tqdm
xlrd
EOF
)

# Miniconda update script to avoid too long paths in interpreter path
miniconda_update_script=$(cat <<EOF
import sys
import re

with open(sys.argv[1]) as f:
    content = f.read()
    content = re.sub(r'#!(.+)/miniconda3/bin/python', '#!/usr/bin/env python', content)

with open(sys.argv[1], "w+") as f:
    f.write(content)
EOF
)

# I) Ensure the target directory is there
environment_directory=$(realpath "$1")

if [ ! -d ${environment_directory} ]; then
    echo "Creating target directory: ${environment_directory}"
    mkdir -p ${environment_directory}
else
    echo "Target directory already exists: ${environment_directory}"
fi

cd ${environment_directory}

# II) Downloads

## II.1) Download Miniconda
if [ "$(md5sum miniconda.sh)" == "${miniconda_md5}  miniconda.sh" ]; then
    echo "Miniconda 3 ${miniconda_version} already downloaded."
else
    echo "Downloading Miniconda3 ${miniconda_version} ..."
    rm -rf miniconda_installed
    rm -rf python_installed
    curl -o miniconda.sh ${miniconda_url}
fi

# III) Install everything

# III.1) Install Miniconda
if [ -f miniconda_installed ]; then
    echo "Miniconda3 ${miniconda_version} already installed."
else
    echo "Installing Miniconda3 ${miniconda_version} ..."

    rm -rf miniconda3
    sh miniconda.sh -b -u -p miniconda3

    cat <<< "${miniconda_update_script}" > fix_conda.py

    PATH=${environment_directory}/miniconda3/bin:$PATH
    python fix_conda.py miniconda3/bin/conda
    python fix_conda.py miniconda3/bin/conda-env
    conda update -y conda

    touch miniconda_installed
fi

# III.2) Create Python environment
if [ -f python_installed ]; then
    echo "Python environment is already set up."
else
    echo "Setting up Python environment ..."

    cat <<< "${python_requirements}" > requirements.txt
    conda create -p venv python=${python_version} --no-default-packages --channel conda-forge --file requirements.txt -y

    touch python_installed
fi