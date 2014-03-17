import rhinoscriptsyntax as rs
from Grasshopper.Kernel.Data import GH_Path
from Grasshopper import DataTree
import ghpythonlib.components as ghcomp
import sys
import gc
import math
import copy

DECIMALPRECISION = 3
CourseList= []
BrickList = [[] for i in xrange(len(ContourCurves))]
DebugList = []
DebugList2 = []

dbg = False 
dbg2 = True
"""
#######################
#### CLASSES START ####
#######################
"""


#IMPLEMENT SO THAT EACH BRICK DOES NOT HAVE THE ENTIER CURVE INSIDE OF IT
class Course:
	#each course is defined as a course curve and a list of bricks
	def __init__(self, curve):
		self.courseCurve = curve
		self.courseBricks = []
		self.courseLen = roundDecimal(rs.CurveLength(curve))
		self.isClosedCurve = rs.IsCurveClosed(curve)

	def getCurve(self):
		return self.courseCurve

	def length(self):
		return self.courseLen

	def isClosed(self):
		return self.isClosedCurve
	
	def getClosestPointAsLength(self, point):
		return rs.CurveLength(self.courseCurve, -1, [0, self.getClosestPointAsParameter(point)])
	
	def getClosestPointAsParameter(self, point):
		return rs.CurveClosestPoint(self.courseCurve, point)

	def getClosestPointAsPoint(self, point):
		return rs.EvaluateCurve(self.courseCurve, self.getClosestPointAsParameter(point))

	def getTangentVectorFromParameter(self, parameter):
		return rs.CurveTangent(self.getCurve(), parameter)		
		return rs.CurveCurvature(self.getCurve(), parameter)[1]		

	def getRotationByPointVector(self, point, vector):
		# get curvature at this point
		hereTangent = self.getTangentVectorFromParameter(self.getClosestPointAsParameter(point))

		DebugList.append([hereTangent])
		
		printIf(dbg, "getangle between", vector, "And", hereTangent)
		# get angle between these fectors, from hereTangent to Vector
		# THIS NEEDS TO BE RESTRICTED TO THE XY PLANE
		# which is why we use grasshopper components; python can't restrict to XY plane
		return ghcomp.Angle(hereTangent, vector, rs.WorldXYPlane())[0]


class Brick3D:
	#each 3d brick is defined as a point, direction, and course curve
	#constructor
	def __init__(self, point, rotation, Course):
		self.brickCenter = point
		self.brickRotation = rotation
		self.Course = Course
		self.setLocationByPoint(point)

	def setRotation(self, rotation):
		self.brickRotation = rotation

	def setCourse(self, Course):
		self.Course = Course

	def setLocationByLength(self, length):
		printIf(dbg, length)
		if(self.Course.isClosed()):
			length %= self.Course.length()
		else:
			if length > self.Course.length():
				return False
		self.curveLenParameter = length
		self.setLocationByPoint(rs.CurveArcLengthPoint(self.Course.getCurve(), length))
		self.curveParameter = rs.CurveClosestPoint(self.Course.getCurve(), self.brickCenter)

#	def setLocationByParameter(self, parameter):
#		self.curveParameter = parameter
#		self.brickCenter = rs.EvaluateCurve(self.Course.getCurve(), parameter)

	def setLocationByPoint(self, point):
#		self.brickCenter = point
		self.curveParameter = rs.CurveClosestPoint(self.Course.getCurve(), point)
		self.brickCenter = rs.EvaluateCurve(self.Course.getCurve(), self.curveParameter)
		self.curveLenParameter = rs.CurveLength(self.getCourse().getCurve(), -1, [0, self.curveParameter])

	def getEndpoints3D(self):
		thisVector = rs.VectorScale(self.getVector(), (BrickWidth / 2))
		#DebugList.append([rs.PointAdd(self.brickCenter, thisVector), rs.PointAdd(self.brickCenter, rs.VectorReverse(thisVector))])
		return [rs.PointAdd(self.brickCenter, thisVector), rs.PointAdd(self.brickCenter, rs.VectorReverse(thisVector))]

	def getVector(self):
#		print self.Course.getCurve(), self.curveParameter
		curveVector = rs.CurveTangent(self.Course.getCurve(), self.curveParameter)		
#		print math.degrees(self.brickRotation)
#		print curveVector
		#rotatedVec = rs.VectorRotate(rs.VectorReverse(curveVector),  math.degrees(self.brickRotation), [0,0,1])
		rotatedVec = rs.VectorRotate(curveVector,  math.degrees(self.brickRotation), [0,0,1])
		return rotatedVec
		return rs.CurveCurvature(self.Course.getCurve(), self.curveParameter)[1]		

	def getRotation(self):
		return self.brickRotation

	def getLocationAsParameter(self):
		return self.curveParameter
	
	def getLocationAsLength(self):
#		return ghcomp.LengthParameter(self.getCourse().getCurve(), self.curveParameter)[0]
#		return roundDecimal(rs.CurveLength(self.getCourse().getCurve(), -1, [0, self.curveParameter]))
		return self.curveLenParameter

	def getLocationAsPoint(self):
		return self.brickCenter

	def getCourse(self):
		return self.Course

	def getCourseLen(self):
		return self.Course.length()


	def getDistancePoint3D(self, point):
		return rs.Distance(self.getLocationAsPoint(), point)

	def getDistance3D(self, b2):
		return rs.Distance(self.getLocationAsPoint(), b2.getLocationAsPoint())

	def getDistanceOnCurve(self, b2):
		[pb1, pb2] = sorted([self.getLocationAsParameter(),b2.getLocationAsParameter()])
		if(self.Course.isClosed()):
			return (pb2 - pb1) % self.Course.length()
		else:
			return abs(pb1 - pb2)

	def getMidpoint3D(self, b2):
		return rs.PointDivide(rs.PointAdd(self.getLocationAsPoint(), b2.getLocationAsPoint()), 2)
		
	def getMidpointOnCurve(self, b2):
		#make sure that they're in order
		[pb1, pb2] = sorted([self.getCurveParameter(),b2.getCurveParameter()])
		if(self.isCurveClosed):
			if((pb2 - pb1) <= (curveLen / 2)):
				#if the two bricks are close enough on a closed curve as to not wrap around
				return roundDecimal((pb1 + pb2) / 2)
			else:
				#no, they wrap around, accomodate for that
				return roundDecimal((pb2 + ((curveLen - pb2 + pb1) / 2)) % curveLen)
		else:
			#vanilla
			return roundDecimal((pb1 + pb2) / 2)

	@classmethod
	def newBrickWidthAfterRotation(self, rotation):
		return math.cos(rotation) * BrickWidth

	@classmethod 
	def getFacingEndpoints3D(self,b1, b2):
		global DebugList

		# get the midpoints of the bricks
		midPoint3D = b1.getMidpoint3D(b2)

		# get all endpoints
		B1EndPoints3D = b1.getEndpoints3D()
		B2EndPoints3D = b2.getEndpoints3D()

		# get all distances between midpoint and all endpoints
		pointDistancesB1 = map(lambda x: rs.Distance(midPoint3D, x), B1EndPoints3D)
		pointDistancesB2 = map(lambda x: rs.Distance(midPoint3D, x), B2EndPoints3D)

		# get closest two endpoints
		closestEndpointIndexB1 = sorted(range(len(B1EndPoints3D)), key=lambda k: pointDistancesB1[k])[0]
		closestEndpointIndexB2 = sorted(range(len(B2EndPoints3D)), key=lambda k: pointDistancesB2[k])[0]
		closestEndpointB1 = B1EndPoints3D[closestEndpointIndexB1]
		closestEndpointB2 = B2EndPoints3D[closestEndpointIndexB2]

		return [closestEndpointB1, closestEndpointB2]

	@classmethod 
	def getBearingEndpoints3D(self,b1,b2):
		#get endpoints
		endpoints = Brick3D.getFacingEndpoints3D(b1, b2)

	#	DebugList.append(endpoints)

		bothBricks = [b1,b2]

	#	DebugList.append(map(lambda x:x.brickCenter, bothBricks))

		bearingEndpoints = []
		# get midpoints between these endpoints and midpoints of b1, b2 
		# REALLY THIS SHOULD BE MIDPOINT OF BEARING IDEAL
		for i in xrange(len(endpoints)):
			bearingEndpoints.append(midpoint3D(endpoints[i], bothBricks[i].getLocationAsPoint()))	

	#	DebugList.append(bearingEndpoints)

		return bearingEndpoints
		

	@classmethod
	# get distances from this brick to lower bricks - in 3D space.
	def getClosestTwoBricks3D(self, thisbrick, abricklist):

		thisdistances = map(lambda x: thisbrick.getDistance3D(x), abricklist)
		#okay, get the indices of the closest midpoint (sort and return keys)

		closestIndex = sorted(range(len(thisdistances)), key=lambda k: thisdistances[k])[0:2]

		#okay, get the locations of the cloeset lower bricks
		return [abricklist[i] for i in closestIndex]



"""
#######################
####  CLASSES END  ####
#######################
"""



def midpoint3D(p1, p2):
	# get midpoint of endpoints
	return rs.PointDivide(rs.PointAdd(p1, p2), 2)

def roundDecimal(num):
	global DECIMALPRECISION
	#ugly but clean
	return float(int((num * 10**DECIMALPRECISION)) / (10**DECIMALPRECISION))
	#return round(num, DECIMALPRECISION)

def printIf(*arg):
	if(arg[0]):
		print ' '.join(map(str, list(arg[1:])))


def ListofListsToTree(LOL):
	ROTFL = DataTree[object]()
	for i in xrange(len(LOL)):
		ROTFL.AddRange(LOL[i], GH_Path(i))
	return ROTFL

def howManyBricksCanWeMake(index, avgrotation=0):
	#get length of curve
	curvelen = CourseList[index].length()
	#return range of brick#
	newBW = Brick3D.newBrickWidthAfterRotation(avgrotation)
	return [math.ceil(curvelen  / (newBW + GapDomain[0])), math.floor(curvelen / (newBW + GapDomain[1]))]

def decideBrickNum(index, avgrotation=0):
	brickn = howManyBricksCanWeMake(index, avgrotation)
	return int(sum(brickn)/len(brickn))

def isBrickSpacingOverlapping(thisBrickLocation, index, isClosedCurve=False, curvelen=0):
	#check to see if the brick overlaps with anything
	thisdistances = map(lambda x: Brick.distance(thisBrickLocation, x.brickCenter, isClosedCurve, curvelen), BrickList[index])
	#print "t>>>>>>>>>", thisdistances
	for adist in thisdistances:
		if(adist < BrickWidth):
			return True
	return False

# check if we can place any more bricks on this course
def isCourseFull(index):
	global BrickList

	return False

	if(len(BrickList[index]) == 0):
		return False

	BrickParams = sorted(map(lambda x: x.getLocationAsParameter(), BrickList[index]) + [0, CourseList[index].length()])

	printIf(dbg, BrickParams)

	sortedBrickList =  sorted(BrickList[index], key=lambda k: k.getLocationAsParameter())

	printIf(dbg, sortedBrickList)

	for i in xrange(1, len(sortedBrickList)):
		# you know something has space if there is at least one location in which the distance between bricks > BrickWidth * 2
		if(sortedBrickList[i - 1].getDistanceOnCurve(sortedBrickList[i]) > BrickWidth * 2):
			return False
	
	return True





#get endpoints of bricks closest to midPoint
def closestEndPoints(midPoint, closestBricks, index):
	global CourseList

	printIf(dbg, midPoint)
	midPointParam = CourseList[index].getClosestPointAsParameter(midPoint)
	closestEndpointParams = [[eachlist - (BrickWidth / 2), eachlist + (BrickWidth / 2)] for eachlist in map(lambda x: x.getLocationAsParameter(), closestBricks)]
#	print "closest bricks = ",map(lambda x: x.getLocationAsParameter(), closestBricks)
#	print "closest endpoints params=",closestEndpointParams	
#	print midPointParam	




# find where to place bricks on top of these two closest bricks, taking bearing (rotation) into account
def findBrickBearingPlacement(closestBricks, index):
	global BrickList
	global CourseList
	global DebugList
	#get midpoint of bricks
	midPoint = closestBricks[0].getMidpoint3D(closestBricks[1])
	
#	DebugList.append([midPoint])

	# get the two endpoints closest to each other
	facingEndpoints = Brick3D.getBearingEndpoints3D(closestBricks[0],closestBricks[1])

	DebugList.append([rs.AddLine(facingEndpoints[0], facingEndpoints[1])])

	# get midpoint of endpoints
	endpointmid = midpoint3D(facingEndpoints[0], facingEndpoints[1])

	#DebugList.append([CourseList[index].getCurve()])

	# and project onto our line
	placementPoint = CourseList[index].getClosestPointAsPoint(endpointmid)	

	DebugList.append([placementPoint])

	#hopefully vector's not too different
	placementVector = rs.VectorCreate(facingEndpoints[0], facingEndpoints[1])

	DebugList.append([placementVector])


	#rotate brick
	rotation = CourseList[index].getRotationByPointVector(placementPoint, placementVector)

#	rotation += (0.05  * (len(CourseList)-index))
	printIf(dbg, "rotation=", rotation)
#	DebugList.append([rotation])
#	printIf(True, "okay distance to attrpt = ", newBrick.getDistancePoint3D(AttractorPoint))
	if(AttractorPoint != None):
		printIf(dbg, 20 / math.sqrt(rs.Distance(placementPoint, AttractorPoint)))
		rotation += 10 / (rs.Distance(placementPoint, AttractorPoint) )

	newBrick = Brick3D(placementPoint, rotation, CourseList[index])
	return newBrick


# find where to place bricks on top of these two closest bricks
# actually, for each pair of bricks, try to spread out and place three bricks
def findBrickPlacement(closestBricks, index):
	global BrickList

	#get midpoint of bricks
	midPoint = closestBricks[0].getMidpoint3D(closestBricks[1])

	#get closest point on line to this midpoint
	closestParam = rs.CurveClosestPoint(ContourCurves[index], midPoint)
	closestPoint = rs.EvaluateCurve(ContourCurves[index], closestParam)
	#closestPoint = rs.CurveArcLengthPoint(ContourCurves[index], closestParam)

	closestBrickDistCurve = closestBricks[0].getDistanceOnCurve(closestBricks[1])

	#rotate brick none, for now
	rotation = 0

	newBrick = Brick3D(closestPoint, rotation, CourseList[index])

	return newBrick


# check if brick overlaps or not
def brickDoesNotOverlap(brickToPlace, index):
	global BrickList

	# are there any bricks that are within BrickWidth distance of brickToPlace?
	for aBrick in (BrickList[index]):
		if(brickToPlace.getDistance3D(aBrick) < (Brick3D.newBrickWidthAfterRotation(brickToPlace.getRotation()) + BrickSpacingMin)):
			print "UHOH"
			print "brickToPlace.getDistance3D(aBrick) (",brickToPlace.getDistance3D(aBrick),") should be > but is < ",
			print (Brick3D.newBrickWidthAfterRotation(brickToPlace.getRotation()) + BrickSpacingMin)
			return False

	return True


# check if we can place brick.
def brickIsSupported(brickToPlace, closestBricks, index):
	global BrickList

	#check from this brick to each brick - is the overlap desirable?
	#overlap = BrickWidth - brick midpoint distance
	for eachClosestBrick in closestBricks:
		overlap = (BrickWidth - brickToPlace.getDistance3D(eachClosestBrick))
		if(overlap < BrickBearingMin):
			return False
	return True

# place brick
def addBrickToCourse(brickToPlace, index):
	global BrickList
	BrickList[index].append(copy.deepcopy(brickToPlace))

def layNormalCourse(index, rhythm=0):
	global BrickList
	global CourseList
	global DebugList2

	avgrotation = -0.9
	newBW = Brick3D.newBrickWidthAfterRotation(avgrotation)

	brickn = decideBrickNum(index, avgrotation)
#	brickn *= 1.3
	averageGap = (BrickSpacingMax + BrickSpacingMin) / 2

#	print ">>> LAYING NORMAL COURSE #", index
	#set provisional location
	if(rhythm == 0):
		provisionalLocation = 0
	else:
		provisionalLocation = (index % rhythm) * (newBW / 2)	

	# add each brick brick, spaced apart
	for i in xrange(brickn):

		printIf(dbg, "provis / len", provisionalLocation, CourseList[index].length())
		if(provisionalLocation > CourseList[index].length()):
			break

		# make a provisional brick
		newBrick = Brick3D([0,0,0], avgrotation, CourseList[index])

		# move the brick to where we want it to be
		newBrick.setLocationByLength(provisionalLocation)

		# add brick to list
		BrickList[index].append(newBrick)
		
		# move the new location to the brick width, plus the gap
		provisionalLocation += newBW + averageGap

#	print "bricklist=", map(lambda x: x.getLocationAsLength(), BrickList[index])


#this places bricks at the edges of a curve
# if applicable (aka curve is closed)
def layEdges(index):
	if(index == 0):
		return

	
	


def layStackingCourse(index):
	global BrickList
	global CourseList
	global dbg

	printIf(dbg, " ")
	printIf(dbg, "###########################################")
	printIf(dbg, "##### PLACING BRICK COURSE", index, " ----" )
	printIf(dbg, "length = ", CourseList[index].length())
	printIf(dbg, "###########################################")
	printIf(dbg, " ")
	brickn = decideBrickNum(index)

	if(index == 0):
		#we're the lowest line, place a normal Course
		layNormalCourse(index)	
	else:
		provisionalBrick = Brick3D([0,0,0], 0, CourseList[index])
		provisionalBrick.setLocationByLength(0)

		for i in xrange(brickn * 2): # this should be a while(True) loop but gh lets python run FOREVER so let's be safe

			#if we have two or more bricks on our floor below us
			if(len(BrickList[index - 1]) >= 2):

				printIf(dbg, "*** COURSE", index,", BRICK #", i)
				printIf(dbg, " ")
				printIf(dbg, "course underneath =",)
				printIf(dbg, map(lambda x: x.getLocationAsLength(), BrickList[index-1]))
			#PROCESS:
				# set a provisional brick
				# find two closest bricks
				# find where to place bricks on top of these two closest bricks
				# place brick
				# move provisional brick to new location
				#okay, try to place the brick right here.

				# if we can't place any more, get out of this
				if(isCourseFull(index)):
					continue

				printIf(dbg, ">> provisional brick (", i, "/", brickn,") at", provisionalBrick.getLocationAsLength())

				# find two closest bricks 
				closestBricks = Brick3D.getClosestTwoBricks3D(provisionalBrick, BrickList[index - 1])
				printIf(dbg, ">>> 1. two closest bricks from", provisionalBrick.getLocationAsLength(), "=",map(lambda x:x.getLocationAsLength(), closestBricks), "on curve with len", closestBricks[0].getCourse().length())

				# find where to place bricks on top of these two closest bricks
				brickToPlace = findBrickBearingPlacement(closestBricks, index)

#				DebugList.append(brickToPlace.getLocationAsPoint())

				# actually, for each pair of bricks, try to spread out
#				bricksToPlace = findBrickPlacements(closestBricks, index)

				printIf(dbg, ">>> 2. Brick should be placed at", brickToPlace.getLocationAsLength() , "/", CourseList[index].length())

				#if(brickIsSupported(brickToPlace, closestBricks, index) and brickDoesNotOverlap(brickToPlace, index)):
				if(brickDoesNotOverlap(brickToPlace, index)):
					# place brick
					printIf(dbg2, ">>> 3. Brick PLACED at",brickToPlace.getLocationAsLength())
					addBrickToCourse(brickToPlace, index)
				else:
					printIf(dbg2, ">>> 3. Brick NOT PLACED")

				# move provisional point to new location
				printIf(dbg2, "moving brick", i,"course", index, "provisional point to new location")
				provisionalBrick.setLocationByLength(brickToPlace.getLocationAsLength() + Brick3D.newBrickWidthAfterRotation(provisionalBrick.getRotation()))
				printIf(dbg2, "rotation=", brickToPlace.getRotation() ,"newBWafterotation=",Brick3D.newBrickWidthAfterRotation(brickToPlace.getRotation()))
				printIf(dbg2, "BW=", BrickWidth)


		#print BrickList[index]
		printIf(dbg, "okay, next course")


def processInput():
	global BrickSpacingMin, BrickSpacingMax, BrickBearingMin 

	# define courses
	for i in xrange(len(ContourCurves)):
		CourseList.append(Course(ContourCurves[i]))		

	BrickSpacingMin = GapDomain[0]
	BrickSpacingMax = GapDomain[1]
	BrickBearingMin = MinBearing



def layCourses():
	for i in xrange(len(CourseList)):
#		layNormalCourse(i, 2)
#		layEdges(i)
		layStackingCourse(i)

def outputCourses():
	global BrickList
	global BrickPoints
	global BrickPattern
	global BrickVectors
	global BrickRotation
	global DebugList
	global DebugList2
	#output what we've got
	DebugList = ListofListsToTree(DebugList)
	DebugList2 = ListofListsToTree(DebugList2)
	BrickPattern = ListofListsToTree([map(lambda x: x.getLocationAsParameter(), alist) for alist in BrickList])
	BrickPoints = ListofListsToTree([map(lambda x: x.getLocationAsPoint(), alist) for alist in BrickList])
	BrickVectors = ListofListsToTree([map(lambda x: x.getVector(), alist) for alist in BrickList])
	BrickRotation = ListofListsToTree([map(lambda x: x.getRotation(), alist) for alist in BrickList])
		

"""
###############################
###############################
###############################
###############################
INPUTS:
ContourCurves
BrickWidth
GapDomain
MinBearing

OUTPUTS:
BrickPattern
BrickPoints
BrickRotation
"""


def main():
	processInput()
	layCourses()
	outputCourses()



#	printIf(dbg, BrickPoints)
if __name__ == "__main__":
	main()

