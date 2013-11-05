#!/usr/bin/env python
# encoding: utf-8

import sys,os

import pathtastictools

# MAIN

model=pathtastictools.SBMLmodel("example.xml")

print model.reacNodes
