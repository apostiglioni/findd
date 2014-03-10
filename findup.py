import os
import hashlib
import csv
import argparse
import locale
from datetime import datetime
import sqlite3
import logging
import sys

def log_time(f):
    def decorator (*args):
        start_time = datetime.now()

        ret = f(*args)

        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logging.info('%s elapsed time: %s', f.__name__, elapsed_time)

        return ret
    return decorator

def _get_files(path):
    for root, dirs, files in os.walk(path):
        for name in files:
            file_fullname = os.path.join(root, name)
            file_realpath = os.path.realpath(file_fullname)
            file_abspath  = os.path.abspath(file_fullname)
            file_size = _get_size(file_fullname)

            # This condition is assumed always true, and the queries may return
            # incorrect values if it evers turns out to be false
            assert file_realpath == file_abspath or os.path.islink(file_fullname), \
            "%s is not %s and %s is not a symlink" % (file_realpath, file_abspath, file_fullname) 
            
            yield (file_fullname, file_size, file_abspath, file_realpath)

def _get_size(file_fullname):
    try: return os.path.getsize(file_fullname)	#TODO: Investigate why some files aren't accesible
    except:
        logging.warning("Can't calculate the size of %s", file_fullname)
        return None

def _md5_checksum(file_path):
    try:
        #m = crc32_adapter()
        m = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(m.block_size * 64), b''): # b'' == EOF
                m.update(chunk)
                pass
        hash_value = m.hexdigest()

        return hash_value
    except:
        logging.warning("Can't calculate the md5 checksum of %s", file_path)
        return None

@log_time
def write_csv(data, csv_filename):
    with open(csv_filename, "w", encoding=locale.getpreferredencoding()) as csv_file:
        csv_writer = csv.writer(csv_file,delimiter='\t')
        for key, file_list in data.items():
	        for file in file_list:
                    #TODO: Investigate why the output file has blank lines
	            csv_writer.writerow([key[0], key[1], file])
        
class crc32_adapter():
    block_size = 32

    def __init__(self):
        import zlib
        import base64
        self.accumulated = b''
    
    def update(self, data):
        if self.accumulated == b'':
            self.accumulated = zlib.adler32(data)
        else:
            self.accumulated = zlib.adler32(data, self.accumulated)

    def hexdigest(self):
        return str(self.accumulated)

class connection_factory():
    def __init__(self, con_string):
        self.con_str = con_string
        self.connection = None

    def __enter__(self):
        self.connection = sqlite3.connect(self.con_str)
        self.connection.row_factory = sqlite3.Row

        return self.connection
    def __exit__(self, type, value, tb):
        if tb is None:
            self.connection.commit()
            self.connection.close()
            self.connection = None
        else:
            self.connection.rollback()
            self.connection.close()
            self.connection = None
        return False

class repository():
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        self.create_schema()
        return self

    def __exit__(self, type, value, tb):
        self.connection = None

    def create_schema(self):
        self.connection.execute('create table files(fullname TEXT PRIMARY KEY, size INT, hash CHAR(32), path TEXT, abspath, TEXT, realpath TEXT)')

    def add_file(self, name, size, path, abspath, realpath):
        self.connection.execute('insert into files(fullname, size, path, abspath, realpath) values(?,?,?,?,?)', (name, size, path, abspath, realpath))


    def iterateOn_duplicate_hash(self):
        for duplicate in self.connection.execute('''
                select hash, size, fullname, path, abspath, realpath
                from files f
                where f.realpath = f.abspath 
                and exists (
                    select 1
                    from files f2
                    where f.size = f2.size and f.hash = f2.hash 
                    group by f2.size, f2.hash
                    having count(*) > 1
                )
                order by hash, size, fullname
            '''):
            yield duplicate

    def iterateOn_unique_hash(self):
        for unique in self.connection.execute('''
                select hash, size, fullname, path, abspath, realpath
                from files f
                where  f.abspath = f.realpath and (
                      f.hash is null or
                      f.size is null or
                      exists (
                        select 1
                        from files f2
                        where f.size = f2.size and f.hash = f2.hash
                        group by size, hash
                        having count(*) = 1
                      )
                )
                order by f.hash, f.size
            '''):
            yield unique
        
    def findBy_duplicate_size(self):
        return self.connection.execute(
                '''
                    select size, fullname
                    from files f
                    where f.realpath = f.abspath 
                    and exists (
                        select 1
                        from files f2
                        where f.size = f2.size
                        group by f2.size
                        having count(*) > 1
                    )
                    order by f.hash, f.size
                ''')

    def update_file(self, name, hash):
        self.connection.execute('update files set hash = ? where fullname=?', (hash, name))
        

class Findd():
    def __init__(self, repository, get_files=_get_files, hash_function=_md5_checksum):
        self.repository = repository
        self.get_files = get_files
        self.hash_function = hash_function

    @log_time
    def insert_files(self, path):
        for file_name, file_size, file_abspath, file_realpath in self.get_files(path):
            logging.debug(
              'inserting filename %s in path %s with abspath %s and realpath %s and size %s', 
              file_name, path, file_abspath, file_realpath, str(file_size)
            )
            self.repository.add_file(name=file_name, size=file_size, path=path, abspath=file_abspath, realpath=file_realpath)

    @log_time
    def update_checksum(self):
        for bysize_size, bysize_name in self.repository.findBy_duplicate_size():
            hash_value = self.hash_function(bysize_name)
            logging.debug('updating hash %s for file %s', hash_value, bysize_name)
            self.repository.update_file(bysize_name, hash=hash_value)
            
    @log_time
    def scan(self, directory_list):
        for directory in directory_list:
            logging.info('start scan of directory %s', directory)
            self.insert_files(directory)
            self.update_checksum()

    @log_time
    def find_duplicates(self, path_list):
        return self._find(path_list, self.repository.iterateOn_duplicate_hash)

    @log_time
    def find_unique(self, path_list):
        return self._find(path_list, self.repository.iterateOn_unique_hash)

    def _find(self, path_list, search_method):
        self.scan(path_list)

        for data in search_method():
            yield data

class file(object):
    """Factory for creating file object types

    Instances of FileType are typically passed as type= arguments to the
    ArgumentParser add_argument() method.

    Keyword Arguments:
        - mode -- A string indicating how the file is to be opened. Accepts the
            same values as the builtin open() function.
        - bufsize -- The file's desired buffer size. Accepts the same values as
            the builtin open() function.
    """

    def __init__(self, mode='w', buffering=-1, encoding='UTF-8'):
        self._mode = mode
        self._buffering = buffering
        self._encoding = encoding

    def __call__(self, string):
        # the special argument "-" means sys.std{in,out}
        if string == '-':
            if 'r' in self._mode:
                return sys.stdin
            elif 'w' in self._mode:
                return sys.stdout
            else:
                msg = ('argument "-" with mode %r') % self._mode
                raise ValueError(msg)

        # all other arguments are used as file names
        try:
            return open(string, mode=self._mode, buffering=self._buffering, encoding=self._encoding)
        except IOError as e:
            message = _("can't open '%s': %s")
            raise ArgumentTypeError(message % (string, e))

    def __repr__(self):
        args = self._mode, self._buffering, self._encoding, self._mode
        args_str = ', '.join(repr(arg) for arg in args if arg != -1)
        return '%s(%s)' % (type(self).__name__, args_str)


def pretty_print(results, output_file):
    prev_hash = None
    prev_size = None

    for hash, size, filename, path, abspath, realpath in results:
            if prev_hash != hash or prev_size != size:
                print(hash, size, sep='\t', file=output_file)
            print('\t%s' % filename, file=output_file)
            prev_hash = hash
            prev_size = size

def plain_print(template, results, output_file):
    from string import Template
    for row in results:
        ctx = dict(zip(row.keys(), row))
        print(Template(template).substitute(ctx))

def exec_command(command, output_file, results):
    for hash, size, filename, path in results:
        exec(command)

def exec_script(script, output_file, results, conn, repo):
    with open(script) as f:
        command = f.read()
    exec(command)

def main():
    args_parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser()
    parser.set_defaults(action='duplicates')
    parser.add_argument("path", help="Path where to look for duplicates", nargs='+')
    parser.add_argument("-d", "--database", help="Stores a temporary SQLite database in a file", default=":memory:")
    parser.add_argument("-lf", "--log-format", help="Logging format", default='%(message)s')
    parser.add_argument("-l", "--log", help="File to output the log messages")
#    parser.add_argument("-u", "--unique", help="Find unique files", action="store_const", const='unique', dest='action')
    parser.add_argument("-u", "--unique", help="Find unique files", action="store_true")
    parser.add_argument("-o", "--output-file", help="Output file (default: stdout)", default='-', type=file('w', encoding='UTF-8'))
    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "-t", 
        "--template", 
        help="""Output template. Variables ${hash}, ${size}, ${fullname}, ${path}, ${abspath}, ${realpath} 
             will be replaced with the actual values""", 
        default="${hash}\t${size}\t${fullname}"
    )
    g.add_argument(
        "-e",
        "--evaluate",
        help="""For each result, evaluate the given python code to process the output.
                Variables hash, size, filename and output_file will be bounded to the appropiate values"""
    )
    g.add_argument(
        "-x",
        "--execute-script",
        help="""Executes the given python script to process the results.
                Variables results and output_file will be bounded to an iterator and the appropiate output stream"""
    )
    g.add_argument(
        "-p",
        "--pretty-print",
        action="store_true",
        help="Groups the results by hash and file size and displays a pretty output"
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        help="Verbosity level (default: WARN)",
        default='WARN',
        choices=['DEBUG','INFO','WARN','ERROR','CRITICAL'],
        type=lambda level: level.upper()
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.verbosity,
        format=args.log_format,
        filename=args.log
    )

    connection_string = args.database
    path = args.path
    action = args.action
    template = args.template

    with connection_factory(connection_string) as conn, repository(conn) as repo, args.output_file as output_file:
        findd = Findd(repo)
#        command = { 'unique': findd.find_unique, 'duplicates': findd.find_duplicates }

#        results = command[action](path)
        results = findd.find_unique(path) if args.unique else findd.find_duplicates(path)

        if args.execute_script: exec_script(args.execute_script, output_file, results, conn, repo)
        elif args.evaluate: func = exec_command(args.evaluate, output_file, results)
        elif args.pretty_print: func = pretty_print(results, output_file)
        else: plain_print(template, results, output_file)

if '__main__' == __name__:
    main()
