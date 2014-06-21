#!/usr/bin/env python3

import os
import sys
import subprocess
import hashlib
import logging
import sqlite3
import re


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

    db_uri = app_home + os.path.sep + '.db'  # where to store the DB
    cursor = None  # internal use, overwritten
    db_conn = None  # also internal

    def __getattr__(self, attribute_name):
        if attribute_name in self:
            return attribute_name
        else:
            raise AttributeError


def get_existing(file_path, file_hash=None):
    """ Check if this hash is already in the db """

    if not (file_hash or file_path):
        raise Exception(LocalMessages.NEITHER_HASH_PATH_PROVIDED)

    elif file_hash:
        logging.debug("Looking for record with hash {0}".format(file_hash))

        rec = Settings.cursor.execute('''SELECT path FROM desc
                  WHERE (hash = ?)''', [file_hash])
        try:
            if rec.fetchone():
                # Already have a record
                print(LocalMessages.RECORD_EXISTS)
                rem = Settings.cursor.execute('''DELETE FROM desc
                      WHERE (hash = ?)''', [file_hash])

        except:
            print(LocalMessages.COULDNT_REMOVE_EXISTING)

    else:
        logging.debug("Looking for record by path {0}".format(file_path))

        sql = '''SELECT
                    D.hash AS hash, D.desc  AS description, D.path as path
                 FROM
                    desc D
                 WHERE
                    (path = ?)'''

        rec = Settings.cursor.execute(sql, [file_path])

        return rec.fetchone()


def dict_factory(cursor, row):
    """ A helper for retriving column names from DB as per
        https://docs.python.org/3.4/library/sqlite3.html#sqlite3.Connection.row_factory """

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

        print("Adding a new record...", end=' ')

        # Insert a row of data
        Settings.cursor.execute('''INSERT INTO desc
            VALUES (?, ?, ?, strftime('%s', 'now'))''', [file_hash, file_path, file_desc])

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

        # Get a SHA512 hash of the path
        self.file_hash = hashlib.sha512(file_path.encode('UTF-8')).hexdigest()

        logging.debug("{0}, {1}, {2}".format(self.file_path, self.file_hash,
                                             self.file_desc))

        # Pass on to saving the record
        self._store_record(self.file_path, self.file_hash, self.file_desc)


class LocalMessages(set):
    """ All predefined errors, warnings, etc. """

    NO_PATH = u"No such file or directory. A typo?"
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
                        datefmt='%m/%d/%Y %I:%M:%S %p', filename=sys.argv[0] + '.log',
                        filemode='w+', level=logging.DEBUG)
    
    # logging.basicConfig(level=logging.DEBUG)
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
                     (hash text, path text, desc blob, added date)''')
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

    list_command = Settings.list_command
    folder = os.path.realpath(folder)
    hashes_parsed = 0
    hashes_len = len(hashes)
    output = None

    if (stdin):
        # Read STDIN
        output = stdin.buffer.readlines()
        
    else:
        # Start listing using system command
        proc = subprocess.Popen([Settings.list_command, Settings.list_command_opts, folder],
                                shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        out, err = proc.communicate()
        output = out.decode('UTF-8').split(os.linesep)

    # In list mode print only visible files
    # (i.e. in the default `ls` mode)
    for line in output:

        if (stdin):
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
        for item in hashes:

            # Mini-guard against None's in hashes
            if not item:
                continue

            # File name from the DB/hashes
            file_name = item['path'].split(os.path.sep)[-1:][0]

            logging.debug("Looking for {} in {}".format(file_name, line))

            # Check the output line against our file name
            # Warning: the regex is a little cheesy... What about Unicode?
            matched = re.search(u'[\s]+{}$'.format(file_name),
                                line, re.U)

            # Add descriptin to the line
            if matched:
                print('{0:s}{2:s}{1:s}{3:s}'.format(line, item['description'],
                    Settings.custom_format_begin, Settings.custom_format_end))
                hashes_parsed += 1
                break
        
        # Don't add description to the line
        # (pass thru, essentially)  
        if not matched:
            print(line)



def get_descriptions(folder=os.getcwd()):
    """ Returns a dictionary with filename as the key
        and its description as value """

    hashes = []
    folder = os.path.realpath(folder)

    # Files in the folder
    dir_files = os.listdir(folder)

    # Get description for each file in the dir
    for file_name in dir_files:
        file_path = ''.join([folder, os.path.sep, file_name])
        logging.debug("Looking at: " + file_path)
        fetched_record = get_existing(file_path)
        if fetched_record:
            hashes.append(fetched_record)

    return hashes


def main():
    """ Entry point to the program """

    init_logs()
    init_db()

    if 3 == len(sys.argv):

        if '-' == sys.argv[1] and sys.argv[2]:
            # Process STDIN
            print_descriptions(
                get_descriptions(folder=sys.argv[2]), folder=sys.argv[2], stdin=sys.stdin)
        else:
            # Run adding new records
            store_description(sys.argv[1], sys.argv[2])

    elif 2 == len(sys.argv):
        print_descriptions(
            get_descriptions(folder=sys.argv[1]), folder=sys.argv[1])

    else:
        print_descriptions(get_descriptions())
        
        ## Show help
        #print_usage(LocalMessages.BAD_PARAMS)

    # (A)lways (B)e (C)losing
    shutdown_db()

# Entry point
if '__main__' == __name__:
    main()

