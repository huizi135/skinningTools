import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import re
import maya.cmds as mc

import os
import pickle

def maya_useNewAPI():
    """
    The presence of this function tells maya that the pulgin produces and expect to be passed, objects created using maya python api 2.0
    :return:
    """
    pass

KExportFlag = "-s"
KExportLongFlag = "-save"
KImportFlag = "-l"
KImportLongFlag = "-load"
KFileFlag = "-f"
KFileLongFlag = "-filename"
KReplaceFlag = "-re"
KReplaceLongFlag = "-replace"
KTargetListFlag = "-tgt"
KTargetListLongFlag = "-target"
KDoAncestorSwapFlag = "-das"
KDoAncestorSwapLongFlag = "-doAncestorSwap"
KHelpFlag = "-h"
KHelpLongFlag = "-help"
KPluginCmdName = "skinWeightIo"

class SkinWeightIOCmd(om.MPxCommand):
    def __init__(self):
        super(SkinWeightIOCmd, self).__init__()
        # flags
        self.doImport = False
        self.doExport = False
        self.fileName = None
        self.doAncestorSwap = False
        # internal data
        self.geomDagPath = None
        self.geomComponent = None
        self.influenceIds = None
        self.skinFn = None
        self.oldWeights = None
        self.replaceStringPair = []
        self.influenceTargetList = []
        
    @staticmethod
    def isUndoable():
        return True
    
    @staticmethod
    def hasSyntax():
        """
        what is MSyntax in Maya API?
        MSyntax is a class in the maya python api used to define the syntax (expected arguments and flags)
        for a custom command plug in
        
        when you create a custom maya command (using MPxCommand), you often need to allow users to pass arguments amd flags
        just like built-in commands, MSyntax helps define:
        
        Flag-based arguments(e.g., -name "myLocator" -size 10)
        
        Positional arguments(e.g., myCommand arg1 arg2)
        
        Types of arguments (int, float, string, boolean, etc.)
        
        Whether arguments are required or optional
        """
        return False
    
    def doIt(self, argList):
        argData = om.MArgDatabase(self.syntax(), argList)
        selectionList = argData.getObjectList()
        selectionStrings = selectionList.getSelectionStrings()
        
        if argData.isFlagSet(KFileFlag):
            self.fileName = argData.flagArgumentString(KFileFlag, 0)
            if argData.isQuery:
                skin_data = self.loadSkinData()
                if skin_data:
                    self.setResult(skin_data["partial_path_names"])
                else:
                    self.displayError("Skin data not valid.")
                return
            
        if argData.isFlagSet(KHelpFlag) or not self.getGeomInfoFromSelectionList(selectionStrings):
            self.printHelp()
            return
        
        if argData.isFlagSet(KImportFlag):
            self.doImport = argData.flagArgumentBool(KImportFlag, 0)
            
        if argData.isFlagSet(KExportFlag):
            self.doExport = argData.flagArgumentBool(KExportFlag, 0)
        
        if argData.isFlagSet(KReplaceFlag):
            replaceCount = argData.numberOfFlagUses(KReplaceFlag)
            if argData.numberOfFlagUses(KReplaceFlag) != 2:
                self.displayError('Replace flag requires a source and target string pair.')
                return
            
            for i in range(replaceCount):
                argList = argData.getFlagArgumentList(KReplaceFlag, i)
                self.replaceStringPair.append(argList.asString(0))
                
        if argData.isFlagSet(KTargetListFlag):
            if argData.numberOfFlagUses(KTargetListFlag):
                for i in range(argData.numberOfFlagUses(KTargetListFlag)):
                    argList = argData.getFlagArgumentList(KTargetListFlag, i)
                    self.influenceTargetList.append(argList.asString(0))
        
        self.redoIt()
        
    def undoIt(self):
        if self.oldWeights:
            self.skinFn.setWeights(self.geomDagPath, self.geomComponent, self.influenceIds, self.oldWeights)
    
    def redoIt(self):
        if self.doImport is self.doExport:
            self.printHelp()
            return
        
        elif self.doImport:
            result = self.importWeights()
        else:
            result = self.exportWeights()
            
        self.setResult(result)
        
    @staticmethod
    def printHelp():
        info = "Command Synopsis:\n"
        info += "skinWeightsIO(selectionList, [filename(f)=string], [load(1)=boolean], [save(s)=boolean]\n"
        info += "[help(h)=boolean])\n\n"
        info += "Note: selectionList maybe either a single mesh or a selection of vertices.\n"
        info += "If no argument provided command will use current maya selection.\n\n"
        info += "Parameters:\n"
        info += "\tload(1)        - If true sets command to load a skin weights file (cannot be used with save).\n"
        info += "\tsave(s)        - If true sets command to save a skin weights file (cannot be used with load).\n"
        info += "\tfilename(f)   - Path to file saved or loaded.\n"
        
        om.MGlobal.displayInfo(info)
    
    @staticmethod
    def commandSyntax():
        syntax = om.MSyntax()
        syntax.addFlag(KExportFlag, KExportLongFlag, om.MSyntax.KBoolean)
        syntax.addFlag(KImportFlag, KImportLongFlag, om.MSyntax.KBoolean)
        syntax.addFlag(KFileFlag, KFileLongFlag, om.MSyntax.KString)
        syntax.addFlag(KReplaceFlag, KReplaceLongFlag, om.MSyntax.KString)
        syntax.makeFlagMultiUse(KReplaceFlag)
        syntax.addFlag(KTargetListFlag, KTargetListLongFlag, om.MSyntax.KString)
        syntax.makeFlagMultiUse(KTargetListFlag)
        syntax.addFlag(KDoAncestorSwapFlag, KDoAncestorSwapLongFlag, om.MSyntax.KBoolean)
        syntax.useSelectionAsDefault(True)
        syntax.setObjectType(om.MSyntax.KSelectionList)
        syntax.addFlag(KHelpFlag, KHelpLongFlag, om.MSyntax.KBoolean)
        
        syntax.makeFlagsQueryWithFullArgs(KFileFlag, True)
        syntax.enableQuery = True
        
        return syntax
    
    @staticmethod
    def cmdCreator():
        return SkinWeightIOCmd()
    
    def getGeomInfoFromSelectionList(self, selectionList):
        # only collect the first valid geometry in selectionlist
        mSel = om.MSeletcionList()
        for sel in selectionList:
            if mc.objectType(sel) == "transform":
                shapes = mc.listRelatives(sel, shapes=True, noIntermediate=True)
                if not shapes:
                    return False
                
                if mc.objectType(shapes[0]) == "mesh":
                    sel = shapes[0] + '.vtx[*]'
                mSel.add(sel)
                break
                
            elif mc.objectType(sel) == 'mesh':
                if 'vtx' not in sel:
                    # select shape node
                    mSel.add(sel + '.vtx[*]')
                    break
                mSel.add(sel)
        
        if mSel.length():
            (self.geomDagPath, self.geomComponent) = mSel.getComponent(0)
            return True
        else:
            return False
        
    def importWeights(self):
        skinData = self.loadSkinData()
        if not skinData:
            return
        savedVertexCount = skinData['topology_vertex_count'] or None
        vertexCount = None
        
        if self.geomDagPath.apiType() == om.MFn.KMesh:
            components = set(om.MFnSingleIndexedComponent(self.geomComponent).getElements())
            vertexCount = len(components)
        
        if vertexCount and savedVertexCount:
            if vertexCount != savedVertexCount:
                raise RuntimeError("Mismatched topologies: mesh vertex count dose not match skin data vertex count")
            
        skincluster = mc.ls(mc.listHistory(self.geomDagPath.partialPathName()), type='skinCluster')
        
        if not skincluster:
            # get influences in the scene
            influences = mc.ls(skinData['partial_path_names'])
            if influences:
                skincluster = mc.skinCluster(influences, self.geomDagPath.partialPathName(),
                                             toSelectedBones=True)[0]
            else:
                raise RuntimeError('No Valid influences!')
        else:
            skincluster = skincluster[0]
        
        self.skinFn = self.getMfnSkinCluster(skincluster)
        
        self.checkInfluences(skinData)
        
        skinWeights, self.influenceIds = self.getInfluenceWeightMapping(skinData)
        
        self.oldWeights = self.skinFn.setWeights(self.geomDagPath,
                                                 self.geomComponent,
                                                 self.influenceIds,
                                                 skinWeights,
                                                 normalize=True,
                                                 returnOldWeights=True)
        mc.select(clear=True)
        return skinWeights
    
    def exportWeights(self):
        skinData = dict()
        skincluster = mc.ls(mc.listHistory(self.geomDagPath.partialPathName()), type='skinCluster')
        if skincluster:
            self.skinFn = self.getMfnSkinCluster(skincluster[0])
            skinData['partial_path_names'], skinData['full_path_names'], self.influenceIds = self.getInfluences(self.skinFn)
            skinData['weights'] = list(self.skinFn.getWeights(self.geomDagPath, self.geomComponent, self.influenceIds))
            
            if self.geomDagPath.apiType() == om.MFn.KMesh:
                skinData['components'] = list(set(om.MFnSingleIndexedComponent(self.geomComponent).getElements()))
            else:
                self.displayWarning("Invalid geometry type, only mesh or nurbsSurface is supported.")
        
        else:
            self.displayError("No skinCluster found on provided mesh.")
            self.printHelp()
            return
        
        skinData['topology_vertex_count'] = len(skinData['components'])
        
        if not os.path.isdir(os.path.dirname(self.fileName)):
            os.makedirs(os.path.dirname(self.fileName))
        
        with open(self.fileName, "wb") as skinDataFile:
            pickle.dump(skinData, skinDataFile)
        # fileName = self.fileName.replace(".weights", ".json")
        # with open(fileName, "w") as skinDataFile:
        #     json.dump(skinData, skinDataFile, indent=4)
        return skinData['weights']
    
    def checkInfluences(self, skinData):
        # iterate influences and remapping to parents if they dont exist
        missingInfluences = []
        
        skinDataInfluences = skinData['partial_path_names']
        influenceObjects = self.skinFn.influenceObjects()
        currentSkinInfluences = [influenceObjects.partialPathName() for influenceObject in influenceObjects]
        
        # if a valid target list is provided, use that influence list instead
        if self.influenceTargetList:
            if len(skinDataInfluences) == len(self.influenceTargetList):
                self.displayInfo(f"Mapping influences to target list."
                                 f"Replacing {skinDataInfluences} with {self.influenceTargetList}")
                # update the original list directly
                skinData['partial_path_names'][:] = self.influenceTargetList
            else:
                raise RuntimeError("Provided target list does not match influence count")
        
        for idx, influence in enumerate(skinDataInfluences):
            influence = self.replaceInfluence(influence)
            if mc.objExists(influence):
                if influence not in currentSkinInfluences:
                    mc.skinCluster(self.skinFn.name(), edit=True, addInfluence=influence, weight=0)
                    
                skinDataInfluences[idx] = influence
                # currentSkinInfluences.append(influence)
            elif self.doAncestorSwap:
                parent = self.findAncestorInfluence(skinData['full_path_name'][idx])
                if parent:
                    if parent not in currentSkinInfluences:
                        mc.skinCluster(self.skinFn.name(), edit=True, addInfluence=parent, weight=0)
                    skinDataInfluences[idx] = parent
                    self.displayInfo(f"Substituting {influence} for ancestor {parent}.")
                else:
                    self.displayError(influence + " and its ancestors are missing.")
                    missingInfluences.append(influence)
            
            else:
                missingInfluences.append(influence)
        
        if missingInfluences:
            error_message = "\n\nUnable to load skin weights! \n\nThe following influences were missing:\n"
            for influence in missingInfluences:
                error_message += "\t" + influence + "\n"
            raise RuntimeError(error_message)
        
    def findAncestorInfluence(self, influence_data):
        parentList = influence_data.split('|')[0:-1]
        for j in range(len(parentList) - 1, 0, -1):
            parent = parentList[j]
            parent = self.replaceInfluence(parent)
            if mc.objExists(parent) and mc.objectType(parent, isType='joint'):
                return parent
        return None
    
    def getInfluenceWeightMapping(self, skinData):
        skinDataInfluences = skinData['partial_path_names']
        # Get active influences as a check for missing ones
        influenceObjects = self.skinFn.influenceObjects()
        currentSkinInfluences = [influenceObject.partialPathName() for influenceObject in influenceObjects]
        
        # Return influences and weights if no need to remap
        if skinDataInfluences == currentSkinInfluences:
            ids = om.MIntArray(list(range(len(skinDataInfluences))))
            return om.MDoubleArray(skinData['weights']), ids
        
        # remap
        weights = skinData['weights']
        mappedWeights = []
        numInfluences = len(skinDataInfluences)
        for i in range(0, len(skinData['weights']), numInfluences):
            skinDataWeightSet = weights[i:i + numInfluences]
            newWeightSet = [0] * len(influenceObjects)
            # skinDataInfluences = ["joint1", "joint2", "joint4"]
            # skinDataWeightSet = [0.4, 0.2, 0.6]
            # influenceObjects = ["joint1", "joint2"]
            # newWeightSet = [0.4, 0.2]
            for j in range(len(influenceObjects)):
                influence = influenceObjects[j].partialPathName()
                newWeightSet[j] = sum(
                    skinDataWeightSet[i] for i, inf in enumerate(skinDataInfluences) if inf == influence
                )
        return om.MDoubleArray(mappedWeights), self.getInfluenceMap(influenceObjects)
    
    def getInfluenceMap(self, influenceObjects):
        influenceArray = om.MIntArray()
        for index, influence in enumerate(influenceObjects):
            influenceArray.append(index)
        return influenceArray
    
    def replaceInfluence(self, influence):
        # check if the influence name is replaced or not
        if self.replaceStringPair:
            renamedInfluence = re.sub(self.replaceStringPair[0], self.replaceStringPair[1], influence)
            if renamedInfluence != influence and mc.objExists(renamedInfluence):
                self.displayInfo(f"Substituting {influence} for influence {renamedInfluence}")
                influence = renamedInfluence
        return influence
    
    @staticmethod
    def getMfnSkinCluster(skinCluster):
        mSel = om.MSelectionList()
        mSel.add(skinCluster)
        oSkin = mSel.getDependNode(0)
        return oma.MFnSkinCluster(oSkin)
    
    @staticmethod
    def getInfluences(mfnSkin):
        partialPathNames = []
        fullPathNames = []
        influencesArray = om.MIntArray()
        for index, infDagPath in enumerate(mfnSkin.influenceObjects()):
            partialPathNames.append(infDagPath.partialPathName())
            fullPathNames.append(infDagPath.fullPathName())
            influencesArray.append(index)
        return partialPathNames, fullPathNames, influencesArray
    
    def loadSkinData(self):
        if not os.path.exists(self.fileName):
            raise IOError("File not found!")
        
        with open(self.fileName, "rb") as skinDataFile:
            skinData = pickle.load(skinDataFile)
        
        if 'partial_path_names' not in skinData or \
                'full_path_names' not in skinData or \
                'components' not in skinData:
            raise RuntimeError('Invalid weights files!')
        return skinData
    
    # initialize the script plug-in
    def initializePlugin(obj):
        mplugin = om.MFnPlugin(obj, "Huizi", "1.0", "Any")
        try:
            mplugin.registerCommand(KPluginCmdName, SkinWeightIOCmd.cmdCreator, SkinWeightIOCmd.commandSyntax)
            om.MGlobal.displayInfo(f"Registered command: {KPluginCmdName}")
        except Exception as e:
            om.MGlobal.displayError(f"Failed to register command: {KPluginCmdName} - {e}")
            
    # uninitialize the script plug-in
    def uninitializePlugin(obj):
        mplugin = om.MFnPlugin(obj)
        try:
            mplugin.deregisterCommand(KPluginCmdName)
            om.MGlobal.displayInfo(f"Deregistered command: {KPluginCmdName}")
        except Exception as e:
            om.MGlobal.displayError(f"Failed to deregister command: {KPluginCmdName} - {e}")
        
        






























































