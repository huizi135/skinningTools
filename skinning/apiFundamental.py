import maya.cmds as mc
import maya.api.OpenMaya as om

def printVertsPos():
    for vert in mc.ls(selection=True, flatten=True):
        print(vert)
        pos = mc.xform(vert, translation=True, query=True, worldSpace=True)
        print(pos)
        index = vert.split("[")[-1][0]
        print(index)
        
def printVertsPos_MObject():
    selection = mc.MGlobal.getActiveSelectionList()
    mobject = selection.getDependNode(0)
    print(mobject)
    print(mobject.apiTypeStr)
    mfnMesh = om.MFnMesh(mobject)
    points = mfnMesh.getPoints(om.MSpace.kObject)
    for pt in points:
        print(pt)
    
def printVertsPos_MDagPath():
    selection = om.MGlobal.getActiveSelectionList()
    mDagPath = selection.getDagPath(0)
    print(mDagPath.fullPathName())
    mfnMesh = om.MFnMesh(mDagPath)
    points = mfnMesh.getPoints(om.MSpace.kWorld)
    for pt in points:
        print(pt)