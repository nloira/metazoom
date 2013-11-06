#!/usr/bin/env python
# encoding: utf-8
"""
basic parsing and sotring of metabolic models in SBML.py

Created by Nicolas Loira on 2013-11-06.
nloira@gmail.com
"""

import sys
import os
from xml.etree.ElementTree import *
from collections import defaultdict

# Yes, a Global
URI = None


def log(m):
	print >>sys.stderr, m

class Compartment():
	def __init__(self, compartmentElement):
		global URI

		self.element = compartmentElement
		self.id = compartmentElement.get("id")
		self.name = compartmentElement.get("name", self.id)
		self.size = int( compartmentElement.get("size", "1") )


class Species():
	def __init__(self, speciesElement, id2compartments):
		global URI

		self.element = speciesElement
		self.id = speciesElement.get("id")
		self.name = speciesElement.get("name", self.id)
		self.compartmentID = speciesElement.get("compartment", None)
		self.compartment = id2compartments[self.compartmentID]


class Reaction():
	def __init__(self, reactionElement, id2species):
		global URI

		self.id = reactionElement.get("id")
		self.name = reactionElement.get("name", None)
		self.reversible = bool(reactionElement.get("reversible","False"))

		reactantIDs = [sr.get('species') for sr in reactionElement.findall("{%s}listOfReactants/{%s}speciesReference" % (URI, URI)) ]
		productIDs = [sr.get('species') for sr in reactionElement.findall("{%s}listOfProducts/{%s}speciesReference" % (URI, URI)) ]

		self.reactants = [ id2species[id] for id in reactantIDs ]
		self.products = [ id2species[id] for id in productIDs ]


class SBMLmodel():
	def __init__(self, filename=None):
		if filename:
			self.parseXML(filename)
			

	def parseXML(self, modelFile):
		global URI

		assert modelFile
		
		if modelFile=="-":
			modelfd=sys.stdin
		else:
			modelfd=open(modelFile)

		# parse file
		result = parse(modelfd)
		root=result.getroot()
		self.xmlTree=result
		self.root=root
		self.URI,self.tag= root.tag[1:].split("}",1)
		assert self.URI, "URI was not set correctly."
		URI=self.URI

		# shortcut for list of reaction nodes
		self.reacNodes = root.findall("*/{%s}listOfReactions/{%s}reaction" % (self.URI,self.URI))
		self.speciesNodes=root.findall("*/{%s}listOfSpecies/{%s}species" % (self.URI, self.URI))
		self.compNodes=root.findall("*/{%s}listOfCompartments/{%s}compartment" % (self.URI, self.URI))


		# build compartment, species and reaction objects

		self.compartments = [Compartment(cn) for cn in self.compNodes]
		id2compartments = dict( [ (c.id, c) for c in self.compartments])

		self.species = [Species(sn, id2compartments) for sn in self.speciesNodes]
		id2species = dict( [ (s.id, s) for s in self.species])

		self.reactions=[Reaction(r, id2species) for r in self.reacNodes]
		id2reactions = dict( [ (r.id, r) for r in self.reactions])

		# remember dictionaries
		self.id2compartments = id2compartments
		self.id2species = id2species
		self.id2reactions = id2reactions


		# map of all parents (useful for removing nodes)
		self.parentMap = dict((c, p) for p in root.getiterator() for c in p)

	def write(self, outFD):
		#self.xmlTree.write(outFD)

		# COBRA doesn't like the extra namespaces added by ElementTree,
		# so we'll parse the output
		assert self.root is not None
		xmlstr=tostring(self.root)
		
		cleanxml=xmlstr		
		#cleanxml=re.sub("<ns\d+:", "<", xmlstr)
		# cleanxml=re.sub("</ns\d+:", "</", cleanxml)
		
		
		print '<?xml version="1.0" encoding="UTF-8"?>'
		print cleanxml
	


	def getGeneAssociations(self, reset=False):
		
		if not reset and hasattr(self, 'r2formula'):
			return self.r2loci,self.r2formula
			
		assert self.root is not None and self.URI is not None
		
		r2loci=dict()
		r2formula=dict()
		r2formulaNode=dict()
		rid2node=dict()
		
		# look for reactions

		for r in self.reacNodes:
			reacId = r.get('id','INVALID')
			rid2node[reacId]=r
			notes  = r.find("{%s}notes" %(self.URI))	
			geneFormula=None

			body=notes.find("{http://www.w3.org/1999/xhtml}body")
			if body is not None:
				notes=body

			
			for line in notes:
				text = line.text
				if text.startswith("GENE ASSOCIATION:") or text.startswith("GENE_ASSOCIATION:"): 
					geneFormula=text[17:].strip()
					lineWithGA=line


			# skip reactions without gene association
			if not geneFormula:
				continue
			r2formula[reacId]=geneFormula
			r2formulaNode[reacId]=lineWithGA
			
			loci=frozenset(geneFormula.replace("(","").replace(")", "").replace("and", "").replace("or", "").split())
			# $loci is now a set of locus for this reactions
			r2loci[reacId]=loci
		
		self.r2loci=r2loci
		self.r2formula=r2formula
		self.r2formulaNode=r2formulaNode
		self.rid2node=rid2node
		
		return r2loci,r2formula
		


class GeneAssociation():
	"""Store a gene association"""
	def __init__(self, reactionNode, model):
		# super(GeneAssociation, self).__init__()
		self.reactionNode = reactionNode
		self.rid=reactionNode.get('id','INVALID')
		self.formula=model.r2formula.get(self.rid,None)
		self.loci=model.r2loci.get(self.rid,None)

	def getReactionName(self):
		assert self.reactionNode
		return self.reactionNode.get('name', 'INVALID')

class GAGroup(set):
	"""store a set of gene associations"""
	def __init__(self):
		super(GAGroup, self).__init__()


def main():
	pass

if __name__ == '__main__':
	main()

