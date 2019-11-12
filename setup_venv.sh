#!/bin/bash

module load new gcc/4.8.2 python/3.6.0

python3.6.0 -m venv sccer-venv
. sccer-venv/bin/activate
python --version
which python
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
