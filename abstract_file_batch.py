"""AbstractFileBatch
"""

__version__ = "1.0"
__author__ = "2-REC"


# TODO:
# - naming conventions (+argument names)
# - check level of each log (+check each message)
# - check all is ok
# - make example/implementation file
# - clean



import sys
import os
import errno
import argparse

import logging


if sys.version_info.major == 3:
    import queue
else:
    import Queue as queue

from convert_thread import ConvertThread



class AbstractFileBatch(object):
    """Abstract File Batch.

        Abstract class to process a list of files in separate threads.
    """

    # Default Values

    # Get input files from current directory
    DEFAULT_INPUT_DIR = "."
    # Save in place
    DEFAULT_OUTPUT_DIR = ""
    # No suffix
    DEFAULT_OUTPUT_SUFFIX = ""
    # 8 concurrent threads
    DEFAULT_NB_THREADS = 8
    # Backup existing files
    DEFAULT_NO_BACKUP = False
    # Look in sub directories
    DEFAULT_SUB_DIR = True

    # Extensions of input files ('None' => All types)
    DEFAULT_EXTENSIONS = None
    # Extension of output files ('None' => Same as input)
    DEFAULT_OUTPUT_EXTENSION = None


    def __init__(self, args=None):
        if type(self) is AbstractFileBatch:
            raise TypeError(
                "Cannot instantiate abstract class '{}'".format(type(self))
            )

        self.logger = logging.getLogger(self.__class__.__name__)

        self.inputDir = self.DEFAULT_INPUT_DIR
        self.inputFiles = None
        self.outputDir = self.DEFAULT_OUTPUT_DIR
        self.outputSuffix = self.DEFAULT_OUTPUT_SUFFIX
        self.numberThreads = self.DEFAULT_NB_THREADS
        self.noBackup = self.DEFAULT_NO_BACKUP
        self.subDir = self.DEFAULT_SUB_DIR

        self.extensions = self.DEFAULT_EXTENSIONS
        self.outputExtension = self.DEFAULT_OUTPUT_EXTENSION

        self.results = []

        self.init()
        self.__parse_arguments(args)


    # TODO: See if needed (?)
    '''
    def __del__(self):
        pass
    '''


    def __parse_arguments(self, args=None):
        # TODO: check if 'args' is string => split(" ")

        # TODO: add 'epilog'?
        parser = argparse.ArgumentParser(
            description=self.__class__.__doc__
        )

        # Options
        # TODO: change argument names (eg: '--input-dir' - Conventions?)
        # + use 'dest' to specify variable names
        # (and conform to conventions, eg: 'input_dir')
        parser.add_argument(
            "--inputDir",
            "-id",
            help=(
                "directory containing the input files"
                " (default: '{}')".format(self.inputDir)
            ),
            default=self.inputDir
        )
        parser.add_argument(
            "--inputFiles",
            "-if",
            help= (
                "list of input files"
                " (absolute paths, or relative to 'inputDir')"
            ),
            nargs='*',
            default=self.inputFiles
        )
        parser.add_argument(
            "--outputDir",
            "-od",
            help=(
                "directory where to generate the output files"
                " (default: '{}')".format(self.outputDir)
            ),
            default=self.outputDir
        )
        parser.add_argument(
            "--outputExtension",
            "-oe",
            help=(
                "extension of generated output files"
                " (default: '{}')".format(self.outputExtension)
            ),
            default=self.outputExtension
        )
        parser.add_argument(
            "--extensions",
            "-e",
            help=(
                "list of extensions of input files"
                " (default: '{}')".format(self.extensions)
            ),
            nargs='*',
            default=self.extensions
        )
        parser.add_argument(
            "--outputSuffix",
            "-os",
            help=(
                "suffix to add to output file names"
                " (default: '{}')".format(self.outputSuffix)
            ),
            default=self.outputSuffix
        )
        parser.add_argument(
            "--numberThreads",
            "-nt",
            help=(
                "number of concurrent threads (1 file per thread)"
                " (default: '{}')".format(self.numberThreads)
            ),
            default=self.numberThreads
        )

        # Flags
        parser.add_argument(
            "--noBackup",
            "-nb",
            help= (
                "force existing files to be overwritten"
                " (else a backup file is created)"
            ),
            action='store_false' if self.noBackup else 'store_true'
        )
        parser.add_argument(
            "--subDir",
            "-sd",
            help="look for input files in sub directories",
            action='store_false' if self.subDir else 'store_true'
        )

        required_arguments = parser.add_argument_group('required arguments')

        # Add derived/implementation script specific arguments
        self.add_arguments(parser, required_arguments)

        # Not using 'parse_args(namespace=self)'
        # to avoid the risk of injecting undefined attributes in class
        parsed_args = parser.parse_args(args)
        options = vars(parsed_args)
        for option in options:
            if hasattr(self, option):
                setattr(self, option, options[option])

        # TODO: handle more cleanly in try/except block (?)
        self.__checkinputs()


    def __checkinputs(self):
        # Extensions
        if self.extensions:
            self.extensions = self.__splitvalues(self.extensions)
            self.extensions = [
                extension.lower()
                for extension in self.extensions
            ]
        if self.outputExtension:
            self.outputExtension = self.outputExtension.lower()

        # Source directory
        if self.inputDir:
            self.inputDir = self.inputDir.strip()
        else:
            self.logger.info((
                "Using default value for inputDir: {}"
            ).format(self.DEFAULT_INPUT_DIR))
            self.inputDir = self.DEFAULT_INPUT_DIR
        self.checkpath(self.inputDir)


        # Source files
        if self.inputFiles:
            self.inputFiles = self.__splitvalues(self.inputFiles)

            inputFiles = []
            for inputFile in self.inputFiles:
                inputFile = inputFile.strip()

                if not os.path.isabs(inputFile):
                    inputFile = os.path.join(self.inputDir, inputFile)

                try:
                    self.__checkfile(inputFile, extensions=self.extensions)
                except OSError as e:
                    self.logger.info(str(e) + " => Ignoring")
                    continue

                inputFiles.append(inputFile)

            self.inputFiles = inputFiles

        else:
            self.logger.info((
                "Using default value for inputFiles:"
                " all files in '{}' (subdirectories: {})"
            ).format(self.inputDir, self.subDir))

            inputFiles = []
            files = self.getfiles(
                self.inputDir,
                extensions=self.extensions,
                recursive=self.subDir
            )
            for inputFile in files:
                inputFile = os.path.join(self.inputDir, inputFile)

                try:
                    self.__checkfile(inputFile, extensions=self.extensions)
                except OSError as e:
                    self.logger.info(str(e) + " => Ignoring")
                    continue

                inputFiles.append(inputFile)

            self.inputFiles = inputFiles

        # Output directory/directories
        if not self.outputDir:
            self.outputDir = self.DEFAULT_OUTPUT_DIR
            self.logger.info((
                "Using default output directory: {}"
            ).format(self.outputDir))

        self.outputDir = self.outputDir.strip()

        if self.outputDir and self.outputDir[0] == ".":
            # Relative path from current dir => same for all files
            self.checkpath(self.outputDir, False)
            self.logger.info((
                "Using common relative output directory: {}"
            ).format(self.outputDir))

        elif os.path.isabs(self.outputDir):
            # Absolute path => same for all files
            self.checkpath(self.outputDir, False)
            self.logger.info((
                "Using common absolute output directory: {}"
            ).format(self.outputDir))

        elif self.outputDir.find("<INPUT_DIR>") == 0:
            self.outputDir = self.outputDir.replace("<INPUT_DIR>", self.inputDir)
            self.logger.info((
                "Using common output directory: {}"
            ).format(self.outputDir))

        else:
            # Relative path => different for each file
            if self.outputDir:
                self.outputDir = os.path.join("<IN_PLACE>", self.outputDir)
            else:
                self.outputDir = "<IN_PLACE>"
            self.logger.info((
                "Using separate output directories: {}"
            ).format(self.outputDir))

        self.checkinputs()


    def run(self):
        if not self.inputFiles:
            self.logger.warning("No files to process")
            return True

        # TODO: raise+catch exceptions instead of boolean return (?)
        # (idem for 'process' & 'postprocess')
        if not self.preprocess():
            self.logger.error("Error in pre-process! => Aborting")
            return False

        success = self.process()
        if not success:
            self.logger.error("Error in process!")

        if not self.postprocess(success):
            self.logger.error("Error in post-process!")
            return False

        return success


    def process(self):
        self.logger.info((
            "Files to process:\n{}"
        ).format("\n".join(self.inputFiles)))

        temp_files = []

        in_queue = queue.Queue()
        out_queue = queue.Queue()

        # Spawn a pool of threads and pass queue instances
        for i in range(self.numberThreads):
            thread = ConvertThread(in_queue, out_queue)
            thread.setDaemon(True)
            thread.start()


        errors = False
        for inputFile in self.inputFiles:
            self.logger.info("Processing file '{}'".format(inputFile))

            #filePath, sep, fileName = inputFile.rpartition("/")
            filePath = os.path.dirname(inputFile)
            fileName = os.path.basename(inputFile)

            if "<IN_PLACE>" in self.outputDir:
                # Default output directory
                outputDir = self.outputDir.replace("<IN_PLACE>", filePath)
                self.checkpath(outputDir, False)
            else:
                if self.inputDir in filePath:
                    outputDir = self.outputDir \
                        + filePath.replace(self.inputDir, "")
                else:
                    outputDir = self.outputDir

            if not os.path.isdir(outputDir):
                self.logger.info((
                    "Creating output directory '{}'"
                ).format(outputDir))
                os.makedirs(outputDir)

            # Change extension of fileName if required
            if self.outputExtension:
                #last_point_index = fileName.rfind(".")
                #fileName = fileName[:last_point_index + 1] + self.outputExtension
                extension = os.path.splitext(fileName)[1]
                if extension:
                    fileName = "{}.{}".format(fileName[:-len(extension)], self.outputExtension)
                else:
                    fileName += ".{}".format(self.outputExtension)

            # Add suffix to fileName if required
            if self.outputSuffix:
                #baseName = fileName.rpartition(".")[0]
                #if baseName:
                #    fileName = fileName.replace(baseName, baseName + self.outputSuffix)
                #else:
                #    fileName += self.outputSuffix
                baseName, extension = os.path.splitext(fileName)
                if extension:
                    fileName = baseName + self.outputSuffix + extension
                else:
                    fileName += self.outputSuffix

            outputFile = os.path.join(outputDir, fileName)
            self.logger.info("Output: {}".format(outputFile))


            if outputFile == inputFile:
                self.logger.info("Overwriting file '{}'" .format(inputFile))

                backupFile = inputFile + ".bak"
                try:
                    os.rename(inputFile, backupFile)
                except Exception as e:
                    self.logger.warning((
                        "WARNING: File '{}' already exists!"
                    ).format(backupFile))
                    index = 1
                    while True:
                        try:
                            os.rename(inputFile, backupFile + str(index))
                            backupFile += str(index)
                            break
                        except Exception as e:
                            self.logger.warning((
                                "WARNING: File '{}' already exists!"
                            ).format(backupFile + str(index)))
                        index += 1

                in_queue.put((self, self.processfile, backupFile, outputFile, True))
                temp_files.append(backupFile)

            else:
                in_queue.put((self, self.processfile, inputFile, outputFile, False))


        in_queue.join()

        self.results = []
        for i in range(out_queue.qsize()):
            self.results.append(out_queue.get())


        for result in self.results:
            in_file, out_file, status = result
            if status:
                # Error
                self.logger.error((
                    "ERROR converting '{}': {}"
                ).format(in_file, status))
                errors = True

            else:
                if in_file in temp_files:
                    if self.noBackup:
                        self.logger.warning((
                            "Deleting file '{}'"
                        ).format(in_file))
                        os.remove(in_file)
                    else:
                        self.logger.info((
                            "Backup saved to '{}'"
                        ).format(in_file))

                self.logger.info((
                    "'{}' converted to '{}'"
                ).format(in_file, out_file))


        return not errors



    #TODO: add 'full_path' option?
    @classmethod
    def getfiles(
        cls,
        starting_path,
        extensions=None,
        recursive=True,
        ignored_subdirectories=None
    ):
        """Get the list of files contained in a directory.

        Specific file extensions can be specified.
        Recursive search can be done, and specific subdirectories to ignore
        can be specified.

        Parameters:
        starting_path: str
            Directory to look into
        extensions: list of str, optional
            List of file extensions (default: None)
        recursive: bool, optional
            Look in subdirectories (default: True)
        ignored_subdirectories: list of str, optional
            Subdirectories to ignore (default: None)

        Returns:
        list of str: Found files
        """

        if not os.path.isdir(starting_path):
            return []

        # Get input files
        files = []
        for item in os.listdir(starting_path):
            full_path = os.path.join(starting_path, item)

            if os.path.isfile(full_path):
                if extensions:
                    # Check if file of 1 of the specified file extensions
                    for extension in extensions:
                        file_extension = os.path.splitext(item)[1]
                        if file_extension.lower() == "." + extension.lower():
                            break
                    else:
                        continue

                # Keep file
                #files.append(full_path)
                files.append(item)

            elif os.path.isdir(full_path):
                if recursive:
                    # Skipping specified subdirectories
                    if (
                        ignored_subdirectories
                        and item in ignored_subdirectories
                    ):
                        continue

                    sub_files = cls.getfiles(
                        full_path,
                        extensions,
                        recursive,
                        ignored_subdirectories
                    )
                    #files += sub_files
                    for sub_file in sub_files:
                        files.append(os.path.join(item, sub_file))

        return files


    @staticmethod
    def checkpath(path, check_existence=True):
        """Check the validity of a path.

        Parameters:
        path: str
            Path to check
        check_existence: bool, optional
            Check if the directory exists (default: True)

        Raises:
        NotADirectoryError
            If the path exists but is not a directory
        FileNotFoundError
            If the path doesn't exist
        """

        if os.path.isdir(path):
            return

        if os.path.exists(path):
            raise OSError(
                errno.ENOTDIR, os.strerror(errno.ENOTDIR), path
            )

        if check_existence:
            raise OSError(
                errno.ENOENT, os.strerror(errno.ENOENT), path
            )


    def __checkfile(self, file_path, extensions=None):
        """Check the validity of a file.

        Parameters:
        file_path: str
            Full path of the file
        extensions: list of str, optional
            List of file extensions (default: None)

        Raises:
        FileNotFoundError
            If the path does not exist (or is not a file)
        ValueError
            If the file extension is not amongst expected ones
        """

        if not os.path.isfile(file_path):
            raise OSError(
                errno.ENOENT, os.strerror(errno.ENOENT), file_path
            )

        if extensions:
            # Check if file is of 1 of the specified extensions
            for extension in extensions:
                file_extension = os.path.splitext(file_path)[1]
                if file_extension.lower() == "." + extension.lower():
                    break
            else:
                #TODO: type of exception?
                raise ValueError((
                    "Invalid extension for '{}' (supported extensions: {})"
                ).format(file_path, extensions))

        self.checkfile(file_path)


    @staticmethod
    def __splitvalues(values):
        # To handle both ',' and ';'|':' depending on OS
        if sys.platform == "win32":
            list_separator = ";"
        else:
            list_separator = ":"

        split_values = []
        for value in values:
            temp_value = value.replace(list_separator, ",")
            if "," in temp_value:
                temp = temp_value.split(",")
                split_values.extend(temp)
            else:
                split_values.append(value)

        return split_values


    def add_arguments(self, optional_arguments, required_arguments):
        """Add arguments to be parsed.

        Can be overridden to add script specific arguments.
        """
        pass


    def checkinputs(self):
        """Add checks to be made on inputs.

        Can be overridden to add script specific checks.
        """
        pass


    def checkfile(self, file_path):
        """Additional checks on the validity of a file.

        The function can be overridden if specific operations/checks
        are desired on the files.

        Parameters:
        file_path: str
            Full path of the file

        Raises:
        Any raised exception should be an 'OSError'.
        """
        pass


    def preprocess(self):
        """Executed before starting the main process.

        Can be overridden to add script specific operations.
        If fails (returns False), the script will stop
        and the process will not be executed.

        Returns:
        bool: status (success or failure)
        """
        return True


    def postprocess(self, status):
        """Executed after finishing the main process.

        The function is executed regardless of the process success.
        Can be overridden to add script specific operations.

        Parameters:
        status: bool
            Return status of the main process

        Returns:
        bool: status (success or failure)
        """
        return True


    # TODO: rename function?
    def init(self):
        """Set initial values to script variables and arguments.

        The function is executed in the '__init__' function,
        and is thus executed before arguùents parsing+checking.
        It is thus a good place to declare/initialise variables
        that will be used as arguments.
        """
        pass


    def processfile(self, srcFilePath, destFilePath):
        """Core process executed on each file.

        Must be overridden.
        """
        raise NotImplementedError("Method not implemented!")
