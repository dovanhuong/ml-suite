#!/usr/bin/env python
#
# // SPDX-License-Identifier: BSD-3-CLAUSE
#
# (C) Copyright 2018, Xilinx, Inc.
#
import os, re, sys
import subprocess

class TestConfig():
  __test__ = False

  def __init__(self, models=[], bitwidths=[], kernel_types=[], exec_modes=[]):
    self._models = models
    self._bitwidths = bitwidths
    self._kernel_types = kernel_types
    self._exec_modes = exec_modes

def run_test(testName, cmdStr, verify, platform):
  if platform is not None:
    cmdStr += " -p " + platform

  _testSrcPath = "%s/../../examples/deployment_modes" \
    % os.path.dirname(os.path.realpath(__file__))

  cwd = os.getcwd()
  os.chdir(_testSrcPath)

  success = False
  output = ""
  try:
    print "\nRunning [%s] ...\nCommand: %s" % (testName, cmdStr)
    process = subprocess.Popen(cmdStr,
      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    # replace '' with b'' for Python 3 below
    for line in iter(process.stdout.readline, ''):
      output += line
      sys.stdout.write(line)
    process.stdout.close()
    ret = process.wait()
    if ret:
      raise subprocess.CalledProcessError(ret, cmdStr)
    success = True
  except subprocess.CalledProcessError as e:
    if e.output:
      print e.output

  os.chdir(cwd)

  if success:
    if verify:
      verify(output)

    print "\nPASS"
  else:
    raise Exception(output)

  return output

class OutputVerifier():
  def __init__(self, expected):
    self._expected = expected

  def get_predictions(self, output):
    predictions = {}
    lines = output.split("\n")
    for l in lines:
      match = re.search(r'^([0-9.]+)\s+\"(.+)\"', l)
      if not match:
        continue
      predictions[match.group(2)] = match.group(1)

    return predictions

  def verify_predictions(self, output):
    pred = self.get_predictions(output)
    golden = self.get_predictions(self._expected)

    diffs = {key: (val, pred[key] if key in pred else None) for key, val in golden.items() if key not in pred or pred[key] != val}
    if diffs:
      raise ValueError('mis-prediction ERROR!!\n{}'.format('\n'.join(['Expected {} predicted {} for label \"{}\"'.format(val[0], val[1], key) for key, val in diffs.items()])))

  def get_accuracy(self, output):
    lines = output.split("\n")
    top1 = 0
    top5 = 0
    for l in lines:
      match = re.search(r'^Average accuracy.+Top-1: ([0-9.]+).+Top-5: ([0-9.]+)', l)
      if not match:
        continue
      top1 = match.group(1)
      top5 = match.group(2)

    return (float(top1), float(top5))

  def verify_accuracy(self, output):
    check = self.get_accuracy(output)
    golden = self.get_accuracy(self._expected)

    thresh = 5.
    if golden[0] - check[0] > thresh \
      or golden[1] - check[1] > thresh:
      raise ValueError, "\nExpected:\n%s" % self._expected
