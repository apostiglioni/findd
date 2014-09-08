import unittest
import tempfile
import shutil
import logging
from os import path, makedirs, urandom, chmod, symlink, remove

from sys import version_info
if version_info >= (3,4):
    from unittest.mock import patch
else:
    from mock import patch

from dupscanner import connection_factory, repository, DupScanner

logging.basicConfig(level='DEBUG')


class DataGenerator():
    def __init__(self):
        pass

    _path_prefix = 'dupscanner_test-'

    def __enter__(self):
        self.root_path = tempfile.mkdtemp(prefix=self._path_prefix)
        self.files = []

        return self

    def __exit__(self, type, value, tb):
        assert path.basename(self.root_path).startswith(self._path_prefix)

        logging.debug('removing temp test directory: {}'.format(self.root_path))
        shutil.rmtree(self.root_path)

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

        assert not path.exists(abs_dest_fullname), \
            'Test data will overwrite existing file: {}'.format(abs_dest_fullname)

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
        abs_dest_fullname = path.join(abs_dest_dirname, dest_basename)

        assert not path.exists(abs_dest_fullname), \
            'Test data will overwrite existing file: {}'.format(abs_dest_fullname)

        symlink(self.abs_path(origin), abs_dest_fullname)

        logging.debug("{} linked to {}".format(origin, abs_dest_fullname))

        self.files.append(abs_dest_fullname)

        return abs_dest_fullname


class TestRepository(unittest.TestCase):

    def test_happy_path(self):
        with DataGenerator() as test_scenario:
            duplicates_expected = test_scenario.create_duplicates(
                ('1/a.data', '2/a.data', '3/a.data', '4/a.data'), size=4097)  # 4097 = block size + 1
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
            uniques_expected.add(test_scenario.create_file('1/e.data', size=4097))
            uniques_expected.add(test_scenario.create_file('4/x.data', size=2048, readable=False))
            uniques_expected.add(test_scenario.create_file('4/xx.data', size=2048, readable=False))

            connection_string = ':memory:'
            with connection_factory(connection_string) as conn, repository(conn) as repo:
                DupScanner(repo).scan((test_scenario.root_path,))

                duplicates_found = {abspath for hash, size, fullname, path, abspath in repo.findBy_duplicate_hash()}

                duplicates_missing = duplicates_expected - duplicates_found
                assert not duplicates_missing, 'Expected duplicate elements were not found: {}'.format(duplicates_missing)

                duplicates_unexpected = duplicates_found - duplicates_expected
                assert not duplicates_unexpected, 'Unexpected duplicate elements were found: {}'.format(duplicates_unexpected)

                assert duplicates_expected == duplicates_found, \
                    'Expected duplicate set doesn\'t match found set. \n Expected: {}\n Found: {}'.format(duplicates_expected, duplicates_found)

                uniques_found = {abspath for hash, size, fullname, path, abspath in repo.findBy_unique_hash()}

                uniques_missing = uniques_expected - uniques_found
                assert not uniques_missing, 'Expected unique elements were not found: {}'.format(
                    uniques_missing)

                uniques_unexpected = uniques_found - uniques_expected
                assert not uniques_unexpected, 'Unexpected unique elements were found: {}'.format(
                    uniques_unexpected)

                assert uniques_expected == uniques_found, \
                    'Expected unique set doesn\'t match found set. \n Expected: {}\n Found: {}'.format(uniques_expected, uniques_found)

    def test_happy_path_with_nested_dirs(self):
        with DataGenerator() as test_scenario:
            duplicates_expected = test_scenario.create_duplicates(
                ('1/a.data', '2/a.data', '3/a.data', '4/a.data'), size=4097)  # 4097 = block size + 1
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
            uniques_expected.add(test_scenario.create_file('1/e.data', size=4097))
            uniques_expected.add(test_scenario.create_file('4/x.data', size=2048, readable=False))
            uniques_expected.add(test_scenario.create_file('4/xx.data', size=2048, readable=False))

            connection_string = ':memory:'
            with connection_factory(connection_string) as conn, repository(conn) as repo:
                DupScanner(repo).scan((test_scenario.root_path,  test_scenario.abs_path('1/')))

                duplicates_found = {abspath for hash, size, fullname, path, abspath in repo.findBy_duplicate_hash()}

                duplicates_missing = duplicates_expected - duplicates_found
                assert not duplicates_missing, 'Expected duplicate elements were not found: {}'.format(
                    duplicates_missing)

                duplicates_unexpected = duplicates_found - duplicates_expected
                assert not duplicates_unexpected, 'Unexpected duplicate elements were found: {}'.format(
                    duplicates_unexpected)

                assert duplicates_expected == duplicates_found, 'Expected duplicate set doesn\'t match found set. \n Expected: {}\n Found: {}'.format(
                    duplicates_expected, duplicates_found)

                uniques_found = {abspath for hash, size, fullname, path, abspath in repo.findBy_unique_hash()}

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
            uniques_expected.add(test_scenario.create_file('3/e.data', size=4069))
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

                duplicates_found = {fullname for hash, size, fullname, path, abspath in repo.findBy_duplicate_hash()}

                duplicates_missing = duplicates_expected - duplicates_found
                assert not duplicates_missing, 'Expected duplicate elements were not found: {}'.format(
                    duplicates_missing)

                duplicates_unexpected = duplicates_found - duplicates_expected
                assert not duplicates_unexpected, 'Unexpected duplicate elements were found: {}'.format(
                    duplicates_unexpected)

                assert duplicates_expected == duplicates_found, \
                       'Expected duplicate set doesn\'t match found set. \n Expected: {}\n Found: {}'.format(duplicates_expected, duplicates_found)

                uniques_found = {fullname for hash, size, fullname,
                                 path, abspath in repo.findBy_unique_hash()}

                uniques_missing = uniques_expected - uniques_found
                assert not uniques_missing, 'Expected unique elements were not found: {}'.format(
                    uniques_missing)

                uniques_unexpected = uniques_found - uniques_expected
                assert not uniques_unexpected, 'Unexpected unique elements were found: {}'.format(
                    uniques_unexpected)

                assert uniques_expected == uniques_found, \
                       'Expected unique set doesn\'t match found set. \n Expected: {}\n Found: {}'.format(uniques_expected, uniques_found)

                links_unexpected = (uniques_found | duplicates_found) & ignored_links

                assert not links_unexpected, 'Unexpected links found'

    def test_false_duplicates_in_path(self):
        with DataGenerator() as test_scenario:
            duplicates_expected = set()

            uniques_expected = set()
            uniques_expected.add(test_scenario.create_file('1/a.data', size=4097))
            uniques_expected.add(test_scenario.create_file('1/b.data', size=4096))
            uniques_expected.add(test_scenario.create_file('1/c.data', size=512))
            uniques_expected.add(test_scenario.create_file('1/e.data', size=4069))
            uniques_expected.add(test_scenario.create_file('1/x.data', size=2048, readable=False))
            uniques_expected.add(test_scenario.create_file('1/xx.data', size=2048, readable=False))

            # TODO: This behavior is not consistent with don't follow links
            test_scenario.symlink('1/', 'links/1')
            uniques_expected.add(path.join(test_scenario.root_path, 'links/1/a.data'))
            uniques_expected.add(path.join(test_scenario.root_path, 'links/1/b.data'))
            uniques_expected.add(path.join(test_scenario.root_path, 'links/1/c.data'))
            uniques_expected.add(path.join(test_scenario.root_path, 'links/1/e.data'))
            uniques_expected.add(path.join(test_scenario.root_path, 'links/1/x.data'))
            uniques_expected.add(path.join(test_scenario.root_path, 'links/1/xx.data'))

            connection_string = ':memory:'
            with connection_factory(connection_string) as conn, repository(conn) as repo:
                # DupScanner(repo).scan((test_scenario.root_path,))
                DupScanner(repo).scan((
                    path.join(test_scenario.root_path, '1'),
                    path.join(test_scenario.root_path, 'links'),
                ))

                duplicates_found = {fullname for hash, size, fullname, path, abspath in repo.findBy_duplicate_hash()}

                duplicates_missing = duplicates_expected - duplicates_found
                assert not duplicates_missing, 'Expected duplicate elements were not found: {}'.format(
                    duplicates_missing)

                duplicates_unexpected = duplicates_found - duplicates_expected
                assert not duplicates_unexpected, 'Unexpected duplicate elements were found: {}'.format(
                    duplicates_unexpected)

                assert duplicates_expected == duplicates_found, \
                       'Expected duplicate set doesn\'t match found set. \n Expected: {}\n Found: {}'.format(duplicates_expected, duplicates_found)

                uniques_found = {fullname for hash, size, fullname,
                                 path, abspath in repo.findBy_unique_hash()}

                uniques_missing = uniques_expected - uniques_found
                assert not uniques_missing, 'Expected unique elements were not found: {}'.format(
                    uniques_missing)

                uniques_unexpected = uniques_found - uniques_expected
                assert not uniques_unexpected, 'Unexpected unique elements were found: {}'.format(
                    uniques_unexpected)

                assert uniques_expected == uniques_found, \
                       'Expected unique set doesn\'t match found set. \n Expected: {}\n Found: {}'.format(uniques_expected, uniques_found)


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

# escenario por probar: link a un link

# escenario por probar link en un directorio parte del path

# escenario scan devuelve 1 si hay warnings

# escenario scan(a, lnk-a) ==> dos directorios, el segundo es un link del primero

