# Not sure what the best solution is here.
# Relative path works when using "pip editable" installation from local directory,
# but is probably pretty brittle.
#
# An alternative would be to get the path to the files as command line argument and specify them
# in the makefile, but sometimes it is more understandable to have the path hard-coded in the script,
# and this is simply not an option in notebooks.
# Advantage is that it works as well for python and java

import os

ROOT_DIR = os.path.abspath( os.path.join( os.path.dirname( __file__ ), ".." , ".." , ".." ) )
RAW_DIR = os.path.join( ROOT_DIR , "data" , "00_raw" )
INTERIM_DIR = os.path.join( ROOT_DIR , "data" , "10_interim" )
FINAL_DIR = os.path.join( ROOT_DIR , "data" , "20_final" )


def _path_getter( dir ):
    def f( file ):
        os.makedirs( dir , exist_ok=True )
        return os.path.join( dir , file )

    return f


# helper functions: get path to a file and create directories if do not exist
raw_file_path = _path_getter( RAW_DIR )
interim_file_path = _path_getter( INTERIM_DIR )
final_file_path = _path_getter( FINAL_DIR )

