import time
import os
import luigi

def files_in_dir(root_dir):
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            yield os.path.join(root, file)


class MatchingFiles(luigi.ExternalTask):
    """
    A Task that represents all the files in a certain directory whose name match a pattern
    """
    root_dir = luigi.Parameter()
    predicate = luigi.Parameter()

    def output(self):
        return [luigi.LocalTarget(f) for f in files_in_dir(self.root_dir) if self.predicate(f)]


class MTimeMixin:
    """
        Mixin that flags a task as incomplete if any requirement
        is incomplete or has been updated more recently than this task
        This is based on http://stackoverflow.com/a/29304506, but extends
        it to support multiple input / output dependencies.

        From https://stackoverflow.com/a/37893165
    """

    def complete(self):
        def to_list(obj):
            if type(obj) in (type(()), type([])):
                return obj
            else:
                return [obj]

        def mtime(path):
            #return time.ctime(os.path.getmtime(path))
            return os.path.getmtime(path)

        # Check if all outputs exist
        if not all(os.path.exists(out.path) for out in to_list(self.output())):
            return False

        # "birth" of output: earliest created output file
        self_mtime = min(mtime(out.path) for out in to_list(self.output()))

        # Check if input either incomplete or younger than output
        for el in to_list(self.requires()):
            if not el.complete():
                return False
            for output in to_list(el.output()):
                if mtime(output.path) > self_mtime:
                    return False

        return True

