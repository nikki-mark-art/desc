#!/usr/bin/env python3

'''

Test desc.py with unittest

To run tests:
> python3 test_desc_py.py

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
        settings = self.settings = desc.Settings()
        print('# Settings variables during setup:')
        print('app_home={}\ndb_uri={}\n'.format(
            settings.app_home, settings.db_uri))

        print('''Warning! These tests may destroy your existent data like
            and existing database.\n''')

        response = input("Type \"YES\" in capitals to go on: ")

        if (response != 'YES'):
            print("Got red light. Stopping here. Tests will show as failed.\n")
            sys.exit(0)

    def test_database_init(self):
        '''
        Should create a sqlite3 database file specified by db_uri
        when none exists
        '''
        os.unlink(self.settings.db_uri)
        desc.init_db()
        file_exists = os.path.isfile(self.settings.db_uri)
        self.assertEqual(file_exists, True)


if __name__ == '__main__':
    unittest.main()
