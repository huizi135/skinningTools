import maya.cmds as mc
import maya.api.OpenMaya as om
from . import skinLib as lib

def checkMaxInfluences(mesh, maxInfs=4):
    skincluster = lib.getSkinclusterFromMesh(mesh)
    if not skincluster:
        om.MGlobal.displayWarning("There is no skincluster attached to the {}".format(mesh))
        return
        
    skincluster = skincluster[0]
    weightsArray = lib.getSkinweights(skincluster)
    influences, influencesCount = lib.getInfluences(skincluster)
    vertsAboveMaxInfs = []
    for idx in range(0, len(weightsArray), influencesCount):
        """
        (inf1, inf2, inf3, inf4), (inf1, inf2, inf3, inf4)....
        """
        infcount = 0
        weightsPerComponnet = weightsArray[idx: idx + influencesCount]
        for weight in weightsPerComponnet:
            if weight > 0:
                infcount += 1
        
        if infcount > maxInfs:
            vertsAboveMaxInfs.append(idx // influencesCount)
            
    #for selection...
    fnVertComp = om.MFnSingleIndexedComponent()
    vertComp = fnVertComp.create(om.MFn.kMeshVertComponent)
    fnVertComp.addElements(vertsAboveMaxInfs)
    mSelection = om.MSelectionList()
    mSelection.add(mesh)
    meshDagPath = mSelection.getDagPath(0)
    mSelection.merge(meshDagPath, vertComp)
    selectString = list(mSelection.getSelectionStrings()[1:])
    mc.select(selectString)
    return selectString

# clamp skin influence
def pruneToMaxInflueness(mesh, verts=None, maxInfs=None):
    """
    take the remainder of weight from the joints with the smallest weights
    that dont meet the max influences criteria and distributes it (weighted) across the remaining joints
    :param mesh:
    :param verts:
    :param maxInfs:
    :return:
    """
    skincluster = lib.getSkinclusterFromMesh(mesh)
    if not skincluster:
        
        return
    else:
        skincluster = skincluster[0]
        
    skinFn = lib.getMfnSkinCluster(skincluster)
    
    #get max influences count from skincluster if maxInfs parameter is None
    if maxInfs is None:
        maxInfs = mc.skinCluster(skincluster, q=True, maximumInfluences=True)
        
    # add vertex indices to component
    mSelection = om.MSelectionList()
    if verts:
        verts = mc.filterExpand(verts, selectionMask=31)
        if not verts:
            raise RuntimeError("No valid vertices were provided or the selection could not be"
                               "expanded to valid vertex component")
        for vert in verts:
            mSelection.add(vert)
        shapeDagPath, vertexComp = mSelection.getComponent(0)
    else:
        #get geometry information
        shapeDagPath, vertetxComp = lib.getGeomInfo(skinFn)
    
    #create array of influence indices
    influencesArray = om.MIntArray()
    influenceObjs = skinFn.influenceObjects()
    infCount = len(influenceObjs)
    for index in range(infCount):
        influencesArray.append(index)
    weights = skinFn.getWeights(shapeDagPath, vertexComp, influencesArray)
    
    #calulate new weight values
    weightsDict = {}
    for i in range(0, len(weights), infCount):
        """
        (inf1, inf2, inf3, inf4), (inf1, inf2, inf3, inf4)....
        """
        for j in range(infCount):
            weightsDict[j] = weights[i + j]
        #weightsDict: {infIndex1: weight1, infIndex2: weight2}
        # [(infIndex1: weight1), (infIndex2: weight2)]
        sortedWeights = sorted(list(weightsDict.items()), key=lambda w:w[1], reverse=True)
        # desending order: [(infIndex1: weight1), (infIndex2: weight2)]
        weightsSum = 0
        for item in sortedWeights[:maxInfs]:
            weightsSum += float(item[1])
        sumMultiplier = (1 / weightsSum)
        for x in range(infCount):
            sortedWeights[x] = (sortedWeights[x][0], (sortedWeights[x][1] * sumMultiplier * (x < maxInfs)))
            weights[i + sortedWeights[x][0] = sortedWeights[x][1]
    
    # set new skincluster weights
    skinFn.setWeights(shapeDagPath, vertetxComp, influencesArray, weights, False)
    
    return True
        





















