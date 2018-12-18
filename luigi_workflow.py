import os
import shutil
import luigi
import luigi.contrib.external_program
from plumbum.cmd import mvn, unzip, java
from plumbum import local, FG

import luigi_utils as lu

###############################################################################
# Config Options
###############################################################################

class java_settings(luigi.Config):
    path = luigi.Parameter(default='matsim-interface')
    release_dir = luigi.Parameter(default='.release')
    release_name = luigi.Parameter(default='sccer_model_coupling-0.0.1-SNAPSHOT')
    jvm_options = luigi.ListParameter(default=['-Xmx7g'])

class data_settings(luigi.Config):
    raw_path = luigi.Parameter(default='data/00_raw')
    interim_path = luigi.Parameter(default='data/10_interim')
    final_path = luigi.Parameter(default='data/20_final')

    network_file = luigi.Parameter(default='output_network.xml.gz') 
    population_file = luigi.Parameter(default='output_population.xml.gz') 
    households_file = luigi.Parameter(default='output_households.xml.gz') 
    events_file = luigi.Parameter(default='10.events.xml.gz') 

    def network_path(self):
        return self.get_raw(self.network_file)

    def population_path(self):
        return self.get_raw(self.population_file)

    def events_path(self):
        return self.get_raw(self.events_file)

    def households_path(self):
        return self.get_raw(self.households_file)
    
    def get_raw(self, f):
        return os.path.join(self.raw_path, f)

    def get_interim(self, f):
        return os.path.join(self.interim_path, f)

    def get_final(self, f):
        return os.path.join(self.final_path, f)


###############################################################################
# Compilation of Java Classes
###############################################################################

class JavaCompilationTask(lu.MTimeMixin, luigi.Task):
    def requires(self):
        # This does not seem to work as Make, and does not re-run if the inputs are newer than output...
        return lu.MatchingFiles(java_settings().path,
                    lambda f: f.endswith('pom.xml') or f.endswith(".java"))

    def run(self):
        with local.cwd(local.cwd / java_settings().path):
            mvn['assembly:assembly', '-DskipTests=true'] & FG

        shutil.rmtree(java_settings().release_dir)

        # TODO replace by python equivalent for portability
        unzip['-u', '-o', os.path.join(java_settings().path, 'target', '%s-release.zip' % java_settings().release_name), '-d', java_settings().release_dir] & FG

    def output(self):
        d = java_settings().release_dir
        #if (os.path.exists(d)):
        #    # If release directory exists, return all files in it, so that it is rebuild only if java files are newer
        #    # (date comparison does not work with directory, as in Make)
        #    return [luigi.LocalTarget(f) for f in lu.files_in_dir(d)]

        return luigi.LocalTarget(d)


###############################################################################
# Processing Tasks
###############################################################################

class JavaTask(luigi.Task):
    def main_class(self):
        """
        return the name of the main class
        """
        raise NonImplementedException()

    def class_path(self):
        return os.pathsep.join([f for f in lu.files_in_dir(java_settings().release_dir) if f.endswith('.jar')])

    def jvm_parameters(self):
        return java_settings().jvm_options

    def program_parameters(self):
        """
        return a list of parameters
        """
        return []

    def requires(self):
        return JavaCompilationTask()

    # TODO: add "input files" and "output files" for the case where the program is
    # className <params> <inputs> <outputs>

    # Could alternately relies on JPype, which would allow configuration directly
    # in Python

    def run(self):
        params = []
        params += self.jvm_parameters()
        params += ['-cp', self.class_path()]
        params += [self.main_class()]
        params += self.program_parameters()
        java(params) & FG        

class FeaturesTask(JavaTask):
    _out = data_settings().get_interim('features.txt')

    def main_class(self):
        return 'ch.ethz.ivt.sccer.planfeatures.WriteSccerPlanFeatures'

    def program_parameters(self):
        return [data_settings().population_path(), data_settings().network_path(), data_settings().events_path(), self._out]

    def output(self):
        return luigi.LocalTarget(self._out)

class HouseholdFeaturesTask(JavaTask):
    _out = data_settings().get_interim('household_features.txt')

    def main_class(self):
        return 'ch.ethz.ivt.sccer.planfeatures.WriteSccerHouseholdFeatures'

    def program_parameters(self):
        return [data_settings().population_path(), data_settings().households_path(), self._out]

    def output(self):
        return luigi.LocalTarget(self._out)
