import os
import hashlib
import sqlite3
import logging
from logtime import log_time

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
    # Returning None to treat this files as unique
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
    # Returning None to treat this files as unique
    return None

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

