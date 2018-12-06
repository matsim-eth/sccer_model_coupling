import os
import luigi
import luigi.contrib.external_program
from plumbum.cmd import mvn
from plumbum import local, FG

from luigi_utils import MTimeMixin

class JavaFiles(luigi.ExternalTask):
    def output(self):
        java_files = [luigi.LocalTarget(os.path.join('matsim-interface', 'pom.xml'))]
        for root, dirs, files in os.walk("matsim-interface"):
            for file in files:
                if file.endswith(".java"):
                    java_files.append(luigi.LocalTarget(os.path.join(root, file)))
        return java_files

class JavaCompilationTask(MTimeMixin, luigi.Task):
    def requires(self):
        # This does not seem to work as Make, and does not re-run if the inputs are newer than output...
        return JavaFiles()

    def run(self):
        with local.cwd(local.cwd / 'matsim-interface'):
            mvn['assembly:assembly', '-DskipTests=true'] & FG

    def output(self):
        # TODO: avoid having version number in there!
        return luigi.LocalTarget(os.path.join('matsim-interface', 'target', 'sccer_model_coupling-0.0.1-SNAPSHOT-release.zip'))

if __name__ == '__main__':
    luigi.build([JavaCompilationTask()])
