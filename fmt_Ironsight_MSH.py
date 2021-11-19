#Ironsight - ".msh" plugin
#By 48464385/PeterZ
#Special thanks: zaramot
# v1.0 (November 8 2021) - Add static mesh and skeleton mesh (.msh)  support. Skeleton weight support.More research is need to support importing Normal.

from inc_noesis import *
import noesis
import rapi
import os
import glob
bAddRootBone=True

def registerNoesisTypes():
    handle = noesis.register("Ironsight", ".msh")
    noesis.setHandlerTypeCheck(handle, CheckType)
    # see also noepyLoadModelRPG
    noesis.setHandlerLoadModel(handle, LoadModel)
    noesis.logPopup()
    return 1

def CheckType(data):
    bs = NoeBitStream(data)
    idMagic = bs.readBytes(4)
    if idMagic != b'MESH':
        return 0
    return 1

def LoadModel(data, mdlList):
    ctx = rapi.rpgCreateContext()
    matList=[];bones=[]
    textureDirectory=os.path.split(rapi.getDirForFilePath(rapi.getInputName()))[0]
    #rapi.rpgSetOption(noesis.RPGOPT_TRIWINDBACKWARD, 1)
    bs = NoeBitStream(data)
    bs.seek(0x24)
    boneCount=bs.readUInt()
    print('BoneCount',str(boneCount))
    print('Bone Start',hex(bs.tell()))

    if(bAddRootBone):
        tmp=b'0000000000000000'
        bones.append(NoeBone(0, 'root', NoeQuat.fromBytes(tmp).toMat43(), None, -1))#add  rootBone
    for boneIndex in range(0,boneCount):
        boneName='bone'+str(boneIndex)
        getPos=bs.tell()+56
        boneHash=bs.readInt()
        unk=bs.readInt()
        boneParent=bs.readInt()
        x=bs.readFloat();y=bs.readFloat();z=bs.readFloat()
        boneMtx = NoeQuat.fromBytes(bs.readBytes(16)).toMat43()
        boneMtx.__setitem__(3,(x,y,z))
        if(bAddRootBone):
            newBone = NoeBone(boneIndex+1, boneName, boneMtx, None, int(boneParent)+1)
        else:
            newBone = NoeBone(boneIndex, boneName, boneMtx, None, int(boneParent))
        bones.append(newBone)
        bs.seek(getPos, NOESEEK_ABS)
    print('Bone End 0x',hex(bs.tell()))

    bs.readBytes(12)#padding

    meshCount=bs.readInt()
    matCount=bs.readInt()

    #Mesh Start
    for meshIndex in range(meshCount):
        rapi.rpgSetName("MESH" + str(meshIndex))
        print("Vertex",str(meshIndex),"start",hex(bs.tell()))
        bs.readBytes(8)#padding
        wShift=bs.readInt()
        vSecSize=bs.readInt()
        vertBuffStart=bs.tell()
        vertBuff = bs.readBytes(vSecSize)
        vertBuffEnd=bs.tell()
        if(wShift==2):#staticMesh
            rapi.rpgBindPositionBufferOfs(
                vertBuff, noesis.RPGEODATA_FLOAT, 28, 0)
            rapi.rpgBindUV1BufferOfs(
                vertBuff, noesis.RPGEODATA_SHORT, 28, 12)
        if(wShift==3):#skeletonMesh
            rapi.rpgBindPositionBufferOfs(
                vertBuff, noesis.RPGEODATA_FLOAT, 32, 0)
            rapi.rpgBindUV1BufferOfs(
                vertBuff, noesis.RPGEODATA_SHORT, 32, 12)
            rapi.rpgSetUVScaleBias(NoeVec3 ((32, 32, 32)),(0,0,0))
            # rapi.rpgBindBoneWeightBufferOfs(
            #     vertBuff, noesis.RPGEODATA_UBYTE, 32, 24, 4)
            # rapi.rpgBindBoneIndexBufferOfs(
            #     vertBuff, noesis.RPGEODATA_UBYTE, 32, 28, 4)
            bs.seek(vertBuffStart,NOESEEK_ABS)
            vwList=[]
            for j in range(0, vSecSize//32):
                bs.seek(24,NOESEEK_REL)
                vwNum = 3
                bidx = []
                bwgt = []
                tmpWeight=[]
                for i in range(3):
                    tmpWeight.append(bs.readUByte())#w3 w2 w1
                tmpWeight.reverse()#w1 w2 w3
                tmpWeight.append(bs.readUByte())#w1 w2 w3 w4
                
                tmpBoneIdx=[]
                for i in range(4):
                    bid=bs.readUByte()//3
                    #print('bone',hex(bs.tell()),bid)
                    tmpBoneIdx.append(bid)#b1 b2 b3 b4

                maxWeight=0
                for i in range(4):
                    maxWeight+=tmpWeight[i]
                
                if(True):
                    for i in range(4):
                        if(tmpWeight[i]>0):
                            if(bAddRootBone):
                                bidx.append(tmpBoneIdx[i]+1)
                            else:
                                bidx.append(tmpBoneIdx[i])
                            bwgt.append(tmpWeight[i])
                        else:
                            bidx.append(-1)
                            bwgt.append(0)
                    #print(bidx,bwgt)
                vwList.append(NoeVertWeight(bidx, bwgt))
            fw = NoeFlatWeights(vwList)
            rapi.rpgBindBoneIndexBuffer(fw.flatW[:fw.weightValOfs], noesis.RPGEODATA_INT, 4*fw.weightsPerVert, fw.weightsPerVert)
            rapi.rpgBindBoneWeightBuffer(fw.flatW[fw.weightValOfs:], noesis.RPGEODATA_FLOAT, 4*fw.weightsPerVert, fw.weightsPerVert)

            bs.seek(vertBuffEnd,NOESEEK_ABS)


        FSecSize=bs.readInt()
        faceBuff = bs.readBytes(FSecSize)
        #print(FSecSize//6)
        rapi.rpgCommitTriangles(
            faceBuff, noesis.RPGEODATA_USHORT, FSecSize//2, noesis.RPGEO_TRIANGLE, 1)
        rapi.rpgClearBufferBinds()
    #Mesh End

    #   #Material Start
    #   try:
    #       matCount=bs.readUInt()
    #       for matIndex in range(matCount):
    #           matMagic=bs.readBytes(4)#MTRL
    #           bs.readBytes(128)
    #           texs=[]
    #           for i in range(14):
    #               texturePathSize = bs.readUInt()
    #               texPathName=noeStrFromBytes(bs.readBytes(texturePathSize), 'euc-kr')
    #               if(texPathName):
    #                   texName=os.path.split(texPathName)[1]
    #                   texs.append(os.path.join(textureDirectory,texName))
    #                   print(texs)
    #           material = NoeMaterial('Material'+str(matIndex), "")
    #           material.setTexture(texs[0])
    #           matList.append(material)
    #           rapi.rpgSetMaterial(texs[0])
    #           bs.readBytes(8)
    #   except:
    #       pass
    #   #Material End
        
    
    mdl = rapi.rpgConstructModel()
    mdl.setModelMaterials(NoeModelMaterials([], matList))
    mdlList.append(mdl)
    mdl.setBones(bones)
    return 1



