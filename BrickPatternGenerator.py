import sys
import rhinoscriptsyntax as rs
from Grasshopper.Kernel.Data import GH_Path
from Grasshopper import DataTree
import gc
import math
import copy

DECIMALPRECISION = 3
CourseList= []
BrickList = [[] for i in xrange(len(ContourCurves))]
DebugList = []


#IMPLEMENT SO THAT EACH BRICK DOES NOT HAVE THE ENTIER CURVE INSIDE OF IT
class Course:
	#each course is defined as a course curve and a list of bricks
	def __init__(self, curve):
		self.courseCurve = curve
		self.courseBricks = []
		self.courseLen = rs.CurveLength(curve)
		self.isClosedCurve = rs.IsCurveClosed(curve)

	def getCurve(self):
		return self.courseCurve

	def length(self):
		return self.courseLen

	def isClosed(self):
		return self.isClosedCurve

	def getClosestParameterFromPoint(self, point):
		return rs.CurveClosestPoint(self.courseCurve, point)


class Brick3D:
	#each 3d brick is defined as a point, direction, and course curve
	#constructor
	def __init__(self, point, rotation, Course):
		#self.brickWidth = brickWidth
		self.brickCenter = point
		self.brickRotation = rotation
		self.Course = Course
#		self.courseCurve = curve
		self.curveParameter = rs.CurveClosestPoint(Course.getCurve(), point)

	def setRotation(self, rotation):
		self.brickRotation = rotation

	def setCourse(self, Course):
		self.Course = Course

	def setLocationByParameter(self, parameter):
		self.brickCenter = rs.EvaluateCurve(self.Course.getCurve(), parameter)
		self.curveParameter = parameter

	def setLocationByPoint(self, point):
		self.brickCenter = point
		self.curveParameter = rs.CurveClosestPoint(self.courseCurve, point)

	def getEndpoints3D(self):
		return[rs.PointAdd(self.brickCenter, self.getVector()), rs.PointAdd(self.brickCenter, rs.VectorReverse(self.getVector()))] 

	def getVector(self):
		return rs.CurveCurvature(self.Course.getCurve(), self.curveParameter)[1]		

	def getRotation(self):
		return self.brickRotation

	def getLocationAsParameter(self):
		return self.curveParameter
		
	def getLocationAsPoint(self):
		return self.brickCenter

	def getCourseLen(self):
		return self.Course.length()

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
		

	def getFacingEndpoints3D(self, b2):

		# get midpoitn in 3d
		midPoint3D = self.getMidpoint3D(b2)

		# get all endpoints in 3D
		endPoints3D = self.getEndpoints3D() + b2.getEndpoints3D()

		B1EndPoints3D = self.getEndpoints3D()
		B2EndPoints3D = b2.getEndpoints3D()
	
		print "Endpoints = ",endPoints3D

		# get all distances between midpoint and all endpoints
		pointDistancesB1 = map(lambda x: rs.Distance(midPoint3D, x), B1EndPoints3D)
		pointDistancesB2 = map(lambda x: rs.Distance(midPoint3D, x), B2EndPoints3D)

		print "Pb1", pointDistancesB1
		print "Pb2", pointDistancesB2
		# get closest two endpoints

		closestEndpointIndexB1 = sorted(range(len(B1EndPoints3D)), key=lambda k: pointDistancesB1[k])[0]
		closestEndpointIndexB2 = sorted(range(len(B2EndPoints3D)), key=lambda k: pointDistancesB2[k])[0]
		closestEndpointB1 = endPoints3D[closestEndpointIndexB1]
		closestEndpointB2 = endPoints3D[closestEndpointIndexB2]

		return [closestEndpointB1, closestEndpointB2]
		# project those endpoints onto curve
		
		# get placementpoint: midpoint of endpoints
		placementPoint = rs.PointDivide(rs.PointAdd(closestEndpointB1, closestEndpointB2), 2)

		# get placement vector:
		placementVector = rs.VectorCreate(closestEndpointB1, closestEndpointB2)
		
		print placementPoint
		print placementVector
	
	def getMidpointOnCurve(self, b2):
		#make sure that they're in order
		[pb1, pb2] = sorted([self.getCurveParameter(),b2.getCurveParameter()])
		if(self.isCurveClosed):
			if((pb2 - pb1) <= (curveLen / 2)):
				#if the two bricks are close enough on a closed curve as to not wrap around
				return Brick3D.roundDecimal((pb1 + pb2) / 2)
			else:
				#no, they wrap around, accomodate for that
				return Brick3D.roundDecimal((pb2 + ((curveLen - pb2 + pb1) / 2)) % curveLen)
		else:
			#vanilla
			return Brick3D.roundDecimal((pb1 + pb2) / 2)

#

	@classmethod
	def roundDecimal(self, num):
		global DECIMALPRECISION
		return round(num, DECIMALPRECISION)


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

def isBrickSpacingping(thisBrickLocation, index, isClosedCurve=False, curvelen=0):
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

	print BrickParams

	sortedBrickList =  sorted(BrickList[index], key=lambda k: k.getLocationAsParameter())

	print sortedBrickList

	for i in xrange(1, len(sortedBrickList)):
		# you know something has space if there is at least one location in which the distance between bricks > BrickWidth * 2
		if(sortedBrickList[i - 1].getDistanceOnCurve(sortedBrickList[i]) > BrickWidth * 2):
			return False
	
	print "FULLLLLLLLLLLLLLLLL"
	return True



# get distances from this brick to lower bricks - in 3D space.
def getClosestTwoBricks3D(thisbrick, index):
	global BrickList

	thisdistances = map(lambda x: thisbrick.getDistance3D(x), BrickList[index])
	#okay, get the indices of the closest midpoint (sort and return keys)

	closestIndex = sorted(range(len(thisdistances)), key=lambda k: thisdistances[k])[0:2]

	#okay, get the locations of the cloeset lower bricks
	return [BrickList[index][i] for i in closestIndex]




#get endpoints of bricks closest to midPoint
def closestEndPoints(midPoint, closestBricks, index):
	global CourseList

	print midPoint
	midPointParam = CourseList[index].getClosestParameterFromPoint(midPoint)
	closestEndpointParams = [[eachlist - (BrickWidth / 2), eachlist + (BrickWidth / 2)] for eachlist in map(lambda x: x.getLocationAsParameter(), closestBricks)]
	print "closest bricks = ",map(lambda x: x.getLocationAsParameter(), closestBricks)
	print "closest endpoints params=",closestEndpointParams	
	print midPointParam	



# find where to place bricks on top of these two closest bricks, taking bearing (rotation) into account
def findBrickBearingPlacement(closestBricks, index):
	global BrickList

	#get midpoint of bricks
	midPoint = closestBricks[0].getMidpoint3D(closestBricks[1])

	print closestBricks[0].getFacingEndpoints3D(closestBricks[1])

	#get closest point on line to this midpoint
	closestParam = rs.CurveClosestPoint(ContourCurves[index], midPoint)
	closestMidPoint = rs.EvaluateCurve(ContourCurves[index], closestParam)

	#rotate brick
	rotation = 0

	newBrick = Brick3D(closestMidPoint, rotation, CourseList[index])

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
		if(brickToPlace.getDistance3D(aBrick) < (BrickWidth + BrickSpacingMin)):
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
	brickn = decideBrickNum(index)
	print brickn
	curvelen = rs.CurveLength(ContourCurves[index])
	#averageGap = (curvelen - (brickn * BrickWidth)) / brickn
	averageGap = (BrickSpacingMax + BrickSpacingMin) / 2

	if(rhythm == 0):
		provisionalLocation = 0
	else:
		provisionalLocation = index % rhythm	
	for i in xrange(brickn):
		# add a brick
		newBrick = Brick3D([0,0,0], 0.3, CourseList[index])
		newBrick.setLocationByParameter(provisionalLocation)
		BrickList[index].append(newBrick)
		
		# move the new location to the brick width, plus the gap
		provisionalLocation += BrickWidth + averageGap


def layStackingCourse(index):
	global BrickList
	global CourseList
	
	print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>PLACING BRICK COURSE", index
	print ">>>>>>>>> COURSE LEN = ", CourseList[index].length()
	brickn = decideBrickNum(index)

	if(index == 0):
		#we're the lowest line, place a normal Course
		layNormalCourse(index)	
	else:
		provisionalBrick = Brick3D([0,0,0], 0, CourseList[index])
		provisionalBrick.setLocationByParameter(0)

		print "PREVIOUS COURSE ="
		print map(lambda x: x.getLocationAsParameter(), BrickList[index-1])
		for i in xrange(brickn * 2): # this should be a while(True) loop but gh lets python run FOREVER so let's be safe

			#if we have two or more bricks on our floor below us
			if(len(BrickList[index - 1]) >= 2):

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

				print ">>>> PROVISIONAL BRICK #", i, "AT", provisionalBrick.getLocationAsParameter()

				# find two closest bricks 
				closestBricks = getClosestTwoBricks3D(provisionalBrick, index - 1)

				# find where to place bricks on top of these two closest bricks
				brickToPlace = findBrickBearingPlacement(closestBricks, index)

				# actually, for each pair of bricks, try to spread out
#				bricksToPlace = findBrickPlacements(closestBricks, index)

				#print ">>>> ACTUALLY IDEAL PLACEMENT IS AT", brickToPlace.getLocationAsParameter() , "/", CourseList[index].length()

				if(brickIsSupported(brickToPlace, closestBricks, index) and brickDoesNotOverlap(brickToPlace, index)):
					# place brick
					addBrickToCourse(brickToPlace, index)

				# move provisional point to new location
				provisionalBrick.setLocationByParameter(provisionalBrick.getLocationAsParameter() + BrickWidth)


		#print BrickList[index]
		print "okay, next course"


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
		layStackingCourse(i)
#	for i in xrange(len(CourseList)):
"""
	for i in xrange(len(CourseList)):
		for j in xrange(len(BrickList[i])):
			DebugList.append(BrickList[i][j].getLocationAsPoint())
			#DebugList.append(rs.EvaluateCurve(ContourCurves[i], BrickList[i][j].brickCenter))

"""

def outputCourses():
	global BrickList
	global BrickPoints
	global BrickPattern
	global BrickRotation
	#output what we've got
	BrickPattern = ListofListsToTree([map(lambda x: x.getLocationAsParameter(), alist) for alist in BrickList])
	BrickPoints = ListofListsToTree([map(lambda x: x.getLocationAsPoint(), alist) for alist in BrickList])
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

	print BrickPoints
if __name__ == "__main__":
	main()

