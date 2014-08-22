import unittest
import tempfile
import shutil
import logging
from os import path, makedirs, urandom, chmod, symlink, remove
from unittest.mock import patch

from dupscanner import connection_factory, repository, DupScanner

# logging.basicConfig(level='DEBUG')


class DataGenerator():
    _path_prefix = 'dupscanner_test-'

    def __enter__(self):
        self.root_path = tempfile.mkdtemp(prefix=self._path_prefix)
        self.files = []

        return self

    def __exit__(self, type, value, tb):
        assert path.basename(self.root_path).startswith(self._path_prefix)

        logging.debug('removing temp test directory: {}'.format(self.root_path))
        # shutil.rmtree(self.root_path)

        self.files = None

    def _mkdirs(self, relative_path):
        abspath = self.abs_path(relative_path)
        if not path.exists(abspath):
            makedirs(abspath)

        return abspath

    def abs_path(self, relative_path):
        return path.abspath(path.join(self.root_path, relative_path))

    def create_file(self, file_path, size=4097, readable=True):
        abs_dirname = self._mkdirs(path.dirname(file_path))

        abs_fullname = path.join(abs_dirname, path.basename(file_path))

        assert not path.exists(
            abs_fullname), 'Test data will overwrite existing file: {}'.format(abs_fullname)
        with open(abs_fullname, 'wb') as f:
            f.write(urandom(size))

        if not readable:
            chmod(abs_fullname, 0o200)

        logging.debug("created{}temporary file {}".format(
            ' read only ' if not readable else ' ', abs_fullname))

        return abs_fullname

    def _generate_file(self, origin, dest, generator):
        dest_basename = path.basename(dest)
        dest_dirname = path.dirname(dest)

        abs_dest_dirname = self._mkdirs(dest_dirname)
        abs_dest_fullname = abs_dest_dirname + '/' + dest_basename

        assert not path.exists(
            abs_dest_fullname), 'Test data will overwrite existing file: {}'.format(abs_dest_fullname)
        generator(self.abs_path(origin), abs_dest_dirname)

        logging.debug("{} {} to {}".format(origin, 'linked' if path.islink(
            abs_dest_fullname) else 'copied', abs_dest_fullname))

        self.files.append(abs_dest_fullname)

        return abs_dest_fullname

    def copy_file(self, origin, dest):
        dest_basename = path.basename(dest)
        dest_dirname = path.dirname(dest)

        abs_dest_dirname = self._mkdirs(dest_dirname)
        abs_dest_fullname = abs_dest_dirname + '/' + dest_basename

        assert not path.exists(
            abs_dest_fullname), 'Test data will overwrite existing file: {}'.format(abs_dest_fullname)
        shutil.copy(self.abs_path(origin), abs_dest_dirname)

        logging.debug("{} copied to {}".format(origin, abs_dest_fullname))

        self.files.append(abs_dest_fullname)

        return abs_dest_fullname

    def create_duplicates(self, paths, size=4097):
        origin = paths[0]
        origin_fullname = self.create_file(origin, size)
        l = [origin_fullname]

        for clone_dirname in paths[1:]:
            clone_fullname = self.copy_file(origin, clone_dirname)
            l.append(clone_fullname)

        return set(l)

    def symlink(self, origin, dest):
        dest_basename = path.basename(dest)
        dest_dirname = path.dirname(dest)

        abs_dest_dirname = self._mkdirs(dest_dirname)
        abs_dest_fullname = abs_dest_dirname + '/' + dest_basename

        assert not path.exists(
            abs_dest_fullname), 'Test data will overwrite existing file: {}'.format(abs_dest_fullname)

        symlink(self.abs_path(origin), abs_dest_fullname)

        logging.debug("{} linked to {}".format(origin, abs_dest_fullname))

        self.files.append(abs_dest_fullname)

        return abs_dest_fullname


class TestRepository(unittest.TestCase):

    def test_happy_path(self):
        with DataGenerator() as test_scenario:
            duplicates_expected = test_scenario.create_duplicates(
                ('1/a.data', '2/a.data', '3/a.data', '4/a.data'), size=4097)  # 4096 = block size + 1
            duplicates_expected |= test_scenario.create_duplicates(
                ('2/aa.data', '4/aa.data'), size=4096)
            duplicates_expected |= test_scenario.create_duplicates(
                ('1/aaa.data', '4/aaa.data'), size=1024)
            duplicates_expected |= test_scenario.create_duplicates(
                ('1/aaaa.data', '3/aaaa.data'), size=0)

            uniques_expected = set()
            uniques_expected.add(test_scenario.create_file('1/b.data', size=4097))
            uniques_expected.add(test_scenario.create_file('2/c.data', size=4096))
            uniques_expected.add(test_scenario.create_file('3/d.data', size=512))
            uniques_expected.add(test_scenario.create_file('4/x.data', size=2048, readable=False))
            uniques_expected.add(test_scenario.create_file('4/xx.data', size=2048, readable=False))

            connection_string = ':memory:'
            with connection_factory(connection_string) as conn, repository(conn) as repo:
                DupScanner(repo).scan((test_scenario.root_path,))

                duplicates_found = {
                    abspath for hash, size, fullname, path, abspath in repo.findBy_duplicate_hash()}

                duplicates_missing = duplicates_expected - duplicates_found
                assert not duplicates_missing, 'Expected duplicate elements were not found: {}'.format(
                    duplicates_missing)

                duplicates_unexpected = duplicates_found - duplicates_expected
                assert not duplicates_unexpected, 'Unexpected duplicate elements were found: {}'.format(
                    duplicates_unexpected)

                assert duplicates_expected == duplicates_found, 'Expected duplicate set doesn\'t match found set. \n Expected: {}\n Found: {}'.format(
                    duplicates_expected, duplicates_found)

                uniques_found = {
                    abspath for hash, size, fullname, path, abspath in repo.findBy_unique_hash()}

                uniques_missing = uniques_expected - uniques_found
                assert not uniques_missing, 'Expected unique elements were not found: {}'.format(
                    uniques_missing)

                uniques_unexpected = uniques_found - uniques_expected
                assert not uniques_unexpected, 'Unexpected unique elements were found: {}'.format(
                    uniques_unexpected)

                assert uniques_expected == uniques_found, 'Expected unique set doesn\'t match found set. \n Expected: {}\n Found: {}'.format(
                    uniques_expected, uniques_found)

    def test_dont_follow_links(self):
        with DataGenerator() as test_scenario:
            duplicates_expected = set()

            uniques_expected = set()
            uniques_expected.add(test_scenario.create_file('1/a.data', size=4097))
            uniques_expected.add(test_scenario.create_file('2/b.data', size=4096))
            uniques_expected.add(test_scenario.create_file('3/c.data', size=512))
            uniques_expected.add(test_scenario.create_file('4/x.data', size=2048, readable=False))
            uniques_expected.add(test_scenario.create_file('4/xx.data', size=2048, readable=False))

            ignored_links = set()
            ignored_links.add(test_scenario.symlink('1/a.data', '2/lnk-a.data'))
            ignored_links.add(test_scenario.symlink('2/b.data', '1/lnk-b.data'))
            ignored_links.add(test_scenario.symlink('4/x.data', '4/lnk-x.data'))
            ignored_links.add(test_scenario.symlink('4/xx.data', '4/lnk-xx.data'))

            connection_string = ':memory:'
            with connection_factory(connection_string) as conn, repository(conn) as repo:
                DupScanner(repo).scan((test_scenario.root_path,))

                duplicates_found = {
                    fullname for hash, size, fullname, path, abspath in repo.findBy_duplicate_hash()}

                duplicates_missing = duplicates_expected - duplicates_found
                assert not duplicates_missing, 'Expected duplicate elements were not found: {}'.format(
                    duplicates_missing)

                duplicates_unexpected = duplicates_found - duplicates_expected
                assert not duplicates_unexpected, 'Unexpected duplicate elements were found: {}'.format(
                    duplicates_unexpected)

                assert duplicates_expected == duplicates_found, 'Expected duplicate set doesn\'t match found set. \n Expected: {}\n Found: {}'.format(
                    duplicates_expected, duplicates_found)

                uniques_found = {fullname for hash, size, fullname,
                                 path, abspath in repo.findBy_unique_hash()}

                uniques_missing = uniques_expected - uniques_found
                assert not uniques_missing, 'Expected unique elements were not found: {}'.format(
                    uniques_missing)

                uniques_unexpected = uniques_found - uniques_expected
                assert not uniques_unexpected, 'Unexpected unique elements were found: {}'.format(
                    uniques_unexpected)

                assert uniques_expected == uniques_found, 'Expected unique set doesn\'t match found set. \n Expected: {}\n Found: {}'.format(
                    uniques_expected, uniques_found)

                links_unexpected = (uniques_found | duplicates_found) & ignored_links

                assert not links_unexpected, 'Unexpected links found'

    def test_delete_old(self):
        with DataGenerator() as test_scenario:
            test_scenario.create_duplicates(
                ('1/a.data', '2/a.data', '3/a.data', '4/a.data'), size=4097)  # 4097 = block size + 1

            connection_string = ':memory:'
            with connection_factory(connection_string) as conn, \
                    repository(conn) as repo, patch('os.remove') as mock_path:

                DupScanner(repo).scan((test_scenario.root_path,))

                f = test_scenario.abs_path('1/a.data')
                repo.delete_file(f)
                mock_path.assert_called_with(f)
                mock_path.reset_mock()

                f = test_scenario.abs_path('2/a.data')
                repo.delete_file(f)
                mock_path.assert_called_with(f)
                mock_path.reset_mock()

                f = test_scenario.abs_path('3/a.data')
                repo.delete_file(f)
                mock_path.assert_called_with(f)
                mock_path.reset_mock()

                try:
                    f = test_scenario.abs_path('4/a.data')
                    repo.delete_file(f)
                    assert False, "Should have raised an exception"
                except Exception as e:
                    f = test_scenario.abs_path('4/a.data')
                    expected = Exception(
                        "409 Can't delete a file without duplicates: {}".format(f))
                    assert repr(expected) == repr(e)

                assert not mock_path.called, 'File should have not been deleted'
                mock_path.reset_mock

    def test_delete(self):
        with DataGenerator() as test_scenario:
            duplicates = ('1/a.data', '2/a.data', '3/a.data', '4/a.data')
            test_scenario.create_duplicates(duplicates, size=10)

            connection_string = ':memory:'
            with connection_factory(connection_string) as conn, \
                    repository(conn) as repo, patch('os.remove') as mock_path:

                DupScanner(repo).scan((test_scenario.root_path,))

                for f in duplicates[:-1]:
                    deleteable = test_scenario.abs_path(f)
                    repo.delete_file(deleteable)
                    mock_path.assert_called_with(deleteable)
                    mock_path.reset_mock()

                try:
                    not_deleteable = test_scenario.abs_path(duplicates[-1])
                    repo.delete_file(not_deleteable)
                    assert False, 'Should have raised an exception'
                except Exception as e:
                    expected = Exception('409 Can\'t delete a file without duplicates: {}'.format(not_deleteable))
                    assert repr(expected) == repr(e)

                assert not mock_path.called, 'File should have not been deleted'
                mock_path.reset_mock

# with connection_factory(connection_string) as conn, repository(conn) as repo:
#   repo.connection.execute('INSERT INTO files(fullname, size, path, abspath, realpath) VALUES("test-data/.DS_Store",6148,"test-data","/Users/apostigl/code/findd/test-data/.DS_Store","/Users/apostigl/code/findd/test-data/.DS_Store")')
#   repo.connection.execute('INSERT INTO files(fullname, size, path, abspath, realpath) VALUES("test-data/1/bull-shark-closeup-underwater.adapt.470.1.jpg",9462,"test-data","/Users/apostigl/code/findd/test-data/1/bull-shark-closeup-underwater.adapt.470.1.jpg","/Users/apostigl/code/findd/test-data/1/bull-shark-closeup-underwater.adapt.470.1.jpg")')
#   repo.connection.execute('INSERT INTO files(fullname, size, path, abspath, realpath) VALUES("test-data/1/hammerhead-shark-swimming.adapt.470.1.jpg",7507,"test-data","/Users/apostigl/code/findd/test-data/1/hammerhead-shark-swimming.adapt.470.1.jpg","/Users/apostigl/code/findd/test-data/1/hammerhead-shark-swimming.adapt.470.1.jpg")')
#   repo.connection.execute('INSERT INTO files(fullname, size, path, abspath, realpath) VALUES("test-data/2/bull-shark-closeup-underwater.adapt.470.1.jpg",9462,"test-data","/Users/apostigl/code/findd/test-data/2/bull-shark-closeup-underwater.adapt.470.1.jpg","/Users/apostigl/code/findd/test-data/2/bull-shark-closeup-underwater.adapt.470.1.jpg")')
#   repo.connection.execute('INSERT INTO files(fullname, size, path, abspath, realpath) VALUES("test-data/2/symlink-hammerhead-shark-swimming.adapt.470.1.jpg",7507,"test-data","/Users/apostigl/code/findd/test-data/2/symlink-hammerhead-shark-swimming.adapt.470.1.jpg","/Users/apostigl/code/findd/test-data/1/hammerhead-shark-swimming.adapt.470.1.jpg")')
#   repo.connection.execute('INSERT INTO files(fullname, size, path, abspath, realpath) VALUES("test-data/3/bull-shark-closeup-underwater.adapt.470.1.jpg",9462,"test-data","/Users/apostigl/code/findd/test-data/3/bull-shark-closeup-underwater.adapt.470.1.jpg","/Users/apostigl/code/findd/test-data/3/bull-shark-closeup-underwater.adapt.470.1.jpg")')
#   repo.connection.execute('INSERT INTO files(fullname, size, path, abspath, realpath) VALUES("test-data/4/bull-shark-closeup-underwater.adapt.470.1.jpg",9462,"test-data","/Users/apostigl/code/findd/test-data/4/bull-shark-closeup-underwater.adapt.470.1.jpg","/Users/apostigl/code/findd/test-data/4/bull-shark-closeup-underwater.adapt.470.1.jpg")')

#   repo.connection.execute('update files set hash = "186d754a292b30a717e7907139215e91" where fullname="test-data/1/hammerhead-shark-swimming.adapt.470.1.jpg"')
#   repo.connection.execute('update files set hash = "dfcde38655be383161e613e989ec910b" where fullname="test-data/1/bull-shark-closeup-underwater.adapt.470.1.jpg"')
#   repo.connection.execute('update files set hash = "dfcde38655be383161e613e989ec910b" where fullname="test-data/2/bull-shark-closeup-underwater.adapt.470.1.jpg"')
#   repo.connection.execute('update files set hash = "dfcde38655be383161e613e989ec910b" where fullname="test-data/3/bull-shark-closeup-underwater.adapt.470.1.jpg"')
#   repo.connection.execute('update files set hash = "dfcde38655be383161e613e989ec910b" where fullname="test-data/4/bull-shark-closeup-underwater.adapt.470.1.jpg"')

    # for fullname, size, path, abspath, realpath in repo.connection.execute(
    #   'select fullname, size, path, abspath, realpath from files'
    # ):
    # print abspath  # fullname, size, path, abspath, realpath

    # print "----------------------------------------------------------------"

    # query =  'SELECT f.fullname, f.size, f.hash, f.path, f.abspath, f.realpath \
    #   FROM files AS f INNER JOIN files AS ff ON ff.hash = f.hash AND ff.size = f.size AND ff.abspath <> f.abspath \
    #   WHERE ff.abspath = ?'

    # abspath = '/Users/apostigl/code/findd/test-data/1/bull-shark-closeup-underwater.adapt.470.1.jpg'
    # for fullname, size, hash, path, abspath, realpath in repo.connection.execute(query, (abspath,)):
    #   print realpath

    # abspath = '/Users/apostigl/code/findd/test-data/2/symlink-hammerhead-shark-swimming.adapt.470.1.jpg'
    # repo.delete_file(abspath)

    # abspath = '/Users/apostigl/code/findd/test-data/1/hammerhead-shark-swimming.adapt.470.1.jpg'
    # repo.delete_file(abspath)
    # expect Exception("409 Can't delete a file without duplicates")

    # abspath = '/Users/apostigl/code/findd/test-data/1/bull-shark-closeup-underwater.adapt.470.1.jpg'
    # repo.delete_file(abspath)
    # expect os.remove(abspath)

    # abspath = '/Users/apostigl/code/findd/test-data/2/bull-shark-closeup-underwater.adapt.470.1.jpg'
    # repo.delete_file(abspath)
    # expect os.remove(abspath)

    # abspath = '/Users/apostigl/code/findd/test-data/3/bull-shark-closeup-underwater.adapt.470.1.jpg'
    # repo.delete_file(abspath)
    # expect os.remove(abspath)

    # abspath = '/Users/apostigl/code/findd/test-data/4/bull-shark-closeup-underwater.adapt.470.1.jpg'
    # repo.delete_file(abspath)
    # expect Exception("409 Can't delete a file without duplicates")

# escenario por probar: link a un link

# escenario por probar link en un directorio parte del path

# escenario scan devuelve 1 si hay warnings
