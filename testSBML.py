#!/usr/bin/env python
# encoding: utf-8

import sys,os

import basicSBML

# MAIN

model=basicSBML.SBMLmodel("example.xml")

for r in model.reactions:
	for p in r.products:
		print p.compartment.size

