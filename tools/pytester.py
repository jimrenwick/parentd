#!/usr/bin/python

import argparse
import logging
import os
import sys
import unittest

def main(flags):
  sys.path.extend(flags.TEST_DIR)
  loader = unittest.TestLoader()
  tests = []
  if flags.TESTS:
    logging.info('Loading just tests: %s', flags.TESTS)
    tests = loader.loadTestsFromNames(flags.TESTS)
  else:
    logging.info('Searching %s for tests.', flags.TEST_DIR)
    tests = loader.discover(os.getcwd(), '*_test.py')
  runner = unittest.TextTestRunner(verbosity=2)
  result = runner.run(tests)
  logging.info('Test result: %s', result)
  if result.errors:
    sys.exit(1)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Run a test suite')
  parser.add_argument('--TESTS', nargs='*',
                      help='The fully qualified names of the tests to run.')
  parser.add_argument('--TEST_DIR', nargs=1, help=(
      'The directory to search for test files matching *_test.py pattern.'))
  parser.add_argument('--logtostderr', action='store_true',
                      help='Print logging to stderr')
  args = parser.parse_args()
  if args.logtostderr:
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)-1s %(asctime)-15s] %(message)s')
  main(args)
      
  
