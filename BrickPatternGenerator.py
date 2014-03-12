
import rhinoscriptsyntax as rs
from Grasshopper.Kernel.Data import GH_Path
from Grasshopper import DataTree
import gc
import math

DECIMALPRECISION = 3
BrickList = [[] for i in xrange(len(ContourCurves))]
DebugList = []

class Brick:
	def __init__(self, courseLength, brickCenter, brickRotation):
		#self.brickWidth = brickWidth
		self.courseLength = courseLength
		self.brickCenter = brickCenter
		self.brickRotation = brickRotation

	@classmethod	
	def distance(self, b1, b2, isClosedCurve=False, curvelen=0):
		[b1, b2] = sorted([b1,b2])
		if(isClosedCurve):
			return (b2 - b1) % curvelen
		else:
			return abs(b1 - b2)

	@classmethod
	def midpoint(self, b1, b2, isClosedCurve=False, curvelen=0):
		#make sure that they're in order
		[b1, b2] = sorted([b1,b2])
		if(isClosedCurve):
			if((b2 - b1) <= (curvelen / 2)):
				#if the two bricks are close enough on a closed curve as to not wrap around
				return round((b1 + b2) / 2, DECIMALPRECISION)
			else:
				#no, they wrap around, accomodate for that
				return round((b2 + ((curvelen - b2 + b1) / 2)) % curvelen , DECIMALPRECISION)	
		else:
			#vanilla
			return round((b1 + b2) / 2, DECIMALPRECISION)

def ListofListsToTree(LOL):
	ROTFL = DataTree[object]()
	for i in xrange(len(LOL)):
		ROTFL.AddRange(LOL[i], GH_Path(i))
	return ROTFL

def howManyBricksCanWeMake(index):
	#don't like the name of this method? deal with it
	curvelen = rs.CurveLength(ContourCurves[index])
	return [math.ceil(curvelen  / (BrickWidth + GapDomain[0])), math.floor(curvelen / (BrickWidth + GapDomain[1]))]

def decideBrickNum(index):
	brickn = howManyBricksCanWeMake(index)
	return int(sum(brickn)/len(brickn))

def isBrickOverlapping(thisBrickLocation, index, isClosedCurve=False, curvelen=0):
	#check to see if the brick overlaps with anything
	thisdistances = map(lambda x: Brick.distance(thisBrickLocation, x.brickCenter, isClosedCurve, curvelen), BrickList[index])
	#print "t>>>>>>>>>", thisdistances
	for adist in thisdistances:
		if(adist < BrickWidth):
			return True
	return False


def isCourseFull(index, isClosedCurve=False, curvelen=0):
	betweendistances = [] 
	brickPoints = sorted(map(lambda x: x.brickCenter, BrickList[index]))
	for i in xrange(1, len(brickPoints)):
		if(Brick.distance(brickPoints[i - 1], brickPoints[i], isClosedCurve, curvelen) < BrickWidth):
			return True
	return False

def getClosestTwoBricks(thisBrickLocation, index, isClosedCurve=False, curvelen=0):
	#get distances from this brick to lower bricks
	thisdistances = map(lambda x: Brick.distance(thisBrickLocation, x.brickCenter, isClosedCurve, curvelen), BrickList[index])
	#okay, get the indices of the closest midpoint (sort and return keys)
	closestIndex = sorted(range(len(thisdistances)), key=lambda k: thisdistances[k])[0:2]
	#okay, get the locations of the cloeset lower bricks
	return [BrickList[index][i].brickCenter for i in closestIndex]

	
def placeNormalCourse(index, brickn):	
	global BrickList
	curvelen = rs.CurveLength(ContourCurves[index])
	averageGap = (curvelen - (brickn * BrickWidth)) / brickn
	
	thisBrickLocation = 0
	for i in xrange(brickn):
		# add a brick
		BrickList[index].append(Brick(curvelen, thisBrickLocation, 0))
		
		# move the new location to the brick width, plus the gap
		thisBrickLocation += BrickWidth + averageGap

def layCourse(index):
	global BrickList
	
	#okay, so place bricks.
	#look at the line below -- unless we're the lowest line, natch
	
	#how many bricks can we make?
	brickn = decideBrickNum(index)
	curvelen = rs.CurveLength(ContourCurves[index])
	isCurveClosed = rs.IsCurveClosed(ContourCurves[index])
	
	print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>INDEX", index
	
	if(index == 0):
		#what the what, we're the lowest line
		placeNormalCourse(index, brickn)	
				
	else:
		#for the time being let's just pretend that the ideal point to put the brick
		#is smack dab bang in the middle of the two closest bricks
		#or in the middle of the two closest points of the course below us
		thisBrickLocation = 0
		brickLocations = []
		brickGap = 0
		#print "lowerbricks=",map(lambda x: x.brickCenter, BrickList[index-1])
		for i in xrange(brickn * 2): # this should be a while(True) loop but gh lets python run FOREVER so let's be safe

			#if we have two or more bricks on our floor below us
			if(len(BrickList[index - 1]) >= 2):
				#okay, try to place the brick right here.

				#for this brick, find the two closest lower bricks, 
				closestBricks = getClosestTwoBricks(thisBrickLocation , index - 1, isCurveClosed, curvelen)
				#print "the two closest =", closestBricks

				#get their midpoint
				theirmidpoint = Brick.midpoint(closestBricks[0], closestBricks[1], isCurveClosed, curvelen)

				#now we have to translate their midpoint to our midpoint, since the curve on this level may be different in length to the one below
				their3dmidpoint = rs.EvaluateCurve(ContourCurves[index - 1], theirmidpoint)
#				print their3dmidpoint
				thismidpoint = rs.CurveClosestPoint(ContourCurves[index], their3dmidpoint)
				#print "what about", thismidpoint,"?"
#				print "INDEX ", index, "<<<<<<<<<<< Trying to place B#",i, "----",  thisBrickLocation, "  it's better to place at ", thismidpoint, ", because of two bricks underneath:", closestBricks[0], "and", closestBricks[1]

				#if it overlaps with something we already have, go on
				if(isBrickOverlapping(thismidpoint, index, isCurveClosed, curvelen)):
#					print "nope, can't"
					thisBrickLocation += BrickWidth
					# aw shucks we're trying to place on the same point twice - break this for loop
				else:	
					BrickList[index].append(Brick(curvelen,thismidpoint,0))
#					print "success!"
					#print "placed brick #", i, "at ", thismidpoint
					thisBrickLocation = thismidpoint + BrickWidth

			if(isCourseFull(index, isCurveClosed, curvelen)):
				continue



"""
what do we want to do?
we want to stack these fucking bricks, that's what we want to do.

>>> PROCESS <<<
look at a line (a course) carefully place bricks on it, being careful that the bricks fall on the bricks below. 
rinse, repeat.

bricks are represent
"""



for i in xrange(len(ContourCurves)):
	layCourse(i)
	##print rs.CurveLength(thisCurve)
for i in xrange(len(ContourCurves)):
	for j in xrange(len(BrickList[i])):
		DebugList.append(rs.EvaluateCurve(ContourCurves[i], BrickList[i][j].brickCenter))

#output what we've got
BrickPattern = ListofListsToTree([map(lambda x: x.brickCenter, alist) for alist in BrickList])
BrickRotation = ListofListsToTree([map(lambda x: x.brickRotation, alist) for alist in BrickList])
	
   





