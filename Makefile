# see http://timmurphy.org/2015/09/27/how-to-get-a-makefile-directory-path/ for a breakdown of
# what this all means
MAKE_DIR = $(dir $(realpath $(firstword $(MAKEFILE_LIST))))
JAVA_RELEASE_DIR = $(MAKE_DIR)/.release
JAVA_RUN = java -cp "$(JAVA_RELEASE_DIR)/*:$(JAVA_RELEASE_DIR)/lib/*"

VENV_DIR = $(MAKE_DIR)/sccer-venv/
PIP = $(VENV_DIR)/bin/pip
PYTHON = $(VENV_DIR)/bin/python3.5

venv:
	virtualenv -p python3.5 $(VENV_DIR)

python_dependencies:
	$(PIP) install -r requirement.txt
	$(PIP) install -e $(MAKE_DIR)/python-analysis/src/

java_utils:
	cd matsim-interface/
	mvn assembly:assembly -DskipTests=true
	unzip target/sccer_model_coupling-0.0.1-SNAPSHOT-release.zip -d $(JAVA_RELEASE_DIR)

requirements.txt:
	$(PIP) freeze > requirements.txt
