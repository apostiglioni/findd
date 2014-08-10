import dupscanner
import unittest
import sqlite3

class TestRepository(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.repo =  dupscanner.repository(self.conn)
        self.repo.create_schema()

    def tearDown(self):
        self.conn.close()

    def test_iterateOn_duplicate_hash(self):
        duplicates = [
            #filename                   #size   #hash             #path        #abspath     #realpath
            ('duplicate-a',             1,      'duplicate',      'c:/path1',  'c:/path1',  'c:/path1'), 
            ('duplicate-b',             1,      'duplicate',      'c:/path2',  'c:/path2',  'c:/path2')
        ]
        unique = [
            ('same_size_diff_hash',     1,      'different hash', 'c:/path3',  'c:/path3',  'c:/path3'),
            ('same_size_no_hash',       1,      None,             'c:/path4',  'c:/path4',  'c:/path4'),
            ('diff_size_same_hash',     2,      'duplicate',      'c:/path5',  'c:/path5',  'c:/path5'),
            ('diff_size_diff_hash',     2,      'different hash', 'c:/path6',  'c:/path6',  'c:/path6'),
            ('diff_size_no_hash-a',     2,      None,             'c:/path7',  'c:/path7',  'c:/path7'),
            ('diff_size_no_hash-b',     2,      None,             'c:/path8',  'c:/path8',  'c:/path8'),
            ('unique_size_unique_hash', 3,      'unique hash',    'c:/path9',  'c:/path9',  'c:/path9'),
            ('unique_size_no_hash',     4,      None,             'c:/path10', 'c:/path10', 'c:/path10'),
            ('no_size_same_hash',       None,   'duplicate',      'c:/path11', 'c:/path11', 'c:/path11'),
            ('no_size_diff_hash-a',     None,   'different hash', 'c:/path12', 'c:/path12', 'c:/path12'),
            ('no_size_diff_hash-b',     None,   'different hash', 'c:/path13', 'c:/path13', 'c:/path13'),
            ('no_size_no_hash-a',       None,   None,             'c:/path14', 'c:/path14', 'c:/path14'),
            ('no_size_no_hash-b',       None,   None,             'c:/path15', 'c:/path15', 'c:/path15')
        ]
                        
        for d in duplicates + unique:
            self.repo.add_file(d[0],d[1],d[3],d[4],d[5])
            if d[2]: self.repo.update_file(d[0],d[2])
            
        values = [
            (filename, size, hash, path, abspath, realpath) 
            for hash, size, filename, path, abspath, realpath
            in self.repo.iterateOn_duplicate_hash()
        ]

        self.assertEqual(
            len(duplicates),
            len(values),
            "The number of results does not match what it is expected. {dup_num} duplicates were expected: {dup_data}".format(
                dup_num=len(duplicates), dup_data=values
            )
        )
        for v in values:
            self.assertIn(v, duplicates)

    def test_iterateOn_unique_hash(self):
        duplicates = [
            #filename                   #size   #hash             #path        #abspath     #realpath
            ('duplicate-a',             1,      'duplicate',      'c:/path1',  'c:/path1',  'c:/path1'), 
            ('duplicate-b',             1,      'duplicate',      'c:/path2',  'c:/path2',  'c:/path2')
        ]
        unique = [
            ('same_size_diff_hash',     1,      'different hash', 'c:/path3',  'c:/path3',  'c:/path3'),
            ('same_size_no_hash',       1,      None,             'c:/path4',  'c:/path4',  'c:/path4'),
            ('diff_size_same_hash',     2,      'duplicate',      'c:/path5',  'c:/path5',  'c:/path5'),
            ('diff_size_diff_hash',     2,      'different hash', 'c:/path6',  'c:/path6',  'c:/path6'),
            ('diff_size_no_hash-a',     2,      None,             'c:/path7',  'c:/path7',  'c:/path7'),
            ('diff_size_no_hash-b',     2,      None,             'c:/path8',  'c:/path8',  'c:/path8'),
            ('unique_size_unique_hash', 3,      'unique hash',    'c:/path9',  'c:/path9',  'c:/path9'),
            ('unique_size_no_hash',     4,      None,             'c:/path10', 'c:/path10', 'c:/path10'),
            ('no_size_same_hash',       None,   'duplicate',      'c:/path11', 'c:/path11', 'c:/path11'),
            ('no_size_diff_hash-a',     None,   'different hash', 'c:/path12', 'c:/path12', 'c:/path12'),
            ('no_size_diff_hash-b',     None,   'different hash', 'c:/path13', 'c:/path13', 'c:/path13'),
            ('no_size_no_hash-a',       None,   None,             'c:/path14', 'c:/path14', 'c:/path14'),
            ('no_size_no_hash-b',       None,   None,             'c:/path15', 'c:/path15', 'c:/path15')
        ]
                        
        for d in duplicates + unique:
            self.repo.add_file(d[0],d[1],d[3],d[4],d[5])
            if d[2]: self.repo.update_file(d[0],d[2])
            
        values = [
            (filename, size, hash, path, abspath, realpath) 
            for hash, size, filename, path, abspath, realpath 
            in self.repo.iterateOn_unique_hash()
        ]


        self.assertEqual(
            len(unique),
            len(values),
            "The number of results does not match what it is expected. {unq_num} unique were expected. Values: {unq_data}".format(
                unq_num=len(unique), unq_data=values
            )
        )
        for v in values:
            self.assertIn(v, unique)

    def test_find_duplicate_size(self):
        duplicates = [
            #filename                   #size   #hash             #path        #abspath     #realpath
            ('duplicate-a',             1,      'duplicate',      'c:/path1',  'c:/path1',  'c:/path1'),
            ('duplicate-b',             1,      'duplicate',      'c:/path2',  'c:/path2',  'c:/path2'),
            ('same_size_diff_hash',     1,      'different hash', 'c:/path3',  'c:/path3',  'c:/path3'),
            ('same_size_no_hash',       1,      None,             'c:/path4',  'c:/path4',  'c:/path4'),
            ('diff_size_same_hash',     2,      'duplicate',      'c:/path5',  'c:/path5',  'c:/path5'),
            ('diff_size_diff_hash',     2,      'different hash', 'c:/path6',  'c:/path6',  'c:/path6'),
            ('diff_size_no_hash-a',     2,      None,             'c:/path7',  'c:/path7',  'c:/path7'),
            ('diff_size_no_hash-b',     2,      None,             'c:/path8',  'c:/path8',  'c:/path8')
        ]
        unique = [
            ('no_size_same_hash',       None,   'duplicate',      'c:/path9',  'c:/path9',  'c:/path9'),
            ('no_size_diff_hash-a',     None,   'different hash', 'c:/path10', 'c:/path10', 'c:/path10'),
            ('no_size_diff_hash-b',     None,   'different hash', 'c:/path11', 'c:/path11', 'c:/path11'),
            ('no_size_no_hash-a',       None,   None,             'c:/path12', 'c:/path12', 'c:/path12'),
            ('no_size_no_hash-b',       None,   None,             'c:/path13', 'c:/path13', 'c:/path13'),
            ('unique_size_unique_hash', 3,      'unique hash',    'c:/path14', 'c:/path14', 'c:/path14'),
            ('unique_size_no_hash',     4,      None,             'c:/path15', 'c:/path15', 'c:/path15')
        ]
                        
        for d in duplicates + unique:
            self.repo.add_file(d[0],d[1],d[3],d[4],d[5])
            if d[2]: self.repo.update_file(d[0],d[2])
            
        values = [(filename, size) for size, filename in self.repo.findBy_duplicate_size()]


        self.assertEqual(
            len(duplicates),
            len(values),
            "The number of results does not match what it is expected. {unq_num} duplicates were expected. Values: {unq_data}".format(
                unq_num=len(duplicates), unq_data=values
            )
        )
        expected = [(dup[0], dup[1]) for dup in duplicates]

        for v in values:
            self.assertIn(v, expected)
        
class TestDupScanner(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.repo =  dupscanner.repository(self.conn)
        self.repo.create_schema()

    def tearDown(self):
        self.conn.close()

    def test_find_duplicates(self):
        duplicates = [
            #filename                   #size   #hash             #path        #abspath     #realpath
            ('duplicate-a',             1,      'duplicate',      'c:/path1',  'c:/path1',  'c:/path1'),
            ('duplicate-b',             1,      'duplicate',      'c:/path2',  'c:/path2',  'c:/path2')
        ]
        unique = [
            ('same_size_diff_hash',     1,      'different hash', 'c:/path3',  'c:/path3',  'c:/path3'),
            ('same_size_no_hash',       1,      None,             'c:/path4',  'c:/path4',  'c:/path4'),
            ('diff_size_same_hash',     2,      'duplicate',      'c:/path5',  'c:/path5',  'c:/path5'),
            ('diff_size_diff_hash',     2,      'different hash', 'c:/path6',  'c:/path6',  'c:/path6'),
            ('diff_size_no_hash-a',     2,      None,             'c:/path7',  'c:/path7',  'c:/path7'),
            ('diff_size_no_hash-b',     2,      None,             'c:/path8',  'c:/path8',  'c:/path8'),
            ('unique_size_unique_hash', 3,      'unique hash',    'c:/path9',  'c:/path9',  'c:/path9'),
            ('unique_size_no_hash',     4,      None,             'c:/path10', 'c:/path10', 'c:/path10'),
            ('no_size_same_hash',       None,   'duplicate',      'c:/path11', 'c:/path11', 'c:/path11'),
            ('no_size_diff_hash-a',     None,   'different hash', 'c:/path12', 'c:/path12', 'c:/path12'),
            ('no_size_diff_hash-b',     None,   'different hash', 'c:/path13', 'c:/path13', 'c:/path13'),
            ('no_size_no_hash-a',       None,   None,             'c:/path14', 'c:/path14', 'c:/path14'),
            ('no_size_no_hash-b',       None,   None,             'c:/path15', 'c:/path15', 'c:/path15'),
            ('linked',                  5,      'linked',         'c:/path16', 'c:/path16', 'c:/path16'),
            ('linked-2',                6,      'linked-2',       'c:/path17', 'c:/path17', 'c:/path17')
        ]
        links = [
            ('link',                    5,      'linked',         'c:/path18', 'c:/path18', 'c:/path16'),
            ('link-2-1',                6,      'linked-2',       'c:/path19', 'c:/path19', 'c:/path17'),
            ('link-2-2',                6,      'linked-2',       'c:/path20', 'c:/path20', 'c:/path17')
        ]

        def get_files(_path):
            f = (
                (name, size, abspath, realpath) 
                for name, size, hash, path, abspath, realpath 
                in duplicates + unique + links
                if path == _path
            )
            return f

        def hash_function(fname):
            d = {filename: hash for filename, size, hash, path, abspath, realpath in duplicates + unique + links}
            return d[fname]

        scanner =  dupscanner.DupScanner(self.repo, get_files=get_files, hash_function=hash_function)

        import logging
        logging.basicConfig(level=logging.DEBUG)
            
        values = [
            (filename, size, hash, path, abspath, realpath)
            for hash, size, filename, path, abspath, realpath
            in scanner.find_duplicates([item[3] for item in duplicates + unique + links])
        ]

        self.assertEqual(
            len(duplicates),
            len(values),
            """The number of results does not match what it is expected. 
            {dup_num} duplicates were expected. {dup_data} was found""".format(
                dup_num=len(duplicates), dup_data=values
            )
        )
        for v in values:
            self.assertIn(v, duplicates)

    def test_find_unique(self):
        duplicates = [
            #filename                   #size   #hash             #path        #abspath     #realpath
            ('duplicate-a',             1,      'duplicate',      'c:/path1',  'c:/path1',  'c:/path1'),
            ('duplicate-b',             1,      'duplicate',      'c:/path2',  'c:/path2',  'c:/path2')
        ]
        unique = [
            ('same_size_diff_hash',     1,      'different hash', 'c:/path3',  'c:/path3',  'c:/path3'),
            ('same_size_no_hash',       1,      None,             'c:/path4',  'c:/path4',  'c:/path4'),
            ('diff_size_same_hash',     2,      'duplicate',      'c:/path5',  'c:/path5',  'c:/path5'),
            ('diff_size_diff_hash',     2,      'different hash', 'c:/path6',  'c:/path6',  'c:/path6'),
            ('diff_size_no_hash-a',     2,      None,             'c:/path7',  'c:/path7',  'c:/path7'),
            ('diff_size_no_hash-b',     2,      None,             'c:/path8',  'c:/path8',  'c:/path8'),
            ('unique_size_unique_hash', 3,      'unique hash',    'c:/path9',  'c:/path9',  'c:/path9'),
            ('unique_size_no_hash',     4,      None,             'c:/path10', 'c:/path10', 'c:/path10'),
            ('no_size_same_hash',       None,   'duplicate',      'c:/path11', 'c:/path11', 'c:/path11'),
            ('no_size_diff_hash-a',     None,   'different hash', 'c:/path12', 'c:/path12', 'c:/path12'),
            ('no_size_diff_hash-b',     None,   'different hash', 'c:/path13', 'c:/path13', 'c:/path13'),
            ('no_size_no_hash-a',       None,   None,             'c:/path14', 'c:/path14', 'c:/path14'),
            ('no_size_no_hash-b',       None,   None,             'c:/path15', 'c:/path15', 'c:/path15'),
            ('linked',                  5,      'linked',         'c:/path16', 'c:/path16', 'c:/path16'),
            ('linked-2',                6,      'linked-2',       'c:/path17', 'c:/path17', 'c:/path17')
        ]
        links = [
            ('link',                    5,      'linked',         'c:/path18', 'c:/path18', 'c:/path16'),
            ('link-2-1',                6,      'linked-2',       'c:/path19', 'c:/path19', 'c:/path17'),
            ('link-2-2',                6,      'linked-2',       'c:/path20', 'c:/path20', 'c:/path17')
        ]

        expected = [
            #filename                   #size   #hash             #path        #abspath     #realpath
            ('same_size_diff_hash',     1,      'different hash', 'c:/path3',  'c:/path3',  'c:/path3'),
            ('same_size_no_hash',       1,      None,             'c:/path4',  'c:/path4',  'c:/path4'),
            ('diff_size_same_hash',     2,      'duplicate',      'c:/path5',  'c:/path5',  'c:/path5'),
            ('diff_size_diff_hash',     2,      'different hash', 'c:/path6',  'c:/path6',  'c:/path6'),
            ('diff_size_no_hash-a',     2,      None,             'c:/path7',  'c:/path7',  'c:/path7'),
            ('diff_size_no_hash-b',     2,      None,             'c:/path8',  'c:/path8',  'c:/path8'),
            # Files with unique size should not have the hash calculated:
            ('unique_size_unique_hash', 3,      None,             'c:/path9',  'c:/path9',  'c:/path9'),
            ('unique_size_no_hash',     4,      None,             'c:/path10', 'c:/path10', 'c:/path10'),
            ('no_size_same_hash',       None,   None,             'c:/path11', 'c:/path11', 'c:/path11'),
            ('no_size_diff_hash-a',     None,   None,             'c:/path12', 'c:/path12', 'c:/path12'),
            ('no_size_diff_hash-b',     None,   None,             'c:/path13', 'c:/path13', 'c:/path13'),
            ('no_size_no_hash-a',       None,   None,             'c:/path14', 'c:/path14', 'c:/path14'),
            ('no_size_no_hash-b',       None,   None,             'c:/path15', 'c:/path15', 'c:/path15'),
            ('linked',                  5,      None,             'c:/path16', 'c:/path16', 'c:/path16'),
            ('linked-2',                6,      None,             'c:/path17', 'c:/path17', 'c:/path17')
        ]


        def get_files(_path):
            f = (
                (name, size, abspath, realpath) 
                for name, size, hash, path, abspath, realpath 
                in duplicates + unique 
                if path == _path
            )
            return f

        def hash_function(fname):
            d = {filename: hash for filename, size, hash, path, abspath, realpath in duplicates + unique}
            return d[fname]

        scanner =  dupscanner.DupScanner(self.repo,get_files=get_files, hash_function=hash_function)
            
        values = [
            (filename, size, hash, path, abspath, realpath)
            for hash, size, filename, path, abspath, realpath
            in scanner.find_unique(
                [item[3] for item in duplicates + unique]
            )
        ]

        self.assertEqual(
            len(expected),
            len(values),
            "The number of results does not match what it is expected. {dup_num} uniques were expected: {dup_data}".format(
                dup_num=len(expected), dup_data=values
            )
        )
        for v in values:
            self.assertIn(v, expected)

