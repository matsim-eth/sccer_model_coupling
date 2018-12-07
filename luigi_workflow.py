import os
import shutil
import luigi
import luigi.contrib.external_program
from plumbum.cmd import mvn, unzip, rm
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
