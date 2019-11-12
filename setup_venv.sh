#!/bin/bash

module load new gcc/4.8.2 python/3.6.0

python3 -m venv sccer-venv
. sccer-venv/bin/activate
python3 --version
which python3
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
