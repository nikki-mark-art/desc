#!/usr/bin/env python3

import os
import stat
import sys
import subprocess
import hashlib
import logging
import sqlite3
import re
import time
import argparse


class Colors:
    """ Terminal colors for a nicer output """

    BOLD = "\033[1m"
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


class Settings:
    """ Place all global objects here, including settings et al """

    list_command = 'ls'
    list_command_opts = '-lah'
    custom_format_begin = ' => ' + Colors.BLUE
    custom_format_end = Colors.ENDC
    app_home = os.path.realpath(os.environ['HOME'] + os.path.sep +
                                '.desc' + os.path.sep)
    expired_symbol = Colors.BOLD + 'x ' + Colors.ENDC

    db_uri = app_home + os.path.sep + '.db'  # where to store the DB
    cursor = None  # internal use, overwritten
    db_conn = None  # also internal

    def __getattr__(self, attribute_name):
        if attribute_name in self:
            return attribute_name
        else:
            raise AttributeError


def get_hash(file_path):
    """ Returns a SHA (UTF-8 bytes) hash of the {inode, device} pair. """

    if not file_path:
        raise Exception(LocalMessages.NO_PATH)

    file_path = os.path.realpath(file_path)
    file_inode = os.stat(file_path).st_ino
    file_device = os.stat(file_path).st_dev

    sha1_hash = hashlib.sha1()
    hashable = '{}:{}'.format(file_inode, file_device).encode('UTF-8')
    sha1_hash.update(hashable)

    #logging.debug(file_path, "'s hash is", sha1_hash.hexdigest())

    return sha1_hash.hexdigest()


def get_existing(file_path, file_hash=None):
    """ Check if this hash is already in the db """

    if not (file_hash or file_path):
        raise Exception(LocalMessages.NEITHER_HASH_PATH_PROVIDED)

    elif file_hash:
        logging.debug("Looking for record by hash {0}".format(file_hash))

        sql = '''
                SELECT
                    D.path, D.ctime, D.desc
                FROM
                    desc D
                WHERE
                    (hash = ?)'''

        rec = Settings.cursor.execute(sql, [file_hash])

        try:
            if rec.fetchone():
                # Already have a record
                print(LocalMessages.RECORD_EXISTS)
                rem = Settings.cursor.execute(
                    '''DELETE FROM desc WHERE (hash = ?)''', [file_hash])

        except:
            print(LocalMessages.COULDNT_REMOVE_EXISTING)

    else:
        logging.debug("Looking for record by path {0}".format(file_path))

        # Obtain the hash of the file in question
        file_hash = get_hash(file_path)
        logging.debug("--> hash is {}".format(file_hash))

        sql = '''SELECT
                    D.hash AS hash,
                    D.desc AS description,
                    D.path AS path,
                    D.ctime AS ctime
                 FROM
                    desc D
                 WHERE
                    (D.hash = ?)'''

        rec = Settings.cursor.execute(sql, [file_hash])

        return rec.fetchone()


def dict_factory(cursor, row):
    """ A helper for retriving column names from DB as per
    https://docs.python.org/3.4/library/sqlite3.html#sqlite3.Connection.row_factory
    """

    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class FileRecord(object):
    """ Local "workhorse" class for managing the metadata """

    def _store_record(self, file_path, file_hash, file_desc):
        """ Local method that organizes a dictionary to be stored """

        # See if we need to remove/update an existing entry
        get_existing(file_path, file_hash)
        file_ctime = os.stat(file_path).st_ctime

        print("Adding a new record...", end=' ')

        # Insert a row of data
        Settings.cursor.execute(
            '''INSERT INTO desc VALUES (?, ?, ?, ?)''',
            [file_hash, file_path, file_desc, file_ctime])

        try:
            # Save the changes
            Settings.db_conn.commit()
            print("Done.")
        except:
            print(LocalMessages.COULDNT_ADD)

    def __init__(self, file_path, file_desc):

        # Elementary preflight checkups
        if not file_path:
            raise Exception(LocalMessages.NO_FILENAME)

        if not os.path.exists(file_path):
            raise Exception(LocalMessages.NO_PATH)

        if not file_desc:
            raise Exception(LocalMessages.NO_FILE_DESC)

        self.file_path = file_path
        self.file_desc = file_desc

        # Get a SGit hash of the file
        self.file_hash = get_hash(file_path)

        logging.debug("{0}, {1}, {2}".format(self.file_path,
                                             self.file_hash, self.file_desc))

        # Pass on to saving the record
        self._store_record(self.file_path, self.file_hash, self.file_desc)


class LocalMessages(set):
    """ All predefined errors, warnings, etc. """

    NO_PATH = u"No such file or directory."
    NO_FILENAME = u"Can't create a record for file without a path."
    BAD_PARAMS = u"Incorrect parameter(s) passed in."
    NEITHER_HASH_PATH_PROVIDED = u"Neither hash nor path provided."
    COULDNT_REMOVE_EXISTING = u"Couldn't remove an existing record."
    RECORD_EXISTS = u"Such hash is already stored. Will rewrite."
    COULDNT_ADD = u"Couldn't add a new hash."
    COULDNT_SHUT_DB = u"Couldn't close the database connection when leaving."

    def __getattr__(self, error_name):
        if error_name in self:
            return error_name
        else:
            raise AttributeError


def init_logs():
    """ Initiates local message logging """

    logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', filename=sys.argv[0] +
                        '.log', filemode='w+', level=logging.DEBUG)

    #logging.basicConfig(level=logging.DEBUG)
    logging.info("-" * 8 + " Logging started " + "-" * 8)
    logging.debug("Self-test: this is a debug level messsage")
    logging.info("Self-test: this is an informational message")
    logging.warning("Self-test: this is a warning")
    logging.error("Self-test: this is an error")


def init_db():
    """ Initialize the database """

    logging.debug("Initiating database procedures")
    db = Settings.db_conn = sqlite3.connect(Settings.db_uri)
    db.row_factory = dict_factory  # For column name access
    Settings.cursor = Settings.db_conn.cursor()

    # Create table if not exists
    db.execute('''CREATE TABLE IF NOT EXISTS desc
                     (hash text, path text, desc blob, ctime text)''')
    db.commit()
    logging.debug("Set up the DB file location")


def shutdown_db():
    """ Clean up after DB is done """

    try:
        Settings.db_conn.close()
    except:
        print(LocalMessages.COULDNT_SHUT_DB)


def print_usage(error):
    """ Prints usage guide and possible error explanation """

    if error:
        try:
            print(error)
        except:
            print("Unspecified error occured. Please read the help file for \
                  more details.")
        finally:
            raise SystemExit

    usage = ''' Blah blah
    yada yada
    '''

    print(usage)


def store_description(file_name, file_desc=''):
    """ Stores the descrption for file_name """

    file_path = os.path.realpath(file_name)
    FileRecord(file_path, file_desc)


def print_descriptions(hashes, folder=os.getcwd(), stdin=None):
    """ Display descr. for the current folder """

    if not (hashes or folder):
        raise Exception("Need both hashes list and the folder to operate on")

    logging.debug("Printing listing of the {} folder".format(folder))

    folder = os.path.realpath(folder)
    hashes_parsed = 0
    hashes_len = len(hashes)

    if stdin:
        # Read STDIN
        output = stdin.buffer.readlines()

    else:
        # Start listing using system command
        proc = subprocess.Popen(
            [Settings.list_command, Settings.list_command_opts, folder],
            shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        out, err = proc.communicate()
        output = out.decode('UTF-8').split(os.linesep)

    # In list mode print only visible files
    # (i.e. in the default `ls` mode)
    for line in output:

        if stdin:
            line = line.decode('UTF-8').strip(os.linesep)

        # Whether to print the output from `ls`
        matched = False

        # This logging below might fail and produce a
        # large traceback log
        #logging.debug("Hashes parsed: ", hashes_parsed)

        # Save cycles on comparing
        if hashes_parsed >= hashes_len:
            print(line)
            continue

        # Parse each line of `ls` output
        # to see if our file is in there
        for existing_item in hashes:

            # Mini-guard against None's in hashes
            if not existing_item:
                continue

            logging.debug("Looking for matching hash {} in {}".format(
                existing_item['hash'], line))

            # Extract the file name from the input stream by assuming that
            # the sought file is the last item in line, right after the last
            # set of whitespace chars.
            nameMatched = re.search(u'^(.*[\s\t]+)?(.*)$', line, re.U)

            # Get the last or the only group
            candidate = nameMatched.groups()[-1:][0]

            if nameMatched and candidate in os.listdir(folder):
                logging.debug("Regex match:" + candidate)
                file_name = candidate.strip()
                file_path = folder + os.sep + file_name
                file_ctime = os.stat(file_path).st_ctime
                file_hash = get_hash(file_path)

                if file_hash == existing_item['hash']:
                    matched = True

            # Add description to the line
            if matched:

                expired = False
                expired_mark = Settings.expired_symbol

                # Behave differently if ctime has changed
                if int(float(file_ctime)) == int(float(existing_item['ctime'])):
                    expired_mark = ''
                else:
                    expired = True

                if expired and not Settings.cli_args.show_expired:
                    print(line)
                else:
                    print('{0:s}{1:s}{2:s}{3:s}{4:s}'.format(
                        line, Settings.custom_format_begin, expired_mark,
                        existing_item['description'], Settings.custom_format_end))

                hashes_parsed += 1
                break

        # Don't add description to the line
        # (pass thru, essentially)
        if not matched:
            print(line)


def get_descriptions(folder=os.getcwd()):
    """ Returns a dictionary with filename as the key
        and description as its value """

    hashes = []
    folder = os.path.realpath(folder)

    # Files in the folder
    dir_files = os.listdir(folder)

    # Get description for each file in the dir
    for file_name in dir_files:
        file_path = ''.join([folder, os.path.sep, file_name])
        logging.debug("get_descriptions(): Looking at " + file_path)
        fetched_record = get_existing(file_path)

        if fetched_record:
            hashes.append(fetched_record)

    return hashes


def init_argparser():
    """ Parse command line options """

    parser = argparse.ArgumentParser(description='Describe files')
    group = parser.add_mutually_exclusive_group()

    # File or folder path
    group.add_argument('path', default='.', nargs='?',
                        help="File or folder path to operate on")

    # A list of files (e.g. from a glob)
    group.add_argument('-l', '--list', dest='file_list', nargs='+',
                        help="List of files to operate on")

    # Message / description
    parser.add_argument('-m', '--message', default=None, nargs='?',
                        help="Text to desribe the file or folder")

    # Read from STDIN
    parser.add_argument('-', '--stdin', action='store_true',
                        help="Read from standard input")

    # Show stale records
    parser.add_argument('-e', '--expired',
                        dest='show_expired', default=False, action='store_true',
                        help="show expired items (check ctime)")

    # Parse
    args = parser.parse_args()
    
    return args


def leave():
    """ Plausible point of leaving """

    # (A)lways (B)e (C)losing
    shutdown_db()

    sys.exit(0)


def main():
    """ Entry point to the program """

    init_logs()
    init_db()

    # Parse command line args
    args = init_argparser()

    # Convert params to strings from lists
    args.path = ''.join(args.path)

    # Export to Settings for access in the other funcs
    Settings.cli_args = args

    logging.debug("Command line arguments: {}".format(args))

    if args.stdin:
        # Process STDIN
        description = get_descriptions(folder=args.path)
        print_descriptions(description, folder=args.path, stdin=sys.stdin)
        leave()

    # Empty messages won't get here
    if args.message:
        
        # Run adding new records
        if args.file_list:
            for path in args.file_list:
                store_description(path, args.message)
        else:
            store_description(args.path, args.message)

        leave()

    print_descriptions(get_descriptions(folder=args.path), folder=args.path)

    leave()

# Entry point
if '__main__' == __name__:
    main()

""" Notes

*   Although the word "description" appears in the source code, it should be
    treated as a metadata term and, of course, the message next to the file
    name in the list doesn't have to describe the nature of it.



Options described

------------------------------------------------------------------------------

        -m     Message / description

               Example: $ desc -l *.bak -m "My back-ups"

               Adds description "My back-ups" (without the qoutes) to all the
               files specified by the glob `*.bak`

------------------------------------------------------------------------------

        -      Read from stdin

               Example: $ ls -la /tmp | desc /tmp -

               Will try to parse the output of the `ls -la` command relatively
               to the /tmp folder specified by `/tmp`. If folder is not
               provided with `-` which reads from stdin then the program will
               emit an error

------------------------------------------------------------------------------

"""
