#!/usr/bin/env python3

''' Test desc.py with unittest

To run tests:
> python3 test_desc_py.py


Tests that need to be added:
----------------------------
[-] Test other shells / terminals
[-] Test Unicode file names
[-] Test moving files around
[-] Test copying files
[-] Test files with the same inode on different devices
[-] Test description of a single item
[-] Test description for "." and ".." aliases
[-] Test that colored output doesn't mess with the rest of the colors
[-] Test that a file name has been updated in the database when file is
    determined to be moved
[-] Test globs in file names to get description
'''

import os
import sys
import unittest

# Import from parent dir
sys.path.insert(0, os.path.realpath(os.pardir))
import desc


class TestDescPy(unittest.TestCase):

    def setUp(self):
        ''' Get all the default settings '''
        self.settings = desc.Settings()
        self.test_description = "This is a sample description"
        self.test_path = os.path.realpath(__file__)

        # print('# Settings variables during setup:')
        # print('app_home={}\ndb_uri={}\n'.format(
        #     settings.app_home, settings.db_uri))

    def test_database_init(self):
        '''
        Should create a sqlite3 database file specified by db_uri
        when none exists
        '''

        print("\nWarning! This test may destroy your existent data "
              "like an existing database.\n")

        response = input("Type \"YES\" in capitals to go on: ")

        if (response != 'YES'):
            print("Got red light. Stopping here. Tests will show as failed.\n")
            sys.exit(0)

        os.unlink(self.settings.db_uri)  # removes the existing db to help
                                         # tests stay independent

        desc.init_db()
        file_exists = os.path.isfile(self.settings.db_uri)
        self.assertEqual(file_exists, True)

    def test_get_existing_hash(self):
        '''
        Should return a record if it exists in the database and return None
        if the hash is not found therein. Tests the `get_existing(file_hash)`
        '''

        test_hash = 'abcdefg0123456789'
        existing = desc.get_existing(file_hash=test_hash, file_path=None)
        self.assertEqual(existing, None)

    def test_get_existing_path(self):
        '''
        Should return a record if it exists in the database and return None
        if the path is not found therein. Tests the `get_existing(file_path)`
        '''

        # A pretty much illegal path should definitely be not in the db
        test_path = '/illegal/file/path/<test>!@#$%'
        existing = desc.get_existing(file_hash=None, file_path=test_path)
        self.assertEqual(existing, None)

    def test_store_description(self):
        '''
        Should store the file path and description to the database. This will
        add a description to this file which contains this test
        '''

        desc.store_description(self.test_path, self.test_description)
        # No assertion here, must raise an exception in the
        # original method if fails

    def test_get_descriptions(self):
        '''
        Should display the same path, description and SHA512 hash that was
        added in the beginning of the test
        '''
        test_path = os.getcwd()

        # First, add a new record akin to test_store_description()
        desc.store_description(self.test_path, self.test_description)

        from hashlib import sha512
        hashes = desc.get_descriptions(test_path)

        # Hashes must not be empty at this point
        self.assertNotEqual(hashes, [])

        # Tests description
        self.assertEqual(hashes[0]['description'], self.test_description)

        # Tests path
        self.assertEqual(hashes[0]['path'], os.path.realpath(__file__))

        # Tests the file path hash
        file_hash = sha512(os.path.realpath(__file__).encode('UTF-8'))
        self.assertEqual(hashes[0]['hash'], file_hash.hexdigest())


if __name__ == '__main__':
    unittest.main(verbosity=0)
