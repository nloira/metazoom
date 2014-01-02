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

def log(msg):
	print >>sys.stderr, msg


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

	# layout screen for the first time
	mz.centerOnAnyReaction()
	mz.fiveColumnsLayout()

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
		# mz.redraw()
		mz.render()
		mainw.noutrefresh()
		curses.doupdate()

###############################################################


class MZlayout():
	REACTION = 1
	SPECIES = 2
	MORE = "~"
	ALTERNATELABEL = { 'id':'name', 'name':'id'}

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
		self.labelMode = "id"
		self.log=""

	def command(self, keyname):

		self.log="presionado: "+keyname

		if keyname.startswith("LOG:"):
			self.log=keyname[4:]
		elif keyname=="KEY_RESIZE":
			# recalculate window size
			(self.my,self.mx) = self.mainw.getmaxyx()
			self.fiveColumnsLayout()
		elif keyname=="n":
			self.labelMode = self.ALTERNATELABEL[self.labelMode]
			for tb in self.textboxes:
				tb.setLabelMode(self.labelMode)
		elif keyname=="r":
			self.centerOnAnyReaction()
			self.fiveColumnsLayout()
		elif keyname=="s":
			self.centerOnAnySpecies()
			self.fiveColumnsLayout()

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


	def fitTolength(self, label, maxLen):
		llabel = len(label)
		if llabel>maxLen:
			return label[:maxLen-1]+self.MORE
		else:
			return label


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

### New layout per columns
	def fiveColumnsLayout(self):

		# we'll find the neighbors at distance 2 of the centerOn element
		# and distribute them on five columns, like this:
		# | L2 | L1 | C0 | R1 | R2 |
		# but we'll use the names:
		# | 0 | 1 | 2 | 3 | 4 |
		(L2,L1,C0,R1,R2)=(0,1,2,3,4)

		# we'll use the class Textbox to represent the actual elements on screen

		### COMMON
		self.textboxes = []

		self.interColumnSpace = 5
		self.colw = (self.mx - (4*self.interColumnSpace))/5
		self.colh = self.my - 1 # left a line for status
		self.colvc = self.colh/2

		# column starting position
		colX = [0]*5
		# colX[0] = 0
		for i in range(4):
			colX[i+1] = colX[i] + self.colw + self.interColumnSpace

		### C0
		# create a textbox for the central element (self.centerOn)
		tbC0 = Textbox(self.centerOn, colX[C0], self.colvc)
		self.textboxes.append(tbC0)

		### Left side
		# create textboxes for left-of-the-center elements
		l1neighbors=self.getLeftOf(self.centerOn)
		lenl1 = len(l1neighbors)
		if lenl1 >0:
			# check that number of neighbors fit in the screen
			if lenl1>self.colh:
				l1neighbors=l1neighbors[0:self.colh]
				lenl1=self.colh

			# get L2 elements for each L1 element
			totL2=0
			l1tol2=dict()
			for n1 in l1neighbors:
				l2neighbors=self.getLeftOf(n1)
				totL2+=len(l2neighbors)
				l1tol2[n1]=l2neighbors

			# compute layout parameters for L1 and L2
			if totL2>self.colh:
				# get only some of them
				maxL2toDisplay=self.colh/lenl1
				l2vspace = 1
				l2start = 0
			else:
				maxL2toDisplay=self.colh*1000  # infinite
				l2vspace = 1
				l2start = (self.colh - (totL2 + l2vspace*(lenl1-1)))/2

			# create textboxes for L2 and L1
			l2pos = l2start

			for n1 in l1neighbors:
				l1pos = l2pos

				# textboxes for L2
				for n2 in l1tol2[n1][0:maxL2toDisplay]:
					tbL2 = Textbox(n2, colX[L2], l2pos)
					self.textboxes.append(tbL2)
					l2pos+=1
					l1pos+=0.5
				l2pos+=l2vspace

				# textbox for L1
				tbL1 = Textbox(n1, colX[L1], int(l1pos))
				self.textboxes.append(tbL1)


			### Right side
			# create textboxes for right-of-the-center elements
			r1neighbors=self.getRightOf(self.centerOn)
			lenr1 = len(r1neighbors)
			if lenr1 >0:
				# check that number of neighbors fit in the screen
				if lenr1>self.colh:
					r1neighbors=r1neighbors[0:self.colh]
					lenr1=self.colh

				# get L2 elements for each L1 element
				totR2=0
				r1tor2=dict()
				for n1 in r1neighbors:
					r2neighbors=self.getRightOf(n1)
					totR2+=len(r2neighbors)
					r1tor2[n1]=r2neighbors

				# compute layout parameters for L1 and L2
				if totR2>self.colh:
					# get only some of them
					maxR2toDisplay=self.colh/lenr1
					r2vspace = 1
					r2start = 0
				else:
					maxR2toDisplay=self.colh*1000  # infinite
					r2vspace = 1
					r2start = (self.colh - (totR2 + r2vspace*(lenr1-1)))/2

				# create textboxes for L2 and L1
				r2pos = r2start

				for n1 in r1neighbors:
					r1pos = r2pos

					# textboxes for L2
					for n2 in r1tor2[n1][0:maxR2toDisplay]:
						tbR2 = Textbox(n2, colX[R2], r2pos)
						self.textboxes.append(tbR2)
						r2pos+=1
						r1pos+=0.5
					r2pos+=r2vspace

					# textbox for L1
					tbR1 = Textbox(n1, colX[R1], int(r1pos))
					self.textboxes.append(tbR1)




		# tell our textboxes about our labelMode
		for tb in self.textboxes:
			tb.setLabelMode(self.labelMode)

		# remember stuff
		self.colX=colX



	def render(self):

		# render textboxes
		for tb in self.textboxes:
			tb.render(self)

		# render log line
		self.mainw.addstr(self.my-1,0,self.log)


class Textbox():

	DECORATORS={ "reaction":"[]", "species":"()", "others":"<>" }
	MORE="~"

	def __init__(self, element,x=0,y=0, align="l"):
		# align \in (l,c,r)
		self.element=element
		self.x=x
		self.y=y
		self.label=element.id
		self.llabel=len(self.label) if self.label!=None else 0
		self.align = align
		self.decorator=Textbox.DECORATORS.get(element.type, Textbox.DECORATORS["others"])

	def setLabelMode(self, labelMode):
		if labelMode=="name" and self.element.name != None:
			self.label=self.element.name
		else:
			self.label=self.element.id
		self.llabel=len(self.label) if self.label!=None else 0

	def render(self, mzlayout):

		maxw=mzlayout.colw

		label=self.label
		if (self.llabel+2)>maxw:
			label=label[:maxw-3]+Textbox.MORE

		label = self.decorator[0:1]+label+self.decorator[1:2]

		x=self.x
		llabel = len(label)

		# move if it does not use all the available column space
		if llabel<maxw:
			if self.align=="l": dx=0
			elif self.align=="r": dx=(maxw-llabel)
			elif self.align=="c": dx=(maxw-llabel)/2
		else:
			dx=0

		self.dx=dx

		mzlayout.mainw.addstr(self.y,self.x+dx,label)




###############################################################

if __name__ == "__main__":
    main()

