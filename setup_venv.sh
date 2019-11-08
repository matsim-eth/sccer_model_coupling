#!/bin/bash

module load new
module load python/3.6.1

python -m venv sccer-venv
. sccer-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
