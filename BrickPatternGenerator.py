
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

def isBrickOverlapping(thisBrickLocation, index, isClosedCurve=False, curvelen=0):
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

	betweendistances = [] 
	isCurveClosed = rs.IsCurveClosed(ContourCurves[index])
	curveLen = rs.CurveLength(ContourCurves[index])

	sortedBrickList =  sorted(BrickList[index], key=lambda k: k.getLocationAsParameter())
	for i in xrange(1, len(sortedBrickList)):
		if(sortedBrickList[i - 1].getDistanceOnCurve(sortedBrickList[i]) < BrickWidth):
			return True
	return False


# get distances from this brick to lower bricks - in 3D space.
def getClosestTwoBricks3D(thisbrick, index):
	global BrickList

	thisdistances = map(lambda x: thisbrick.getDistance3D(x), BrickList[index])
	#okay, get the indices of the closest midpoint (sort and return keys)

	closestIndex = sorted(range(len(thisdistances)), key=lambda k: thisdistances[k])[0:2]

	#okay, get the locations of the cloeset lower bricks
	return [BrickList[index][i] for i in closestIndex]


# find where to place bricks on top of these two closest bricks
def findBrickPlacement(closestBricks, index):
	global BrickList

	#get midpoint of bricks
	midPoint = closestBricks[0].getMidpoint3D(closestBricks[1])

	#get closest point on line to this midpoint
	closestParam = rs.CurveClosestPoint(ContourCurves[index], midPoint)
	closestPoint = rs.EvaluateCurve(ContourCurves[index], closestParam)

	#rotate brick
	rotation = 0

	newBrick = Brick3D(closestPoint, rotation, CourseList[index])
	return newBrick


# check if we can place brick.
def canPlaceBrick(brickToPlace, index):
	global BrickList
	# TO IMPLEMENT
	return True

# place brick
def addBrickToCourse(brickToPlace, index):
	global BrickList
	BrickList[index].append(copy.deepcopy(brickToPlace))

def placeNormalCourse(index, brickn):	
	global BrickList
	curvelen = rs.CurveLength(ContourCurves[index])
	averageGap = (curvelen - (brickn * BrickWidth)) / brickn
	
	thisBrickLocation = 0
	for i in xrange(brickn):
		# add a brick
		newBrick = Brick3D([0,0,0], 0, CourseList[index])
		newBrick.setLocationByParameter(thisBrickLocation)
		BrickList[index].append(newBrick)
		
		# move the new location to the brick width, plus the gap
		thisBrickLocation += BrickWidth + averageGap


def layBrickCourse(index):
	global BrickList
	
	print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>PLACING BRICK COURSE", index
	brickn = decideBrickNum(index)

	if(index == 0):
		#what the what, we're the lowest line
		#how many bricks can we make?
		placeNormalCourse(index, brickn)	
		print ">>>> PLACED NORMAL COURSE"		
	else:
		provisionalBrick = Brick3D([0,0,0], 0, CourseList[index])
		provisionalBrick.setLocationByParameter(0)

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

				# set a provisional brick 
				# ====> provisionalBrick

				print ">>>> PROVISIONAL BRICK #", i, "AT", provisionalBrick.getLocationAsParameter()

				# find two closest bricks 
				closestBricks = getClosestTwoBricks3D(provisionalBrick, index - 1)
				# find where to place bricks on top of these two closest bricks
				brickToPlace = findBrickPlacement(closestBricks, index)

				print ">>>> ACTUALLY IDEAL PLACEMENT IS AT", brickToPlace.getLocationAsParameter()

				if(canPlaceBrick(brickToPlace, index)):
					# place brick
					print "* PLACED BRICK"
					addBrickToCourse(brickToPlace, index)

				# move provisional point to new location
				provisionalBrick.setLocationByParameter(provisionalBrick.getLocationAsParameter() + BrickWidth)

				# and if we can't place any more, get out of this
				if(isCourseFull(index)):
					continue

		print BrickList[index]
		print "okay, next course"


def processCourses():
	for i in xrange(len(ContourCurves)):
		CourseList.append(Course(ContourCurves[i]))		



def layCourses():
	for i in xrange(len(CourseList)):
		layBrickCourse(i)

	for i in xrange(len(CourseList)):
		for j in xrange(len(BrickList[i])):
			DebugList.append(BrickList[i][j].getLocationAsPoint())
			#DebugList.append(rs.EvaluateCurve(ContourCurves[i], BrickList[i][j].brickCenter))



def outputCourses():
	global BrickList
	#output what we've got
	BrickPattern = ListofListsToTree([map(lambda x: x.brickCenter, alist) for alist in BrickList])
	BrickPoints = ListofListsToTree([map(lambda x: x.getLocationAsPoint(), alist) for alist in BrickList])
	BrickRotation = ListofListsToTree([map(lambda x: x.brickRotation, alist) for alist in BrickList])
		

"""
###############################
###############################
###############################
###############################
INPUTS:
ContourCurves
BrickWidth
GapDomain
MinTributary

OUTPUTS:
BrickPattern
BrickPoints
BrickRotation
"""


def main():

	processCourses()
	layCourses()
	outputCourses()


	print BrickPoints
if __name__ == "__main__":
	main()

