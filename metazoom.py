#!/usr/bin/env python
# encoding: utf-8
"""
Metazoom is a little ncurses-based visualizer of genome-scale metabolic models.

Nicolas Loira
nloira@gmail.com
2013
"""

import sys,os
import getopt
import curses
import time
import random

import basicSBML



def usage():
	"""Shows usage instructions"""
	print "Usage "+sys.argv[0]+ " [-h] [-c currency_file] SBMLfile.xml \n \
		-h/--help: print this message \n \
		-c: defines a file with a list of species indentifiers used as currency metabolites\n \
		(type '?' in metazoom to list available command)"


def main():

	# parse arguments
	try: opts, args = getopt.getopt(sys.argv[1:], "hc:", ["help"])
	except getopt.GetoptError:
		usage()
		sys.exit(2)

	currency_file = None

	for o,a in opts:
		if o in ("-h","--help"):
			usage()
			sys.exit()

		if o=="-c": currency_file=a

	if len(args)!=1:
		usage()
		sys.exit(2)

	# loading SBML model
	SBMLfile = args[0]
	print "Parsing "+SBMLfile+" ..."
	model=basicSBML.SBMLmodel(SBMLfile)

	print "Imported %d reactions" % len(model.reactions)
	print "Imported %d species" % len(model.species)
	print "Imported %d compartments" % len(model.compartments)

	# boot TUI
	print "\nStarting TUI..."
	curses.wrapper(mainTUI, model)

	# closing up
	print "Shutting down metazoom..."


###############################################################

def mainTUI(*args, **kwds):
	# just wait for a while

	mainw, model=args

	# setup curses
	curses.init_pair(1, curses.COLOR_RED, curses.COLOR_WHITE)
	curses.curs_set(0) # invisible cursor
	mainw.nodelay(0) # wait for user input

	# start metazoom layout engine
	mz = MZlayout(mainw, model)
	mz.printAtCenter("Welcome to MetaZoom")

	# Main loop
	while True:
		# get command
		key=mainw.getch()

		try:
			keyname=curses.keyname(key)
		except Exception, e:
			pass
			# keyname="LOG: invalid key:"+str(key) 
		
		
		# prepare new screen
		mainw.erase()

		# execute command
		mz.command(keyname)

		# update screen
		mz.redraw()
		mainw.noutrefresh()
		curses.doupdate()

###############################################################


class MZlayout():
	REACTION = 1
	SPECIES = 2

	def __init__(self, mainw, model):
		self.model=model
		self.mainw=mainw
		(self.my,self.mx) = mainw.getmaxyx()

		self.centerOn = None
		self.cmode = None
		self.focusOn = None
		self.distance = 1
		self.statusBar = ""
		self.log = None

	def command(self, keyname):

		if keyname.startswith("LOG:"):
			self.log=keyname[4:]
		elif keyname=="KEY_RESIZE":
			# recalculate window size
			(self.my,self.mx) = self.mainw.getmaxyx()
		else:
			self.centerOnAnyReaction()

	def centerOnAnyReaction(self):
		assert len(self.model.reactions)>0

		self.centerOn = random.choice(self.model.reactions)
		self.cmode = MZlayout.REACTION

	def centerOnAnySpecies(self):
		assert len(self.model.species)>0

		self.centerOn = random.choice(self.model.species)
		self.cmode = MZlayout.SPECIES

	def printAtCenter(self, label):
		llabel=len(label)
		assert llabel>0

		# display label on center of screen
		y = self.my/2
		x = (self.mx-llabel)/2

		self.mainw.addstr(y,x,label)

	def redraw(self):


		# what is the message?
		if self.log:
			label=self.log
			self.log=None
		elif self.cmode in (MZlayout.REACTION, MZlayout.SPECIES):
			label = self.decorate(self.centerOn.id, self.cmode)
		else:
			assert False, "WRONG CENTER MODEL"

		# display label on center of screen
		self.printAtCenter(label)

		# get neighbors at distance 1
		if self.cmode in (MZlayout.REACTION, MZlayout.SPECIES):
			# lists of neigbors
			leftNeighbors = self.getLeftOf(self.centerOn)
			rightNeighbors = self.getRightOf(self.centerOn)

			# type of neigbors
			ntype = MZlayout.REACTION if self.cmode==MZlayout.SPECIES else MZlayout.SPECIES

			# where do we put them?
			## let's leave some space before and after the center label
			lenlabel=len(label)


			# right side is easy (left aligned)
			if len(rightNeighbors)>0:
				rinix = (self.mx+lenlabel)/2 + 4
				riniy = (self.my-len(rightNeighbors))/2

				for rn in rightNeighbors:
					rlabel=self.decorate(rn.id, ntype)
					self.mainw.addstr(riniy,rinix,rlabel)
					riniy+=1

			# left side is trickier (left aligned, with enough space for all of them)
			if len(leftNeighbors)>0:
				liniy = (self.my-len(leftNeighbors))/2

				lnLabels=[self.decorate(ln.id, ntype) for ln in leftNeighbors]
				maxleftlen = max(map(len, lnLabels))
				linix = (self.mx-lenlabel)/2 -4 -maxleftlen

				for lnLabel in lnLabels:
					self.mainw.addstr(liniy,linix,lnLabel)
					liniy+=1


		# where do we list them?

	def decorate(self, label, cmode):
		if cmode==MZlayout.REACTION:
			dlabel = "["+label+"]"
		elif cmode==MZlayout.SPECIES:
			dlabel = "("+label+")"
		else:
			assert False, "WRONG CENTER MODEL"
		return dlabel

	def getRightOf(self, element):

		className=element.__class__.__name__
		if className=="Reaction":
			neighbors = element.products
		elif className=="Species":
			neighbors = self.model.reactionsThatConsume(element)
		else:
			assert False, "Trying to find neighbors for class %s" % (className)

		return neighbors

	def getLeftOf(self, element):

		className=element.__class__.__name__
		if className=="Reaction":
			neighbors = element.reactants
		elif className=="Species":
			neighbors = self.model.reactionsThatProduce(element)
		else:
			assert False, "Trying to find neighbors for class %s" % (className)

		return neighbors






###############################################################

if __name__ == "__main__":
    main()

