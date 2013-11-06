#!/usr/bin/env python
# encoding: utf-8

import sys,os

import pathtastictools

# MAIN

model=pathtastictools.SBMLmodel("example.xml")

for r in model.reactions:
	for p in r.products:
		print p.id