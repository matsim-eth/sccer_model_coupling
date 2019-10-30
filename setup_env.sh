#!/bin/sh

module load python/3.6.1

python -m venv sccer-venv
source sccer-venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
