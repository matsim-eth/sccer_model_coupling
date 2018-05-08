# see http://timmurphy.org/2015/09/27/how-to-get-a-makefile-directory-path/ for a breakdown of
# what this all means
MAKE_DIR = $(dir $(realpath $(firstword $(MAKEFILE_LIST))))

# Java paths
JAVA_RELEASE_DIR = $(MAKE_DIR)/.release
JAVA_RUN = java -Xmx7g -cp "$(JAVA_RELEASE_DIR)/sccer_model_coupling-0.0.1-SNAPSHOT/*:$(JAVA_RELEASE_DIR)/sccer_model_coupling-0.0.1-SNAPSHOT/libs/*"

JAVA_FILES = $(find $(MAKE_DIR)/matsim-interface/src/ -name '*.java')

# Python paths
VENV_DIR = $(MAKE_DIR)/sccer-venv/
PIP = $(VENV_DIR)/bin/pip
PYTHON = $(VENV_DIR)/bin/python3.5
JUPYTER = $(VENV_DIR)/bin/jupyter
RUN_NOTEBOOK = $(JUPYTER) nbconvert --ExecutePreprocessor.timeout=-1 --inplace --to notebook --execute

# Data paths
DATA_DIR = $(MAKE_DIR)/data/
RAW_DIR = $(DATA_DIR)/00_raw/
INTERIM_DIR = $(DATA_DIR)/10_interim/
FINAL_DIR = $(DATA_DIR)/20_final/

####################################################################################
.PHONY: python_dependencies java_utils setup_euler clean all

start_notebook: targets/python_dependencies all
	$(JUPYTER) notebook

all: targets/stem_classes

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
	$(PIP) install -r requirements.txt
	$(PIP) install -e $(MAKE_DIR)/python-analysis/src/
	touch targets/python_dependencies

targets/java_utils: $(JAVA_FILES) | targets
	cd matsim-interface/; \
	mvn assembly:assembly -DskipTests=true; \
	unzip -u -o target/sccer_model_coupling-0.0.1-SNAPSHOT-release.zip -d $(JAVA_RELEASE_DIR)
	touch targets/java_utils

requirements.txt:
	$(PIP) freeze | grep -v '^-e ' > requirements.txt

targets:
	mkdir targets

#####################################################################################
# Data processing
#####################################################################################

targets/features: targets/java_utils | targets
	$(JAVA_RUN) ch.ethz.ivt.sccer.planfeatures.WriteSccerPlanFeatures $(RAW_DIR)/output_population.xml.gz $(RAW_DIR)/output_network.xml.gz $(RAW_DIR)/10.events.xml.gz $(INTERIM_DIR)/features.txt
	touch $@

targets/stem_classes: targets/features targets/python_dependencies | targets
	$(PYTHON) python-analysis/src/run/002_activity_patterns_with_park_time.py -i $(INTERIM_DIR)/features.txt -o $(FINAL_DIR)/002_clusters.csv -f $(FINAL_DIR)/002_parktimes_per_cluster.pdf
	touch $@
