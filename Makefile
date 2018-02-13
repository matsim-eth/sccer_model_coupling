# see http://timmurphy.org/2015/09/27/how-to-get-a-makefile-directory-path/ for a breakdown of
# what this all means
MAKE_DIR = $(dir $(realpath $(firstword $(MAKEFILE_LIST))))

# Java paths
JAVA_RELEASE_DIR = $(MAKE_DIR)/.release
JAVA_RUN = java -Xmx4g -cp "$(JAVA_RELEASE_DIR)/sccer_model_coupling-0.0.1-SNAPSHOT/*:$(JAVA_RELEASE_DIR)/sccer_model_coupling-0.0.1-SNAPSHOT/libs/*"

# Python paths
VENV_DIR = $(MAKE_DIR)/sccer-venv/
PIP = $(VENV_DIR)/bin/pip
PYTHON = $(VENV_DIR)/bin/python3.5

# Data paths
DATA_DIR = $(MAKE_DIR)/data/
RAW_DIR = $(DATA_DIR)/00_raw/
INTERIM_DIR = $(DATA_DIR)/10_interim/
FINAL_DIR = $(DATA_DIR)/20_final/

####################################################################################
.PHONY: python_dependencies java_utils setup_euler clean all

all: targets/features

clean:
	rm -r targets
	rm $(INTERIM_DIR)/*
	rm $(FINAL_DIR)/*
	cd matsim-interface/; mvn clean

#####################################################################################
# Build, setup
#####################################################################################
targets/venv: | targets
	virtualenv -p python3.5 $(VENV_DIR)
	touch targets/venv

targets/python_dependencies: targets/venv | targets
	$(PIP) install -r requirement.txt
	$(PIP) install -e $(MAKE_DIR)/python-analysis/src/
	touch targets/python_dependencies

java_utils: matsim-interface
	cd matsim-interface/; \
	mvn assembly:assembly -DskipTests=true; \
	unzip -u -o target/sccer_model_coupling-0.0.1-SNAPSHOT-release.zip -d $(JAVA_RELEASE_DIR)

requirements.txt:
	$(PIP) freeze > requirements.txt

targets:
	mkdir targets

#####################################################################################
# Data processing
#####################################################################################

targets/features: java_utils | targets
	$(JAVA_RUN) ch.ethz.ivt.sccer.planfeatures.WriteSccerPlanFeatures $(RAW_DIR)/output_population.xml.gz $(RAW_DIR)/output_network.xml.gz $(RAW_DIR)/10.events.xml.gz $(INTERIM_DIR)/features.txt
	touch targets/features
