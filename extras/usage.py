"""usage.py

    Example usage of the Abstract File Batch.
"""

import os

from abstract_file_batch import AbstractFileBatch


class FileBatchExample(AbstractFileBatch):
    """Example implementation of 'AbstractFileBatch'.
    """

    # Overridden global constants

    DEFAULT_OUTPUT_DIR = "<INPUT_DIR>/output"
    DEFAULT_OUTPUT_SUFFIX = "_out"

    DEFAULT_EXTENSIONS = [ "txt" ]
    #DEFAULT_OUTPUT_EXTENSION = "txt"



    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.script_var = "Variable"


    def init(self):
        # Declare variables to use as arguments
        self.maxNumber = 10
        self.maxSize = 1048576


    def add_arguments(self, optional_arguments, required_arguments):
        # Add an optional argument
        optional_arguments.add_argument(
            "--maxNumber",
            "-mn",
            help=(
                "maximum number of files (default: {})"
            ).format(self.maxNumber),
            type=int,
            default=self.maxNumber
        )

        # Add a required argument
        required_arguments.add_argument(
            "--maxSize",
            "-ms",
            help="maximum file size (in bytes)",
            type=int,
            required=True
        )


    def checkinputs(self):
        if self.maxNumber < 2:
            raise Exception("TOO SMALL!")


    def preprocess(self):
        # Example test to cancel the process before it starts
        if len(self.inputFiles) > self.maxNumber:
            self.logger.info(
                "Too many files ({}).".format(len(self.inputFiles))
            )
            return False

        self.logger.info(
            "About to start the process."
            " Time to grab a coffee."
        )
        return True


    def postprocess(self, status):
        self.logger.info(
            "Process has finished."
            " Hope you had time to enjoy your coffee."
        )
        return True


    # Example of optional additional checks
    def checkfile(self, filePath):
        # Check file is smaller than 1MB
        if os.stat(filePath).st_size > self.maxSize:
            raise OSError("File '{}' too big".format(filePath))


    def processfile(self, srcFilePath, destFilePath):
        # Core process on each file
        self.logger.info((
            "File '{}' being processed to '{}'..."
        ).format(srcFilePath, destFilePath))

        # Create empty output file
        with open(destFilePath, "w") as outfile:
            pass



if __name__ == "__main__":

    # TODO: configure logger
    import logging
    logging.basicConfig(level=logging.DEBUG)

    '''
    import sys
    batch = FileBatchExample(sys.argv[1:])
    '''
    batch = FileBatchExample()
    batch.run()
