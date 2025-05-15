import os.path
from fileinput import filename

import maya.cmds as mc

skinWeightIO_plugin = os.path.join(os.path.dirname(__file__), "skinWeightIO.py")

def getSelMeshes():
    nodes = mc.ls(selection=True, type=["transform", "mesh"])
    #avoid duplicates
    selMeshes = set()
    for node in nodes:
        if mc.nodeType(node) == 'transform':
            shapes = mc.listRelatives(node, type="mesh", shapes=True, noIntermediate=True) or []
            selMeshes.update(shapes)
        elif mc.nodeType(node) in "mesh":
            selMeshes.add(node)
    return list(selMeshes)

def importExportSkinWeights(meshes=None, doImport=True, outputDir=None, doAncestorSwap=False, replace=[], target=[]):
    if not mc.pluginInfo(skinWeightIO_plugin, query=True, loaded=True):
        try:
            mc.loadPlugin(skinWeightIO_plugin)
            print(f"plugin '{skinWeightIO_plugin}' loaded successfully.")
        except Exception as e:
            print(f"Failed to load plugin '{skinWeightIO_plugin}': {e}")
            
    if meshes:
        mc.select(meshes)
        
    meshes = getSelMeshes()
    
    if not meshes:
        mc.warning("No meshes provided or selected, please select a mesh to proceed.")
        return
    
    if not outputDir:
        scenePath = mc.file(query=True, sceneName=True)
        if not scenePath:
            raise RuntimeError("please save the scene or specify an output path to proceed.")
        outputDir = os.path.dirname(scenePath)
        
    for mesh in meshes:
        outputPath = os.path.join(outputDir, f"{mesh}.wts")
        mc.skinWeightIO(mesh, filename=outputPath, load=doImport, save=not doImport, doAncestorSwap=doAncestorSwap,
                        replace=replace, target=target)
        