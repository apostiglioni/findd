#! /usr/bin/env python
#python 2 compatibility
from __future__ import print_function

import sys
import argparse
import logging

from dupscanner import connection_factory, repository, DupScanner

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
#  parser.add_argument("-u", "--unique", help="Find unique files", action="store_const", const='unique', dest='action')
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
    dupscanner = DupScanner(repo)
#    command = { 'unique': dupscanner.find_unique, 'duplicates': dupscanner.find_duplicates }

#    results = command[action](path)
    results = dupscanner.find_unique(path) if args.unique else dupscanner.find_duplicates(path)

    if args.execute_script: exec_script(args.execute_script, output_file, results, conn, repo)
    elif args.evaluate: func = exec_command(args.evaluate, output_file, results)
    elif args.pretty_print: func = pretty_print(results, output_file)
    else: plain_print(template, results, output_file)

if '__main__' == __name__:
  main()