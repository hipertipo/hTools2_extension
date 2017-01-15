#!/usr/local/bin/python

#############################################################################
#
#   v0.900 2011-06-06
#
#   Copyright 2011 Karsten Luecke
#   All rights reserved.
#
#   No warranties. By using this you agree
#   that you use it at your own risk!
#
#   http://www.kltf.de/kltf_otproduction.htm
#
#############################################################################

''' OPTIONS '''
METADATA_EXTENSION = ".woff.xml"
VERSION_NUMBER     = "1.0"
''' OPTIONS '''

#############################################################################

import sys, os, zlib
from struct import unpack,pack
from copy import deepcopy
from math import log

#############################################################################

def makelargestPowerOfTwo(pairsNumber):
    # searchRange,rangeShift,entrySelector = makelargestPowerOfTwo(subtablePairsNumber)
    exp = 0
    largestPowerOfTwo = 0
    while largestPowerOfTwo <= pairsNumber:
        exp += 1
        largestPowerOfTwo = 2 ** exp
    if largestPowerOfTwo > pairsNumber:
        exp -= 1
        largestPowerOfTwo /= 2
    return largestPowerOfTwo,pairsNumber-largestPowerOfTwo,exp
    # NOTE:
    # For the kern table,
    # "largestPowerOfTwo" and
    # "pairsNumber-largestPowerOfTwo"
    # must be multiplied by the
    # "size in bytes of an entry in the table" (kern table specs),
    # i.e. *6 in the kern table
    # (2 bytes each per left gid, right gid, kern value)!

def calculateTableLength(table):
    uLONG  = 4
    uSHORT = 2
    tableLength      = len(table)
    tableLengthPadd  = (tableLength/uLONG)*uLONG
    return int(tableLength), int(tableLengthPadd)

def calculateTableChecksum(tablePadd,tableLengthPadd):
    uLONG  = 4
    uSHORT = 2
    checksum = 0
    uLongs   = range(tableLengthPadd/uLONG)
    for u in uLongs:
        checksum += unpack('>L',tablePadd[u*uLONG:(u+1)*uLONG])[0]
    checksum &= 0xFFFFFFFF
    return int(checksum)

def paddTableCalculateChecksum(table,tablename=0,checksum=True):
    uLONG  = 4
    uSHORT = 2
    # table lengths:
    tableLength,     \
    tableLengthPadd  = calculateTableLength(table)
    # padd table:
    if tableLengthPadd < tableLength: tableLengthPadd += uLONG
    tablePaddDiff    = tableLengthPadd - tableLength
    tablePadd        = table + tablePaddDiff*"\0"
    # checksum:
    if checksum:
        if tablename == "head":  tableChecksum = calculateTableChecksum( tablePadd[:2*uLONG] + '\0'*4 + tablePadd[3*uLONG:] , tableLengthPadd ) # set the checksumadjustment to zero
        else:                    tableChecksum = calculateTableChecksum( tablePadd                                          , tableLengthPadd )
    else:
        tableChecksum = 0
    # return:
    return tablePadd, int(tableLength), int(tableLengthPadd), int(tableChecksum)

def calculateHeadChecksumAdjustment(font,headTableOffset=0):
    # input is complete-binary-font plus offset-to-head-table
    if not headTableOffset:
        # returns font-with-(un)adjusted-checksum plus adjusted-checksum
        return deepcopy(font),0
    uLONG  = 4
    uSHORT = 2
    # this is superfluous since I only needed "fontLengthPadd" from this ...:
    fontPadd,fontLength,fontLengthPadd,fontChecksum = paddTableCalculateChecksum(font,tablename=0,checksum=False)
    fontChecksum = 0xB1B0AFBA - calculateTableChecksum( fontPadd[:headTableOffset+2*uLONG] + '\0'*4 + fontPadd[headTableOffset+3*uLONG:], fontLengthPadd ) # font is assumed to be padded
    fontChecksum &= 0xFFFFFFFF
    fontLength = None; fontLengthPadd = None
    # returns font-with-adjusted-checksum plus adjusted-checksum
    return fontPadd[:headTableOffset+2*uLONG] + pack('>L',fontChecksum) + fontPadd[headTableOffset+3*uLONG:], int(fontChecksum)

#############################################################################

def compressFont(filename,outfilename=0,version=0,metadata=0,privatedata=0):
    #versioning:
    version_major = 1
    version_minor = 0
    if version:
        if "." in version:
            version_major, \
            version_minor  = version.split(".")[:2]
            if not len(version_major):  version_major = 0
            else:                       version_major  = int(version_major)
            if not len(version_minor):  version_minor = 0
            else:                       version_minor  = int(version_minor)
        else:
            version_major = int(version.strip())
            version_minor = 0
    # constants:
    uLONG  = 4
    uSHORT = 2
    OTVersions        = ["\000\001\000\000", "\x00\x01\x00\x00", "OTTO"]
    TT                = ["\000\001\000\000", "\x00\x01\x00\x00"]
    OT                = "OTTO"
    OTHeaderLength    = 1*uLONG + 4*uSHORT
    OTDirEntryLength  = 4*uLONG
    ZOTSignature      = "wOFF"
    ZOTHeaderLength   = 11*uLONG
    ZOTDirEntryLength = 5*uLONG
    # open font:
    if os.path.isdir(filename) or not os.path.exists(filename):
        return
    else:
        theFile = open( filename,"rb" )
        data = theFile.read()
        theFile.close()
    # read font head:
    OTVersion = data[:4]
    if OTVersion not in OTVersions:
        print "'%s' is not an OpenType font and will not be compressed!" % os.path.basename(filename)
        return
    #print "... woffing '%s' ..." % os.path.basename(filename)
    # total OTF size:
    OTTotalTablesSize       = int(len(data))
    # read directory:
    OTTableNumberBINARY     = data[ 2*uSHORT : 3*uSHORT ]
    OTTableNumber           = unpack( '>H', OTTableNumberBINARY )[0]
    # search range, entry selector, ranges shift completely omitted!
    # (why not add complete header, then compress tables? dito, then for TTC ...)
    OTTableDirectoryBINARY  = data[ OTHeaderLength : OTHeaderLength+OTTableNumber*OTDirEntryLength ]
    # create ZOT table directory
    # and ZOT tables:
    # counters:
    ZOTTableDirectoryLength = ZOTDirEntryLength * OTTableNumber
    ZOTCurrentTableOffset   = int(ZOTHeaderLength+ZOTTableDirectoryLength)
    # data:
    ZOTTableDirectoryBINARY = []
    ZOTTablesBINARY         = []
    # get original order:
    tablesInOriginalOrder   = []
    for t in range(OTTableNumber):
        tagBINARY              = data[ OTHeaderLength+t*OTDirEntryLength         : OTHeaderLength+t*OTDirEntryLength+1*uLONG ]
        checksumBINARY         = data[ OTHeaderLength+t*OTDirEntryLength+1*uLONG : OTHeaderLength+t*OTDirEntryLength+2*uLONG ]
        offsetBINARY           = data[ OTHeaderLength+t*OTDirEntryLength+2*uLONG : OTHeaderLength+t*OTDirEntryLength+3*uLONG ]
        lengthBINARY           = data[ OTHeaderLength+t*OTDirEntryLength+3*uLONG : OTHeaderLength+t*OTDirEntryLength+4*uLONG ]
        offset                 = unpack( '>L', offsetBINARY )[0]
        length                 = unpack( '>L', lengthBINARY )[0]
        table                  = data[ offset : offset+length ]
        tablesInOriginalOrder += [(   deepcopy(offsetBINARY), (deepcopy(tagBINARY),deepcopy(checksumBINARY),deepcopy(offsetBINARY),deepcopy(lengthBINARY),deepcopy(offset),deepcopy(length),deepcopy(table))   )]
    t = None; tagBINARY = None; checksumBINARY = None; offsetBINARY = None; lengthBINARY = None; offset = None; length = None; table = None
    tablesInOriginalOrder.sort() # i.e. by offsets!
    # fill:
    for t in tablesInOriginalOrder:
        tagBINARY,      \
        checksumBINARY, \
        offsetBINARY,   \
        lengthBINARY,   \
        offset,         \
        length,         \
        table           = t[1] # we skip the original offsetBINARY
##      print "   %s" % "".join(unpack('cccc',tagBINARY))
        ZOTTable        = zlib.compress( table, 9 ) # level 1-9

        # temp test checksum -----
        if tagBINARY == "head":
            headChecksumAdjustment = unpack( '>L', table[2*uLONG:3*uLONG])[0]
            headOffset             = int(offset)
        trash1,\
        trash2,\
        trash3,\
        cs = paddTableCalculateChecksum(table,tablename=tagBINARY)
#       print tagBINARY,unpack(">L",checksumBINARY)[0],cs
        # temp test checksum -----

        # padding, just in case:
        OTTestLength,  OTTestLengthPadd  = calculateTableLength(    table )
        ZOTTestLength, ZOTTestLengthPadd = calculateTableLength( ZOTTable )
        # add to table directory and tables:
        if ZOTTestLength     < OTTestLength: # then it was compressed
#       if ZOTTestLengthPadd < OTTestLengthPadd: # then it was compressed
#           print "     (compressed: %s -> %s)" % (OTTestLength,ZOTTestLength)
#           print
            ZOTTable,      \
            ZOTLength,     \
            ZOTLengthPadd, \
            trash1         = paddTableCalculateChecksum( ZOTTable )
            ZOTTableDirectoryBINARY += [( deepcopy(tagBINARY), "".join([
                tagBINARY,                           # tag
                pack( '>L', ZOTCurrentTableOffset ), # new offset
                pack( '>L', ZOTLength ),             # compLength
                lengthBINARY,                        # origLength
                checksumBINARY,                      # origChecksum
            ]) )]
            ZOTTablesBINARY += [ ZOTTable ]
            ZOTCurrentTableOffset += ZOTLengthPadd
        else: # then it was not compressed
##          print "     (note: table not compressed)"
#           print
            table,        \
            trash1,       \
            OTLengthPadd, \
            trash2        = paddTableCalculateChecksum(table)
            ZOTTableDirectoryBINARY += [( deepcopy(tagBINARY), "".join([
                tagBINARY,                           # tag
                pack( '>L', ZOTCurrentTableOffset ), # new offset
                lengthBINARY,                        # compLength =  # comp (UNpadded original) 9
                lengthBINARY,                        # origLength =  # orig (umpadded original) 9
                checksumBINARY,                      # origChecksum
            ]) )]
            ZOTTablesBINARY += [ table ]
            ZOTCurrentTableOffset += OTLengthPadd
    t = None

    # checksum test -----
    newFont,totalchecksum = calculateHeadChecksumAdjustment(data,headOffset)
#   print "\nhead"
#   print headChecksumAdjustment
#   print totalchecksum
    # checksum test -----

    # add meta data:
    ZOTMetaOffset     = 0
    ZOTMetaLength     = 0
    ZOTMetaLengthOrig = 0
    # find and open metadata:
    if not metadata:
        metaPath = os.path.splitext(filename)[0] + METADATA_EXTENSION
        if os.path.isfile(metaPath) and os.path.exists(metaPath):
            metaFile = open( metaPath,"rb" )
            metadata = metaFile.read()
            metaFile.close()
        else:
            metadata = 0
    if metadata:
        # load xml file:
        # measure, compress and write:
        ZOTMetaLengthOrig      = len(metadata)
        ZOTMeta                = zlib.compress( metadata, 9 ) # level 1-9
        ZOTMeta,               \
        ZOTMetaLength,         \
        ZOTMetaLengthPadd,     \
        trash1                 = paddTableCalculateChecksum( ZOTMeta )
        ZOTTablesBINARY       += [ ZOTMeta ]
        ZOTMetaOffset          = int(ZOTCurrentTableOffset)
        ZOTCurrentTableOffset += ZOTMetaLengthPadd
#       print metadata
#       print ZOTMeta
#       print ZOTMetaOffset
#       print ZOTMetaLength
#       print ZOTMetaLengthPadd
#       print ZOTMetaLengthOrig
    # add private data:
    ZOTPrivateOffset     = 0
    ZOTPrivateLength     = 0
    ZOTPrivateLengthPadd = 0
    if privatedata:
        ZOTPrivate             = zlib.compress( privatedata, 9 ) # level 1-9
        privatedata,           \
        ZOTPrivateLength,      \
        ZOTPrivateLengthPadd,
        trash1                 = paddTableCalculateChecksum(privatedata)
        ZOTTablesBINARY       += [ privatedata ]
        ZOTPrivateOffset       = int(ZOTCurrentTableOffset)
        ZOTCurrentTableOffset += ZOTPrivateLengthPadd
    # sort and finalize OTTableDirectoryBINARY:
    ZOTTableDirectoryBINARY.sort()
    ZOTTableDirectoryBINARY = [ ZOTTableDirectoryBINARY[i][1] for i in range(len(ZOTTableDirectoryBINARY)) ] ; i = None
    # create ZOT header:
    ZOTHeaderBINARY = [
        ZOTSignature,                                #  0 signature
        OTVersion,                                   #  1 flavor
        pack( '>L', ZOTCurrentTableOffset ),         #  2 length
        pack( '>H', OTTableNumber ),                 #  3 numTables
        pack( '>H', 0 ),                             #  reserved
        pack( '>L', OTTotalTablesSize ),             #  4 totalOTFSize
        pack( '>H', version_major ),                 #  5 major version
        pack( '>H', version_minor ),                 #    minor version
        pack( '>L', ZOTMetaOffset ),                 #  6 metaOffset
        pack( '>L', ZOTMetaLength ),                 #  7 metaLength
        pack( '>L', ZOTMetaLengthOrig ),             #  8 metaOrigLength
        pack( '>L', ZOTPrivateOffset ),              #  9 privOffset
        pack( '>L', ZOTPrivateLength ),              # 10 privLength
    ]
    ZOTHeaderBINARY += ZOTTableDirectoryBINARY
    ZOTHeaderBINARY += ZOTTablesBINARY
    ZOTHeaderBINARY = "".join(ZOTHeaderBINARY)
    if len(ZOTHeaderBINARY) != ZOTCurrentTableOffset:
        print
        print "error with length:"
        print "ZOTHeaderBINARY length",len(ZOTHeaderBINARY)
        print "ZOTCurrentTableOffset", ZOTCurrentTableOffset
    # save it:
    if outfilename:  zotfile =               outfilename
    else:            zotfile = os.path.splitext(filename)[0] + ".woff"
    if os.path.exists( zotfile ):
        os.remove( zotfile )
    directory = os.path.dirname( zotfile )
    if not os.path.exists( directory ):
        os.makedirs( directory )
    theFile = open( zotfile ,"wb")
    theFile.write( ZOTHeaderBINARY )
    theFile.close()
    # tidy up:
    ZOTHeaderBINARY = None; ZOTTablesBINARY = None; ZOTTableDirectoryBINARY = None; ZOTMeta = None; trash1 = None; trash2 = None

#############################################################################

def getInputOutputFiles(inputPath):
    allowedSuffixes  = [".ttf",".otf"]
    inputOutputFiles = []
    if os.path.isdir(inputPath):
        print "ispath"
        files    = os.listdir(inputPath)
        for file in files:
            thispath = os.path.join(inputPath,file)
            if  (os.path.splitext(thispath)[1].lower() in allowedSuffixes) \
            and (file[0] != ".") :
                outpath = os.path.join( os.path.dirname(thispath) , "WOFF" , os.path.splitext(file)[0]+".woff" )
                inputOutputFiles += [(thispath,outpath)]
    else:
            file = os.path.basename(inputPath)
            thispath = os.path.join(inputPath,file)
            thispath = inputPath
            if  (os.path.splitext(thispath)[1].lower() in allowedSuffixes) \
            and (file[0] != ".") :
                outpath = os.path.join( os.path.dirname(thispath) ,        os.path.splitext(thispath)[0]+".woff" )
                inputOutputFiles += [(thispath,outpath)]
    return inputOutputFiles

#############################################################################

def doit():
    global VERSION_NUMBER
    args = sys.argv
    if len(args) < 2:
        print "ERROR: You forgot to provide a font folder!"
        return
    for aIdx in range(len(args)-1,-1,-1):
        if args[aIdx].lower() == "-v" and len(args) > aIdx+2:
            VERSION_NUMBER = args[aIdx+1].strip()
            del args[aIdx]
            del args[aIdx+1]
    foldername = args[1]
    fontfiles = getInputOutputFiles(foldername)
    if not len(fontfiles):
        print "ERROR: No .ttf or .otf fonts found!"
        return

    for inoutfile in fontfiles:
        print inoutfile ##
        compressFont(inoutfile[0],outfilename=inoutfile[1],version=VERSION_NUMBER)

    print "\nFinished!"

#############################################################################

if __name__ == "__main__":
    doit()

#############################################################################


