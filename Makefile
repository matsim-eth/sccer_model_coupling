# see http://timmurphy.org/2015/09/27/how-to-get-a-makefile-directory-path/ for a breakdown of
# what this all means
MAKE_DIR = $(dir $(realpath $(firstword $(MAKEFILE_LIST))))

# Java paths
JAVA_RELEASE_DIR = $(MAKE_DIR)/.release
JAVA_RUN = java -Xmx17g -cp "$(JAVA_RELEASE_DIR)/sccer_model_coupling-0.0.1-SNAPSHOT/*:$(JAVA_RELEASE_DIR)/sccer_model_coupling-0.0.1-SNAPSHOT/libs/*"

JAVA_FILES = $(find $(MAKE_DIR)/matsim-interface/src/ -name '*.java')

# Python paths
VENV_DIR = $(MAKE_DIR)/sccer-venv/
PIP = $(VENV_DIR)/bin/pip
PYTHON = $(VENV_DIR)/bin/python3.6
JUPYTER = $(VENV_DIR)/bin/jupyter
RUN_NOTEBOOK = $(JUPYTER) nbconvert --ExecutePreprocessor.timeout=-1 --inplace --to notebook --execute

# Data paths
DATA_DIR = $(MAKE_DIR)/data/
RAW_DIR = $(DATA_DIR)/00_raw/
INTERIM_DIR = $(DATA_DIR)/10_interim/
FINAL_DIR = $(DATA_DIR)/20_final/

####################################################################################
.PHONY: python_dependencies java_utils setup_euler clean all all_euler

all: targets/stem_classes

start_notebook: targets/python_dependencies all
	$(JUPYTER) notebook

# somehow did not manage to get access to outside world from compute nodes.
# So on euler, need to first build python venv and java utils, and only then
# submit job for the rest
all_euler: targets/python_dependencies targets/java_utils
	# TODO: check what bsub parameters make sense (or switch to snakemake to handle this better)
	bsub -R "rusage[mem=7500]" make all

clean:
	rm -r targets
	rm $(INTERIM_DIR)/*
	rm $(FINAL_DIR)/*
	cd matsim-interface/; mvn clean

#####################################################################################
# Build, setup
#####################################################################################
targets/venv:
	virtualenv -p python3.6 $(VENV_DIR)
	touch targets/venv

targets/python_dependencies: targets/venv
	$(PIP) install -r requirements.txt
	$(PIP) install -e $(MAKE_DIR)/python-analysis/src/
	touch targets/python_dependencies

targets/java_utils: $(JAVA_FILES)
	cd matsim-interface/; \
	mvn assembly:assembly -DskipTests=true; \
	unzip -u -o target/sccer_model_coupling-0.0.1-SNAPSHOT-release.zip -d $(JAVA_RELEASE_DIR)
	touch targets/java_utils

requirements.txt:
	$(PIP) freeze | grep -v '^-e ' > requirements.txt

#####################################################################################
# Data processing
#####################################################################################

targets/features: targets/java_utils
	$(JAVA_RUN) ch.ethz.ivt.sccer.planfeatures.WriteSccerPlanFeatures $(RAW_DIR)/population.xml.gz $(RAW_DIR)/network.xml.gz $(RAW_DIR)/output_events.xml.gz $(INTERIM_DIR)/features.txt
	touch $@

targets/household_features: targets/java_utils
	$(JAVA_RUN) ch.ethz.ivt.sccer.planfeatures.WriteSccerHouseholdFeatures $(RAW_DIR)/population.xml.gz $(RAW_DIR)/households.xml.gz $(INTERIM_DIR)/household_features.txt
	touch $@

targets/stem_classes: targets/features targets/household_features targets/python_dependencies
	$(PYTHON) python-analysis/src/run/002_activity_patterns_with_park_time.py -i $(INTERIM_DIR)/features.txt -o $(FINAL_DIR)/002_clusters.csv -f $(FINAL_DIR)/002_parktimes_per_cluster.pdf
	touch $@
