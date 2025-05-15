import maya.cmds as mc
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

def getMObject(node):
    selectionList = om.MSelectionList()
    selectionList.add(node)
    return selectionList.getDependNode(0)

def getMfnSkinCluster(skincluster):
    """
    :param skincluster(str): the name of the skincluster node
    :return: functionset of skincluster object
    """
    mObject = getMObject(skincluster)
    mfnSkinCluster = oma.MFnSkinCluster(mObject)
    return mfnSkinCluster

def getInfluences(skincluster):
    mfnSkinCluster = getMfnSkinCluster(skincluster)
    influences = [inf.partialPathName() for inf in mfnSkinCluster.influences()]
    return influences, influences.__len__()

def getGeomInfo(mfnSkinCluster):
    dagPath = mfnSkinCluster.getPathAtIndex(0)
    meshVertItFn = om.MItMeshVertex(dagPath)
    #interator, you can get all the vertices index
    indices = range(meshVertItFn.count())
    
    # turn index into MObject
    singleIdComp = om.MFnSingleIndexedComponent()
    vertComp = singleIdComp.create(om.MFn.kMeshVertComponent)
    singleIdComp.addElements(indices)
    return dagPath, vertComp

def getSkinweights(skincluster, influences=None):
    mfnSkinCluster = getMfnSkinCluster(skincluster)
    meshDagPath, vertComp = getGeomInfo(mfnSkinCluster)
    if not influences:
        weightsArray, influenceCount = mfnSkinCluster.getWeights(meshDagPath, vertComp)
    else:
        influencesArray = om.MIntArray()
        influenceObjects = mfnSkinCluster.influenceObjects()
        influencePartialNames = [inf.partialPathName() for inf in influenceObjects]
        for inf in influenceObjects:
            if inf in influencePartialNames:
                index = influencePartialNames.index(inf)
                influencesArray.append(index)
        weightsArray = mfnSkinCluster.getWeights(meshDagPath, vertComp, influencesArray)
    return weightsArray

def setSkinweights(skincluster, weightsArray):
    mfnSkinCluster = getMfnSkinCluster(skincluster)
    meshDagPath, vertComp = getGeomInfo(mfnSkinCluster)
    _, influenceCount = getInfluences(skincluster)
    infIndexes = om.MIntArray()
    for index in range(influenceCount):
        infIndexes.append(index)
    weightsArray = om.MDoubleArray(weightsArray)
    oldWeights = mfnSkinCluster.setWeights(meshDagPath, vertComp, infIndexes,
                                           weightsArray, normalize= True,
                                           returnOldWeights=True)
    return oldWeights
    

























