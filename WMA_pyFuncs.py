#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
essentially, a python refactoring of the relevant parts of 
https://github.com/DanNBullock/wma_tools

Dan Bullock, Nov 11, 2020
"""

def makePlanarROI(reference, mmPlane, dimension):
    """makePlanarROI(reference, mmPlane, dimension):
    #
    # INPUTS:
    # -reference:  the nifti that the ROI will be
    # applied to, also functions as the source of affine transform.
    #
    # -mmPlane: the ACPC (i.e. post affine application) mm plane that you would like to generate a planar ROI
    # at.  i.e. mmPlane=0 and dimension= x would be a planar roi situated along
    # the midsaggital plane.
    #
    # -dimension: either 'x', 'y', or 'z', to indicate the plane that you would
    # like the roi generated along
    #
    # OUTPUTS:
    # -planarROI: the roi structure of the planar ROI
    #
    #  Daniel Bullock 2020 Bloomington
    #this plane will be oblique to the subject's *actual anatomy* if they aren't
    #oriented orthogonally. As such, do this only after acpc-alignment
    #
    #adapted from https://github.com/DanNBullock/wma_tools/blob/master/ROI_Tools/bsc_makePlanarROI_v3.m
    """
    import nibabel as nib
    import numpy as np
    import dipy.tracking.utils as ut
    
    fullMask = nib.nifti1.Nifti1Image(np.ones(reference.get_fdata().shape), reference.affine, reference.header)
    #pass full mask to subject space boundary function
    convertedBoundCoords=subjectSpaceMaskBoundaryCoords(fullMask)
    
    #create a dict to interpret input
    dimDict={'x':0,'y':1,'z':2}
    selectedDim=dimDict[dimension]
    
    #if the requested planar coordinate is outside of the image, throw a full on error
    if convertedBoundCoords[0,selectedDim]>mmPlane or convertedBoundCoords[1,selectedDim]<mmPlane: 
        raise ValueError('Requested planar coordinate outside of reference image')
    
    #not always 0,0,0
    subjectCenterCoord=np.mean(convertedBoundCoords,axis=0)
    #copy it over to be the plane center coord and replace with requested value
    planeCenterCoord=subjectCenterCoord.copy()
    planeCenterCoord[selectedDim]=mmPlane
    
    planeCoords=[]
    #i guess the only way
    for iDims in list(range(len(dimDict))):
        if iDims==selectedDim:
            #set the value to the plane coord in the relevant dimension
            planeCoords.append(mmPlane)
        else:
            #set step size at half the voxel length in this dimension
            stepSize=fullMask.header.get_zooms()[iDims]*.5
            #create a vector with the coords for this dimension
            dimCoords=np.arange(convertedBoundCoords[0,iDims],convertedBoundCoords[1,iDims],stepSize)
            #append it to the planeCoords list object
            planeCoords.append(list(dimCoords))
    x, y, z = np.meshgrid(planeCoords[0], planeCoords[1], planeCoords[2],indexing='ij')
    #squeeze the output (maybe not necessary)          
    planeCloud= np.squeeze([x, y, z])
    #convert to coordinate vector
    testSplit=np.vstack(planeCloud).reshape(3,-1).T
    #use dipy functions to treat point cloud like one big streamline, and move it back to image space
    lin_T, offset =ut._mapping_to_voxel(fullMask.affine)
    inds = ut._to_voxel_coordinates(testSplit, lin_T, offset)
    
    #create a blank array for the output
    outData=np.zeros(reference.shape).astype(bool)
    #set the relevant indexes to true
    #-1 because of zero indexing
    outData[inds[:,0]-1,inds[:,1]-1,inds[:,2]-1]=True
    #format output
    returnedNifti=nib.nifti1.Nifti1Image(outData, reference.affine, header=reference.header)
    return returnedNifti

def roiFromAtlas(atlas,roiNum):
    """roiFromAtlas(atlas,roiNum)
    #creates a nifti structure mask for the input atlas image of the specified label
    #
    #  DEPRICATED BY  multiROIrequestToMask
    #
    # INPUTS:
    # -atlas:  an atlas nifti
    #
    # -roiNum: an int input indicating the SINGLE label that is to be extracted.  Will throw warning if not present
    #
    # OUTPUTS:
    # -outImg:  a mask with int(1) in those voxels where the associated label was found.  If the label wasn't found, an empty nifti structure is output.
    """

    import numpy as np
    import nibabel as nib
    outHeader = atlas.header.copy()
    atlasData = atlas.get_fdata()
    outData = np.zeros((atlasData.shape)).astype(int)
    #check to make sure it is in the atlas
    #not entirely sure how boolean array behavior works here
    if  np.isin(roiNum,atlasData):
            outData[atlasData==roiNum]=int(1)
    else:
        import warnings
        warnings.warn("WMA.roiFromAtlas WARNING: ROI label " + str(roiNum) + " not found in input Nifti structure.")
                
    outImg = nib.nifti1.Nifti1Image(outData, atlas.affine, outHeader)
    return outImg

def planeAtMaskBorder(inputMask,relativePosition):
    """#planeAtMaskBorder(inputNifti,roiNum,relativePosition):
    #creates a planar roi at the specified border of the specified ROI.
    #
    # INPUTS:
    # -inputMask:  a nifti with ONLY 1 and 0 (int) as the content, a boolean mask, in essence
    #
    # -relativePosition: string input indicating which border to obtain planar roi at
    # Valid inputs: 'superior','inferior','medial','lateral','anterior','posterior','rostral','caudal','left', or 'right'
    #
    # OUTPUTS:
    # outPlaneNifti: planar ROI as Nifti at specified border
    """
    import numpy as np
    
    #establish valid positional terms
    validPositionTerms=['superior','inferior','medial','lateral','anterior','posterior','rostral','caudal','left','right']
    #cased relativePosition check
    #again, don't know how arrays work with booleans
    if ~np.isin(relativePosition.lower(),validPositionTerms):
         raise Exception("planeAtROIborder Error: input relative position " + relativePosition + " not valid.")
    
    #convert the boundary coords of the mask to subject space in order to interpret positional terms
    convertedBoundCoords=subjectSpaceMaskBoundaryCoords(inputMask)
    
    #kind of assumes at least moderately ACPC aligned data, at least insofar
    #as relative anatomical position terms are concerned
    
    positionTermsDict={'superior': np.max(convertedBoundCoords[:,2]),
                      'inferior': np.min(convertedBoundCoords[:,2]),
                      'medial':   np.min(convertedBoundCoords[np.min(np.abs(convertedBoundCoords[:,0]))==np.abs(convertedBoundCoords[:,0]),0]),
                      'lateral': np.max(convertedBoundCoords[np.max(np.abs(convertedBoundCoords[:,0]))==np.abs(convertedBoundCoords[:,0]),0]),
                      'anterior': np.max(convertedBoundCoords[:,1]),
                      'posterior': np.min(convertedBoundCoords[:,1]),
                      'rostral': np.max(convertedBoundCoords[:,1]),
                      'caudal': np.min(convertedBoundCoords[:,1]),
                      'left': np.min(convertedBoundCoords[:,0]),
                      'right': np.max(convertedBoundCoords[:,0])}    

    #similar to the positonal term Dict but for interpreting pertinant dimension
    dimensionDict={'superior': 'z',
                   'inferior': 'z',
                   'medial':   'x',
                   'lateral': 'x',
                   'anterior': 'y',
                   'posterior': 'y',
                   'rostral': 'y',
                   'caudal': 'y',
                   'left': 'x',
                   'right': 'x'}

    outPlaneNifti=makePlanarROI(inputMask,positionTermsDict[relativePosition] , dimensionDict[relativePosition])
    
    #return the planar roi you have created
    return outPlaneNifti

def createSphere(r, p, reference):
    """ create a sphere of given radius at some point p in the brain mask
    Args:
    r: radius of the sphere
    p: point (in subject coordinates of the brain mask, i.e. not the image space) of the center of the
    sphere)
    reference:  The reference nifti whose space the sphere will be in
    
    
    modified version of nltools sphere function which outputs the sphere ROI in the
    coordinate space of the input reference
    """
    import nibabel as nib
    import numpy as np
    
    print('Creating '+ str(r) +' mm radius spherical roi at '+str(p))
    
    fullMask = nib.nifti1.Nifti1Image(np.ones(reference.get_fdata().shape), reference.affine, reference.header)
    #obtain boundary coords in subject space in order set max min values for interactive visualization
    convertedBoundCoords=subjectSpaceMaskBoundaryCoords(fullMask)
    
    #if the sphere centroid is outside of the image, throw a full on error
    if np.any(    [np.min(convertedBoundCoords[:,dims])>p[dims] or  
                   np.max(convertedBoundCoords[:,dims])<p[dims] 
                   for dims in list(range(len(reference.shape))) ]):
        raise ValueError('Requested sphere centroid outside of reference image')
    
    if np.any(    [np.min(convertedBoundCoords[:,dims])-r>p[dims] or  
                   np.max(convertedBoundCoords[:,dims])+r<p[dims] 
                   for dims in list(range(len(reference.shape))) ]):
        import warnings
        warnings.warn('Requested sphere partially outside of reference image')
    
    #get the dimensions of the source image
    dims = reference.shape
    
    imgCoord=np.floor(nib.affines.apply_affine(np.linalg.inv(reference.affine),p))
    
    #previous version of this misunderstood this process and included header.zooms
    #radius is interpreted in mm, but image indexing is interpreted in voxels
    #as such, you have to normalize the later distance mask computation (mask_r)
    #with that information
    
    #for each dimension, compute the orthogonal distance of the relevant centroid
    #coordinate component from each other point in the mask
    #NO NEED FOR AFFINE USAGE, BECAUSE THIS IS ALL IN IMAGE SPACE
    dimVoxelDistVals=[np.abs((np.arange(0, dims[i]) )-imgCoord[i])
                      for i in list(range(len(dims)))]
    #ogrid doesnt work?  meshgrid seems to work fine
    #not sure why previous version was forcing to type int
    x, y, z = np.meshgrid(dimVoxelDistVals[0], dimVoxelDistVals[1], dimVoxelDistVals[2],indexing='ij')          
    
    #clever element-wise computation and summation of 3-dimensional Pythagorean
    #components, followed by masking via radius value
    #NOTE THAT THE SUBSEQUENT FORMULATION HAS IMAGESPACE UNITS ON THE RIGHT
    #AND MM SPACE ON THE LEFT.  AS SUCH WE MUST MODIFY THE DISTANCE COMPUTATION
    #mask_r = x*x + y*y + z*z <= r*r
    voxelDims=reference.header.get_zooms()
    mask_r = x*x*voxelDims[0] + y*y*voxelDims[1] + z*z*voxelDims[2] <= r*r

    outSphereROI = np.zeros(dims, dtype=bool)
    outSphereROI[mask_r] = True
    #not sure of robustness to strange input affines, but seems to work
    return nib.Nifti1Image(outSphereROI, affine=reference.affine, header=reference.header)

def multiROIrequestToMask(atlas,roiNums):
    """multiROIrequestToMask(atlas,roiNums):
    #creates a nifti structure mask for the input atlas image of the specified labels
    #
    # INPUTS:
    # -atlas:  an atlas nifti
    #
    # -roiNums: an 1d int array input indicating the labels that are to be extracted.  Singleton request (single int) will work fine.  Will throw warning if not present
    #
    # OUTPUTS:
    # -outImg:  a mask with int(1) in those voxels where the associated labels were found.  If the label wasn't found, an empty nifti structure is output.
    
    ##NOTE REPLACE WITH nil.masking.intersect_masks when you get a chance
    """
    import numpy as np
    import nibabel as nib
    
    #force input roiNums to array, don't want to deal with lists and dicts
    roiNumsInArray=np.asarray(roiNums)
    
    if  np.logical_not(np.all(np.isin(roiNumsInArray,np.unique(atlas.get_fdata()).astype(int)))):
        import warnings
        warnings.warn("WMA.multiROIrequestToMask WARNING: ROI label " + str(list(roiNumsInArray[np.logical_not(np.isin(roiNumsInArray,np.unique(atlas.get_fdata()).astype(int)))])) + " not found in input Nifti structure.")
        
    #obtain coordiantes of all relevant label values
    labelCoords=np.where(np.isin(atlas.get_fdata(),roiNumsInArray))

    #create blank data structure
    concatData=np.zeros(atlas.shape)
    #set all appropriate values to true
    concatData[labelCoords]=True

    #set all appropriate values to true
    concatOutNifti=nib.nifti1.Nifti1Image(concatData, affine=atlas.affine, header=atlas.header)
    
    return concatOutNifti

def planarROIFromAtlasLabelBorder(inputAtlas,roiNums, relativePosition):
    """#planarROIFromAtlasLabelBorder(referenceNifti, mmPlane, dimension):
    #generates a planar ROI at the specified label border from the input atlas
    #
    # INPUTS:
    # -inputAtlas:  the atlas that the numeric labels specified in roiNums will be extracted from
    #
    # -roiNums: either a specification of a single or multiple ROIs which the planar ROI border will be assesed for.
    # a submission of multiple ROIs will be assessed as the amalgamation (i.e. merging) of those labels.
    #
    # -relativePosition: string input indicating which planar border to generate
    # Valid inputs: 'superior','inferior','medial','lateral','anterior','posterior','rostral','caudal','left', or 'right'
    #
    # OUTPUTS:
    # -planarROI: the roi structure of the planar ROI
    #
    #  Daniel Bullock 2020 Bloomington
    """
    
    #this plane will be oblique to the subject's *actual anatomy* if they aren't
    #oriented orthogonally. As such, do this only after acpc-alignment

    #merge the inputs if necessary
    mergedRequest=multiROIrequestToMask(inputAtlas,roiNums)
    
    #use that mask to generate a planar border
    planeOut=planeAtMaskBorder(mergedRequest,relativePosition)
    
    return(planeOut)
    
def sliceROIwithPlane(inputROINifti,inputPlanarROI,relativePosition):
    #sliceROIwithPlane(inputROINifti,planarROI,relativePosition):
    #slices input ROI Nifti using input planarROI and returns portion specified by relativePosition
    #
    # inputROINifti:  a (presumed ROI) nifti with ONLY 1 and 0 (int) as the content, a boolean mask, in essence
    #
    # planarROI: a planar roi (nifti) that is to be used to perform the slicing operation on the inputROINifti
    # 
    # relativePosition: which portion of the sliced ROI to return
    # Valid inputs: 'superior','inferior','medial','lateral','anterior','posterior','rostral','caudal','left', or 'right'
   
    #test for intersection between the ROIS
    import nibabel as nib
    import numpy as np
    
    #get the data
    inputROINiftiData=inputROINifti.get_fdata()
    inputPlanarROIData=inputPlanarROI.get_fdata()
    
    #boolean to check if intersection
    intersectBool=np.any(np.logical_and(inputROINiftiData!=0,inputPlanarROIData!=0))
    if ~intersectBool:
        import warnings
        warnings.warn("WMA.sliceROIwithPlane WARNING: input planar ROI does not intersect with input ROI.")

    
    #implement test to determine if input planar roi is indeed planar
    #get coordinates of mask voxels in image space
    planeVoxCoords=np.where(inputPlanarROI.get_fdata())
    #find the unique values of img space coordinates for each dimension
    uniqueCoordCounts=[len(np.unique(iCoords)) for iCoords in planeVoxCoords]
    #one of them should be singular in the case of a planar roi, throw an error if not
    if ~np.any(np.isin(uniqueCoordCounts,1)):
        raise ValueError('input cut ROI not planar (i.e. single voxel thick for True values)')
    
    fullMask = nib.nifti1.Nifti1Image(np.ones(inputROINifti.get_fdata().shape), inputROINifti.affine, inputROINifti.header)
    #pass full mask to subject space boundary function
    fullVolumeBoundCoords=subjectSpaceMaskBoundaryCoords(fullMask)
    #get boundary mask coords for mask
    maskVolumeBoundCoords=subjectSpaceMaskBoundaryCoords(inputPlanarROI)
    #find the subject space plane that the dim is in
    subjSpacePlaneDimIndex=np.where(~np.all(np.equal(fullVolumeBoundCoords,maskVolumeBoundCoords),axis=0))[0][0]
    
    #set up the dictionary for boundaries
    positionTermsDict={'superior': np.max(fullVolumeBoundCoords[:,2]),
                      'inferior': np.min(fullVolumeBoundCoords[:,2]),
                      'medial':   np.min(fullVolumeBoundCoords[np.min(np.abs(fullVolumeBoundCoords[:,0]))==np.abs(fullVolumeBoundCoords[:,0]),0]),
                      'lateral': np.max(fullVolumeBoundCoords[np.max(np.abs(fullVolumeBoundCoords[:,0]))==np.abs(fullVolumeBoundCoords[:,0]),0]),
                      'anterior': np.max(fullVolumeBoundCoords[:,1]),
                      'posterior': np.min(fullVolumeBoundCoords[:,1]),
                      'rostral': np.max(fullVolumeBoundCoords[:,1]),
                      'caudal': np.min(fullVolumeBoundCoords[:,1]),
                      'left': np.min(fullVolumeBoundCoords[:,0]),
                      'right': np.max(fullVolumeBoundCoords[:,0])}
    
    #set up the dictionary for dimensions
    dimensionDict={'superior': 2,
                   'inferior': 2,
                   'medial':   0,
                   'lateral': 0,
                   'anterior': 1,
                   'posterior': 1,
                   'rostral': 1,
                   'caudal': 1,
                   'left': 0,
                   'right': 0}    


    planeCoords=[]
    #i guess the only way
    for iDims in list(range(len(inputROINifti.shape))):
        #set step size at half the voxel length in this dimension
        stepSize=fullMask.header.get_zooms()[iDims]*.5
        if iDims==dimensionDict[relativePosition]:
            #kind of wishy,washy, but because we halved the step size in the previous step
            #by taking the average of the coord bounds (in subject space) we should actually be fine
            #we'll use this as one of our two bounds
            thisDimBounds=np.sort([np.mean(maskVolumeBoundCoords[:,subjSpacePlaneDimIndex]),positionTermsDict[relativePosition]])
           
        else:
            thisDimBounds=np.sort([fullVolumeBoundCoords[0,iDims],fullVolumeBoundCoords[1,iDims]])
           
        #create a vector with the coords for this dimension
        dimCoords=np.arange(thisDimBounds[0],thisDimBounds[1],stepSize)
        #append it to the planeCoords list object
        planeCoords.append(list(dimCoords))
            
    x, y, z = np.meshgrid(planeCoords[0], planeCoords[1], planeCoords[2],indexing='ij')
    #squeeze the output (maybe not necessary)          
    planeCloud= np.squeeze([x, y, z])
    #convert to coordinate vector
    testSplit=np.vstack(planeCloud).reshape(3,-1).T
    #use dipy functions to treat point cloud like one big streamline, and move it back to image space
    import dipy.tracking.utils as ut
    lin_T, offset =ut._mapping_to_voxel(inputROINifti.affine)
    inds = ut._to_voxel_coordinates(testSplit, lin_T, offset)
    
    #create a blank array for the keep area mask
    keepArea=np.zeros(inputPlanarROI.shape).astype(bool)
    #set the relevant indexes to true
    #-1 because of zero indexing
    #could be an issue here if mismatch between input nifti and planar roi
    keepArea[inds[:,0]-1,inds[:,1]-1,inds[:,2]-1]=True 
    
    #create a nifti structure for this object
    sliceKeepNifti=nib.nifti1.Nifti1Image(keepArea, inputPlanarROI.affine, header=inputPlanarROI.header)
    
    #intersect the ROIs to return the remaining portion
    #will cause a problem if Niftis have different affines.
    from nilearn import masking 
    remainingROI=masking.intersect_masks([sliceKeepNifti,inputROINifti], threshold=1, connected=False)
    #consider throwing an error here if the output Nifti is empty
    
    return remainingROI

def alignROItoReference(inputROI,reference):
    """ extracts the coordinates of an ROI and reinstantites them as an ROI in the refernce space of the reference input
    Helps avoid affine weirdness.
    Args:
    inputROI: an input ROI in nifti format
    reference: the reference nifti that you would like the ROI moved to.
        
    Outputs:
    outROI: output nifti ROI in the reference space of the input reference nifti

    """   
    import numpy as np
    import nibabel as nib
    from dipy.tracking.utils import seeds_from_mask
    
    densityKernel=np.asarray(reference.header.get_zooms())
    
    roiCoords=seeds_from_mask(inputROI.get_fdata(), inputROI.affine, density=densityKernel)
    
    #use dipy functions to treat point cloud like one big streamline, and move it back to image space
    import dipy.tracking.utils as ut
    lin_T, offset =ut._mapping_to_voxel(reference.affine)
    inds = ut._to_voxel_coordinates(roiCoords, lin_T, offset)
    #create a blank array for the keep area mask
    outData=np.zeros(reference.shape).astype(bool)
    #set the relevant indexes to true
    #-1 because of zero indexing
    outData[inds[:,0]-1,inds[:,1]-1,inds[:,2]-1]=True 
    
    #create a nifti structure for this object
    outROI=nib.nifti1.Nifti1Image(outData, reference.affine, header=reference.header)

    return outROI
    
def segmentTractMultiROI(streamlines, roisvec, includeVec, operationsVec):
    """segmentTractMultiROI(streamlines, roisvec, includeVec, operationsVec):
    #Iteratively applies ROI-based criteria
    #INPUTS
    #
    # -streamlines: appropriately formatted list of candidate streamlines, e.g. a candidate tractome
    #
    # -roisvec: a list of nifti objects that will serve as your ROIs
    #
    # -includeVec: a boolean list indicating whether you want the associated roi to act as an INCLUSION or EXCLUSION ROI (True=inclusion)
    #
    # operationsVec: a list with any of the following instructions on which streamline nodes to asses (and how)
    #    "any" : any point is within tol from ROI. Default.
    #    "all" : all points are within tol from ROI.
    #    "either_end" : either of the end-points is within tol from ROI
    #    "both_end" : both end points are within tol from ROI.
    #
    # OUTPUTS
    # -outBoolVec: boolean vec indicating streamlines that survived ALL operations
    #
    # NOTE: roisvec, includeVec, and operationsVec should all be the same lenth
    # ADVICE: apply the harshest (fewest survivors) criteria first.  Will result 
    # in signifigant speed ups.
    # ADVICE: starting with specifying endpoints has the additional benefit of reducting
    # the number of nodes considered per streamline to 2.  This would be an effective way
    # of implementing a fast and harsh first criteria.
    """
    import numpy as np
    
    if ~ len(np.unique([len(roisvec), len(includeVec), len(operationsVec)]))==1:
        raise ValueError('mismatch between lengths of roi, inclusion, and operation vectors')

    #create an array to store the boolean result of each round of segmentation    
    outBoolArray=np.zeros([len(streamlines),len(roisvec)],dtype=bool)
    
    for iOperations in list(range(len(roisvec))):
        
        #perform this segmentation operation
        curBoolVec=applyNiftiCriteriaToTract_DIPY_Test(streamlines, roisvec[iOperations], includeVec[iOperations], operationsVec[iOperations])
        
        #if this is the first segmentation application
        if iOperations == 0:
            #set the relevant column to the current segmentation bool vec
            outBoolArray[:,iOperations]=curBoolVec
        #otherwise
        else:
            #obtain the indexes for the previous round of survivors
            lastRoundSurvivingIndexes=np.where(outBoolArray[:,iOperations-1])[0]
            #of those, determine which survived this round
            thisRoundSurvivingIndexes=lastRoundSurvivingIndexes[np.where(curBoolVec)[0]]
        
            #set the entries that survived the previous round AND this round to true
            outBoolArray[thisRoundSurvivingIndexes,iOperations]=True
        
        #in either case, subsegment the streamlines to the remaining streamlines in order to speed up the next iteration
        streamlines=streamlines[np.where(curBoolVec)[0]]
        
    #when all iterations are complete collapse across the colums and return only those streams that met all criteria
    outBoolVec=np.all(outBoolArray,axis=1)
    
    return outBoolVec
   

def applyNiftiCriteriaToTract_DIPY(streamlines, maskNifti, includeBool, operationSpec):
    """segmentTractMultiROI(streamlines, roisvec, includeVec, operationsVec):
    #Iteratively applies ROI-based criteria, uses a range of dipy functions
    #and custom made functions to expedite the typically slow segmentation process
    #
    #adapted from https://github.com/dipy/dipy/blob/master/dipy/tracking/streamline.py#L200
    #basically a variant of
    #https://github.com/DanNBullock/wma/blob/33a02c0373d6742ddf07fd8ac3c8481662577743/utilities/wma_SegmentFascicleFromConnectome.m
    #
    #INPUTS
    #
    # -streamlines: appropriately formatted list of candidate streamlines, e.g. a candidate tractome
    #
    # -maskNifti: a nifti Mask containing only 1s and 0s
    #
    # -includeBool: a boolean indicator of whether you want the associated ROI to act as an INCLUSION or EXCLUSION ROI (True=inclusion)
    #
    # -operationSpec: operation specification, one following instructions on which streamline nodes to asses (and how)
    #    "any" : any point is within tol from ROI. Default.
    #    "all" : all points are within tol from ROI.
    #    "either_end" : either of the end-points is within tol from ROI
    #    "both_end" : both end points are within tol from ROI.
    #
    # OUTPUTS
    #
    # - outBoolVec: boolean vec indicating streamlines that survived operation
    """
    #still learning how to import from modules
    from dipy.tracking.utils import near_roi
    import numpy as np
    import dipy.tracking.utils as ut
    import nibabel as nib
    from nilearn import masking 
    import scipy
    
    #perform some input checks
    validOperations=["any","all","either_end","both_end"]
    if np.logical_not(np.in1d(operationSpec, validOperations)):
         raise Exception("applyNiftiCriteriaToTract Error: input operationSpec not understood.")
    
    if np.logical_not(type(maskNifti).__name__=='Nifti1Image'):
        raise Exception("applyNiftiCriteriaToTract Error: input maskNifti not a nifti.")
    
    #the conversion to int may cause problems if the input isn't convertable to int.  Then again, the point of this is to raise an error, so...
    elif np.logical_not(np.all(np.unique(maskNifti.get_fdata()).astype(int)==[0, 1])): 
        raise Exception("applyNiftiCriteriaToTract Error: input maskNifti not convertable to 0,1 int mask.  Likely not a mask.")
        
    if np.logical_not(isinstance(includeBool, bool )):
        raise Exception("applyNiftiCriteriaToTract Error: input includeBool not a bool.  See input description for usage")
        
    #in order to achieve a speedup we should minimize the number of coordinates we are testing.
    #let's intersect the ROI and a mask of the streamlines so that we can subset the relevant portions/voxels of the ROI
    tractMask=ut.density_map(streamlines, maskNifti.affine, maskNifti.shape)
    #dialate tract mask in order to include voxels that are outside of the 
    #tractmask, but nonetheless within the tolerance.
    tractMask=scipy.ndimage.binary_dilation(tractMask.astype(bool), iterations=1)
    #convert int-based voxel-wise count data to int because apparently that's the only way you can save with nibabel
    tractMask=nib.Nifti1Image(np.greater(tractMask,0).astype(int), affine=maskNifti.affine)

    #take the intersection of the two, the tract mask and the ROI mask nifti.
    #ideally we are reducing the number of points that each streamline node needs to be compared to
    #for example, a 256x 256 planar ROI would result in 65536 coords,
    #intersecting with a full brain tractogram reduces this by about 1/3
    #because we are not bothering with the roi coordinates that are outside
    #the whitematter mask
    tractMaskROIIntersection=masking.intersect_masks([tractMask,maskNifti], threshold=1, connected=False)

    #we can obtain a speedup with respect to the tractogram as well, by only
    #considering those streamlines that plausably occupy the same bounding box
    #as the ROI.  The use of a bounding box is predicated upon the assumption that
    #assessing whether any node coordinate is within a specified bounds
    # (i.e. B_D_1>C_I_N_D>B_D_2; I=streamline index, N=node index, D=dimension index, b=bound)
    #is sufficiently fast *and* specifc (in that it exclusdes a sufficient number of stremalines)
    #to justify this additional round of computation
    
    #if we could reduce this to only those streamline-nodes that are within the bounding box
    #we could speed this up further.
    
    #find the streamlines that are within the bounding box of the maskROI,
    #NOTE: this isn't necessarily the full mask input by the user
    boundedStreamsBool=subsetStreamsByROIboundingBox(streamlines, tractMaskROIIntersection)
    
    #subset them
    boundedStreamSubset=streamlines[np.where(boundedStreamsBool)[0]]
    #second track mask application doesn't seem to do anything    
    
    #use dipy's near roi function to generate bool
    criteriaStreamsBool=near_roi(boundedStreamSubset, tractMaskROIIntersection.affine, tractMaskROIIntersection.get_fdata().astype(bool), mode=operationSpec)
       
    #find the indexes of the original streamlines that the survivors correspond to
    boundedStreamsIndexes=np.where(boundedStreamsBool)[0]
    originalIndexes=boundedStreamsIndexes[np.where(criteriaStreamsBool)[0]]
    
    if includeBool==True:
        #initalize an out bool vec
        outBoolVec=np.zeros(len(streamlines))
        #set the relevant entries to true
        outBoolVec[originalIndexes]=True
    elif includeBool==False:          
        #initalize an out bool vec
        outBoolVec=np.ones(len(streamlines))
        #set the relevant entries to true
        outBoolVec[originalIndexes]=False
    
    return outBoolVec

def applyNiftiCriteriaToTract_DIPY_Test(streamlines, maskNifti, includeBool, operationSpec):
    """segmentTractMultiROI(streamlines, roisvec, includeVec, operationsVec):
    #Iteratively applies ROI-based criteria, uses a range of dipy functions
    #and custom made functions to expedite the typically slow segmentation process
    #
    #adapted from https://github.com/dipy/dipy/blob/master/dipy/tracking/streamline.py#L200
    #basically a variant of
    #https://github.com/DanNBullock/wma/blob/33a02c0373d6742ddf07fd8ac3c8481662577743/utilities/wma_SegmentFascicleFromConnectome.m
    #
    #INPUTS
    #
    # -streamlines: appropriately formatted list of candidate streamlines, e.g. a candidate tractome
    #
    # -maskNifti: a nifti Mask containing only 1s and 0s
    #
    # -includeBool: a boolean indicator of whether you want the associated ROI to act as an INCLUSION or EXCLUSION ROI (True=inclusion)
    #
    # -operationSpec: operation specification, one following instructions on which streamline nodes to asses (and how)
    #    "any" : any point is within tol from ROI. Default.
    #    "all" : all points are within tol from ROI.
    #    "either_end" : either of the end-points is within tol from ROI
    #    "both_end" : both end points are within tol from ROI.
    #
    # OUTPUTS
    #
    # - outBoolVec: boolean vec indicating streamlines that survived operation
    """
    #still learning how to import from modules
    from dipy.tracking.utils import near_roi
    import numpy as np
    import dipy.tracking.utils as ut
    import nibabel as nib
    from nilearn import masking 
    import scipy
    
    #perform some input checks
    validOperations=["any","all","either_end","both_end"]
    if np.logical_not(np.in1d(operationSpec, validOperations)):
         raise Exception("applyNiftiCriteriaToTract Error: input operationSpec not understood.")
    
    if np.logical_not(type(maskNifti).__name__=='Nifti1Image'):
        raise Exception("applyNiftiCriteriaToTract Error: input maskNifti not a nifti.")
    
    #the conversion to int may cause problems if the input isn't convertable to int.  Then again, the point of this is to raise an error, so...
    elif np.logical_not(np.all(np.unique(maskNifti.get_fdata()).astype(int)==[0, 1])): 
        raise Exception("applyNiftiCriteriaToTract Error: input maskNifti not convertable to 0,1 int mask.  Likely not a mask.")
        
    if np.logical_not(isinstance(includeBool, bool )):
        raise Exception("applyNiftiCriteriaToTract Error: input includeBool not a bool.  See input description for usage")
        
    #in order to achieve a speedup we should minimize the number of coordinates we are testing.
    #let's intersect the ROI and a mask of the streamlines so that we can subset the relevant portions/voxels of the ROI
    tractMask=ut.density_map(streamlines, maskNifti.affine, maskNifti.shape)
    #dialate tract mask in order to include voxels that are outside of the 
    #tractmask, but nonetheless within the tolerance.
    tractMask=scipy.ndimage.binary_dilation(tractMask.astype(bool), iterations=1)
    #convert int-based voxel-wise count data to int because apparently that's the only way you can save with nibabel
    tractMask=nib.Nifti1Image(np.greater(tractMask,0).astype(int), affine=maskNifti.affine)

    #take the intersection of the two, the tract mask and the ROI mask nifti.
    #ideally we are reducing the number of points that each streamline node needs to be compared to
    #for example, a 256x 256 planar ROI would result in 65536 coords,
    #intersecting with a full brain tractogram reduces this by about 1/3
    #because we are not bothering with the roi coordinates that are outside
    #the whitematter mask
    tractMaskROIIntersection=masking.intersect_masks([tractMask,maskNifti], threshold=1, connected=False)

    #we can obtain a speedup with respect to the tractogram as well, by only
    #considering those streamlines that plausably occupy the same bounding box
    #as the ROI.  The use of a bounding box is predicated upon the assumption that
    #assessing whether any node coordinate is within a specified bounds
    # (i.e. B_D_1>C_I_N_D>B_D_2; I=streamline index, N=node index, D=dimension index, b=bound)
    #is sufficiently fast *and* specifc (in that it exclusdes a sufficient number of stremalines)
    #to justify this additional round of computation
    
    
    #find the streamlines that are within the bounding box of the maskROI,
    #NOTE: this isn't necessarily the full mask input by the user, as a result of the
    #intersection with the tract mask
    [boundedIndexes, boundedStreams]=subsetStreamsNodesByROIboundingBox(streamlines, tractMaskROIIntersection)
    
    #use dipy's near roi function to generate bool
    criteriaStreamsBool=near_roi(boundedStreams, tractMaskROIIntersection.affine, tractMaskROIIntersection.get_fdata().astype(bool), mode=operationSpec)

    originalIndexes=boundedIndexes[np.where(criteriaStreamsBool)[0]]
    
    if includeBool==True:
        #initalize an out bool vec
        outBoolVec=np.zeros(len(streamlines))
        #set the relevant entries to true
        outBoolVec[originalIndexes]=True
    elif includeBool==False:          
        #initalize an out bool vec
        outBoolVec=np.ones(len(streamlines))
        #set the relevant entries to true
        outBoolVec[originalIndexes]=False
    
    return outBoolVec

def subsetStreamsByROIboundingBox(streamlines, maskNifti):
    """subsetStreamsByROIboundingBox(streamlines, maskNifti):
    #subsets the input set of streamlines to only those that have nodes within the box
    #
    # INPUTS
    #
    # -streamlines: streamlines to be subset
    #
    # -maskNifti:  the mask nifti from which a bounding box is to be extracted, which will be used to subset the streamlines
    #
    # OUTPUTS
    #
    # -criteriaVec:  a boolean vector indicating which streamlines contain nodes within the bounding box.
    #
    """
    #compute distance tolerance
    from dipy.core.geometry import dist_to_corner
    import time
    
    #begin timing
    t1_start=time.process_time()
    
    #use distance to corner to set tolerance
    dtc = dist_to_corner(maskNifti.affine)
    
    #convert them to subject space
    subjectSpaceBounds=subjectSpaceMaskBoundaryCoords(maskNifti)
    #expand to accomidate tolerance
    subjectSpaceBounds[0,:]=subjectSpaceBounds[0,:]-dtc
    subjectSpaceBounds[1,:]=subjectSpaceBounds[1,:]+dtc
    
    #map and lambda function to determine whether each streamline is within the bounds
    criteriaVec=list(map(lambda streamline: streamlineWithinBounds(streamline,subjectSpaceBounds), streamlines))
    
    #stop timing
    t1_stop=time.process_time()
    # get the elapsed time
    modifiedTime=t1_stop-t1_start
    
    print('Tractogram subseting complete in ' +str(modifiedTime) +', '+str(sum(criteriaVec)) + ' of ' + str(len(streamlines)) + ' within mask boundaries')
    return criteriaVec

def subsetStreamsNodesByROIboundingBox(streamlines, maskNifti):
    """subsetStreamsByROIboundingBox(streamlines, maskNifti):
    #subsets the input set of streamlines to only those that have nodes within the box
    #
    # INPUTS
    #
    # -streamlines: streamlines to be subset
    #
    # -maskNifti:  the mask nifti from which a bounding box is to be extracted, which will be used to subset the streamlines
    #
    # OUTPUTS
    #
    # -criteriaVec:  a boolean vector indicating which streamlines contain nodes within the bounding box.
    #
    """
    #compute distance tolerance
    from dipy.core.geometry import dist_to_corner
    from dipy.tracking.streamline import Streamlines
    import numpy as np
    import time
    
    #begin timing
    t1_start=time.process_time()
    
    #use distance to corner to set tolerance
    dtc = dist_to_corner(maskNifti.affine)
    
    #convert them to subject space
    subjectSpaceBounds=subjectSpaceMaskBoundaryCoords(maskNifti)
    #expand to accomidate tolerance
    subjectSpaceBounds[0,:]=subjectSpaceBounds[0,:]-dtc
    subjectSpaceBounds[1,:]=subjectSpaceBounds[1,:]+dtc
    
    #map and lambda function to extract the nodes within the bounds
    criteriaVec=list(map(lambda streamline: streamlineNodesWithinBounds(streamline,subjectSpaceBounds), streamlines))
    outIndexes=np.where(list(map(lambda x: x.size>0, criteriaVec)))[0]
    outStreams=Streamlines(criteriaVec)
    
    #stop timing
    t1_stop=time.process_time()
    # get the elapsed time
    modifiedTime=t1_stop-t1_start
    
    print('Tractogram subseting complete in ' +str(modifiedTime) +', '+str(len(outIndexes)) + ' of ' + str(len(streamlines)) + ' within mask boundaries')
    return outIndexes, outStreams

def streamlineWithinBounds(streamline,bounds):
    """ determine whether **any** node of the input streamline is within the specified bounds
    Args:
        -streamline: an n by d shaped array where n=the number of nodes and d = the dimensionality of the streamline
        
        -bounds: a 2 x d array specifying the coordinate boundaries (in the pertinant space of the streamline) for assesment

    Output:
        withinBoundsBool:  a boolean value indicating whether the input streamline satisfies the within-bounds criteria
    
    """
    import numpy as np

    #see which nodes are between the bounds
    nodeCriteria=np.asarray([np.logical_and(streamline[:,iDems]>bounds[0,iDems],streamline[:,iDems]<bounds[1,iDems]) for iDems in list(range(bounds.shape[1])) ])
    
    #return true if any single node is between all three sets of bounds
    return np.any(np.all(nodeCriteria,axis=0))

def streamlineNodesWithinBounds(streamline,bounds):
    """ determine whether **any** node of the input streamline is within the specified bounds
    Args:
        streamline: an n by d shaped array where n=the number of nodes and d = the dimensionality of the streamline
        bounds: a 2 x d array specifying the coordinate boundaries (in the pertinant space of the streamline) for assesment

    Output:
        withinBoundsNodes:  an array of the nodes 
    
    """
    import numpy as np
    
    #see which nodes are between the bounds
    nodeCriteria=np.asarray([np.logical_and(streamline[:,iDems]>bounds[0,iDems],streamline[:,iDems]<bounds[1,iDems]) for iDems in list(range(bounds.shape[1])) ])
    
    #return return the viable nodes, could and often will be empty
    return streamline[np.all(nodeCriteria,axis=0)]

    
def subjectSpaceMaskBoundaryCoords(maskNifti):
    """ convert the boundary voxel indexes into subject space coordinates using the provided affine
    Args:
        inputVoxelBounds: a mask nifti
        affine: an affine matrix with which to transform the voxel bounds / image space coordinates

    Output:
        subjectSpaceBounds:  a 2 x 3 dimensional array indicating the minimum and maximum bounds for each dimension
    """
    
    import dipy.segment.mask as mask
    import numpy as np
    refDimBounds=np.asarray(mask.bounding_box(maskNifti.get_fdata()))
    
    #use itertools and cartesian product to generate vertex img space coordinates
    import itertools
    outCoordnates=np.asarray(list(itertools.product(refDimBounds[:,0], refDimBounds[:,1], refDimBounds[:,2])))
     
    #perform affine
    import nibabel as nib
    convertedBoundCoords=nib.affines.apply_affine(maskNifti.affine,outCoordnates)
    
    #create holder for output
    import numpy as np
    subjectSpaceBounds=np.zeros([2,convertedBoundCoords.shape[1]])
    
    #list comprehension to iterate across dimensions
    #picking out min and max vals
    #min
    subjectSpaceBounds[0,:]=[np.min(convertedBoundCoords[:,iDems]) for iDems in list(range(convertedBoundCoords.shape[1]))]
    #max
    subjectSpaceBounds[1,:]=[np.max(convertedBoundCoords[:,iDems]) for iDems in list(range(convertedBoundCoords.shape[1]))]
    
    return subjectSpaceBounds

def applyEndpointCriteria(streamlines,planarROI,requirement,whichEndpoints):
    """ apply a relative location criteria to the endpoints of all streamlines in a collection of streamlines
    Args:
        streamlines: streamlines to be segmented from
        planarROI: the planar ROI relative to which the streamlines' endpoints' locations should be assessed
        requirement:  A relative anatomical positional term
        whichEndpoints:  whether this criteria should apply to 'both', 'one', or 'neither' endpoint
    
    Output:
        streamBool:  a boolean vector indicating which streamlines meet the specified criteria.
    """
    import numpy as np
    import nibabel as nib
    
    fullMask = nib.nifti1.Nifti1Image(np.ones(planarROI.get_fdata().shape), planarROI.affine, planarROI.header)
    #obtain boundary coords in subject space in order set max min values for interactive visualization
    convertedBoundCoords=subjectSpaceMaskBoundaryCoords(fullMask)

    #implement test to determine if input planar roi is indeed planar
    #get coordinates of mask voxels in image space
    
    from dipy.tracking.utils import apply_affine
    planeSubjCoords=apply_affine(planarROI.affine, np.array(np.where(planarROI.get_fdata())).T)
    #find the unique values of img space coordinates for each dimension
    uniqueCoordCounts=[len(np.unique(planeSubjCoords[:,iCoords])) for iCoords in list(range(planeSubjCoords.shape[1]))]
    #one of them should be singular in the case of a planar roi, throw an error if not
    if ~np.any(np.isin(uniqueCoordCounts,1)):
        raise ValueError('input ROI not planar (i.e. single voxel thick for True values)')
    
    planeCoord=planeSubjCoords[0,np.where(np.equal(uniqueCoordCounts,1))[0][0]]

    #set up the dictionary for boundaries
    positionTermsDict={'superior': np.max(convertedBoundCoords[:,2]),
                      'inferior': np.min(convertedBoundCoords[:,2]),
                      'medial':   np.min(convertedBoundCoords[np.min(np.abs(convertedBoundCoords[:,0]))==np.abs(convertedBoundCoords[:,0]),0]),
                      'lateral': np.max(convertedBoundCoords[np.max(np.abs(convertedBoundCoords[:,0]))==np.abs(convertedBoundCoords[:,0]),0]),
                      'anterior': np.max(convertedBoundCoords[:,1]),
                      'posterior': np.min(convertedBoundCoords[:,1]),
                      'rostral': np.max(convertedBoundCoords[:,1]),
                      'caudal': np.min(convertedBoundCoords[:,1]),
                      'left': np.min(convertedBoundCoords[:,0]),
                      'right': np.max(convertedBoundCoords[:,0])}
    
    dimensionDict={'superior': 2,
                   'inferior': 2,
                   'medial':   0,
                   'lateral': 0,
                   'anterior': 1,
                   'posterior': 1,
                   'rostral': 1,
                   'caudal': 1,
                   'left': 0,
                   'right': 0}        
    
    #throw an error if there's a mismatch 
    if  np.logical_not(np.where(np.equal(uniqueCoordCounts,1))[0][0]==dimensionDict[requirement]):
        raise Exception("applyEndpointCriteria Error: input relative position " + requirement + " not valid for input plane.")
    
    #create blank structure for endpoints
    endpoints=np.zeros((len(streamlines),6))
    #get the endpoints, taken from
    #https://github.com/dipy/dipy/blob/f149c756e09f172c3b77a9e6c5b5390cc08af6ea/dipy/tracking/utils.py#L708
    for iStreamline in range(len(streamlines)):
        #remember, first 3 = endpoint 1, last 3 = endpoint 2    
        endpoints[iStreamline,:]= np.concatenate([streamlines[iStreamline][0,:], streamlines[iStreamline][-1,:]])
    
    Endpoints1=endpoints[:,0:3]
    Endpoints2=endpoints[:,3:7]
    
    #sort the bounds
    sortedBounds=np.sort(planeCoord,positionTermsDict[requirement])
    #get the relevant image dimension
    spaceDim=np.where(np.equal(uniqueCoordCounts,1))[0][0]
    
    #apply the criteria to both endpoints
    endpoints1Criteria=np.logical_and(np.greater(Endpoints1[:,spaceDim],sortedBounds[0]),np.less(Endpoints1[:,spaceDim],sortedBounds[1]))
    endpoints2Criteria=np.logical_and(np.greater(Endpoints2[:,spaceDim],sortedBounds[0]),np.less(Endpoints2[:,spaceDim],sortedBounds[1]))
    
    whichEndpointsDict={'neither': 0,
                        'one': 1,
                        'both':   2}
    
    
    #sum the two endpoint criterion vectors
    sumVec=np.add(endpoints1Criteria,endpoints2Criteria,dtype=int)
    
    #see where the target value is met
    targetMetVec=sumVec==whichEndpointsDict[whichEndpoints]
    
    return targetMetVec
    
def applyMidpointCriteria(streamlines,planarROI,requirement):
    """ apply a relative location criteria to the midpoints of all streamlines in a collection of streamlines
    Args:
        streamlines: streamlines to be segmented from
        planarROI: the planar ROI relative to which the streamlines' midpoints' locations should be assessed
        requirement:  A relative anatomical positional term

    Output:
        streamBool:  a boolean vector indicating which streamlines meet the specified criteria.
    """
    import numpy as np
    import nibabel as nib
    
    fullMask = nib.nifti1.Nifti1Image(np.ones(planarROI.get_fdata().shape), planarROI.affine, planarROI.header)
    #obtain boundary coords in subject space in order set max min values for interactive visualization
    convertedBoundCoords=subjectSpaceMaskBoundaryCoords(fullMask)

    #implement test to determine if input planar roi is indeed planar
    #get coordinates of mask voxels in image space
    
    from dipy.tracking.utils import apply_affine
    planeSubjCoords=apply_affine(planarROI.affine, np.array(np.where(planarROI.get_fdata())).T)
    #find the unique values of img space coordinates for each dimension
    uniqueCoordCounts=[len(np.unique(planeSubjCoords[:,iCoords])) for iCoords in list(range(planeSubjCoords.shape[1]))]
    #one of them should be singular in the case of a planar roi, throw an error if not
    if ~np.any(np.isin(uniqueCoordCounts,1)):
        raise ValueError('input ROI not planar (i.e. single voxel thick for True values)')
    
    planeCoord=planeSubjCoords[0,np.where(np.equal(uniqueCoordCounts,1))[0][0]]

    #set up the dictionary for boundaries
    positionTermsDict={'superior': np.max(convertedBoundCoords[:,2]),
                      'inferior': np.min(convertedBoundCoords[:,2]),
                      'medial':   np.min(convertedBoundCoords[np.min(np.abs(convertedBoundCoords[:,0]))==np.abs(convertedBoundCoords[:,0]),0]),
                      'lateral': np.max(convertedBoundCoords[np.max(np.abs(convertedBoundCoords[:,0]))==np.abs(convertedBoundCoords[:,0]),0]),
                      'anterior': np.max(convertedBoundCoords[:,1]),
                      'posterior': np.min(convertedBoundCoords[:,1]),
                      'rostral': np.max(convertedBoundCoords[:,1]),
                      'caudal': np.min(convertedBoundCoords[:,1]),
                      'left': np.min(convertedBoundCoords[:,0]),
                      'right': np.max(convertedBoundCoords[:,0])}
    
    dimensionDict={'superior': 2,
                   'inferior': 2,
                   'medial':   0,
                   'lateral': 0,
                   'anterior': 1,
                   'posterior': 1,
                   'rostral': 1,
                   'caudal': 1,
                   'left': 0,
                   'right': 0}        
    
    #throw an error if there's a mismatch 
    if  np.logical_not(np.where(np.equal(uniqueCoordCounts,1))[0][0]==dimensionDict[requirement]):
        raise Exception("applyEndpointCriteria Error: input relative position " + requirement + " not valid for input plane.")

    #use dipy to get the midpoints    
    from dipy.segment.metric import MidpointFeature
    feature = MidpointFeature()
    midpoints = np.squeeze(np.asarray(list(map(feature.extract, streamlines))))
    
    
    #sort the bounds
    sortedBounds=np.sort(planeCoord,positionTermsDict[requirement])
    #get the relevant image dimension
    spaceDim=np.where(np.equal(uniqueCoordCounts,1))[0][0]
    
    #apply the criteria to both endpoints
    midpointsCriteria=np.logical_and(np.greater(midpoints[:,spaceDim],sortedBounds[0]),np.less(midpoints[:,spaceDim],sortedBounds[1]))

    return midpointsCriteria     

def maskMatrixByBoolVec(dipyGrouping,boolVec):
    """ recompute a connectivity matrix for a specified subset of the streamlines
    Args:
        dipyGrouping: the grouping output of the dipy utils.connectivity_matrix [WITH symmetric=False]
        boolVec: a boolean vector indicating which streamlines to consider in this computation
        

    Output:
        matrixSubset:  a matrix whose entries have been altered in accordance with the input
    """

    import numpy as np 

    #get the number of unique labels
    uniqueLabels=np.unique(np.asarray(list(dipyGrouping.keys())))
    #get the indexes of the valid streamlines from the input boolVec
    #concatenate to force to 1d array
    validStreams=np.concatenate(np.where(boolVec))
    #inatialize blank matrix object
    matrixSubset=np.zeros((len(uniqueLabels),len(uniqueLabels)))
    
    #iterate over the dictionary keys/ pairings
    for iPairings in range(len(list(dipyGrouping.keys()))):
        #get the current dictionary key entry
        currKey=list(dipyGrouping.keys())[iPairings]
        #get the length of the intersction of the boolVec streamlines and the current streamlines
        #and place it in the matrix location
        matrixSubset[currKey[0],currKey[1]]=len(np.intersect1d(dipyGrouping[currKey],validStreams))
    
    return matrixSubset.astype(int)

def dummyNiftiForStreamlines(streamlines):
    import numpy as np
    import nibabel as nib
    import dipy.tracking.utils as ut
    
    #dipy is stubborn and wants a reference nifti for some reason
    #fineI'llDoItMyself.jpg
    tractBounds=np.asarray([np.min(streamlines._data,axis=0),np.max(streamlines._data,axis=0)])
    roundedTractBounds=np.asarray([np.floor(tractBounds[0,:]),np.ceil(tractBounds[1,:])])
    constructedAffine=np.eye(4)
    constructedAffine[0:3,3]=tractBounds[0,:]

    lin_T, offset =ut._mapping_to_voxel(constructedAffine)
    inds = ut._to_voxel_coordinates(streamlines._data, lin_T, offset)
        
    testBounds=np.asarray([np.min(inds,axis=0),np.max(inds,axis=0)])
        
    #now create a dummy nifit, because that's what dipy demands
    dataShape=(roundedTractBounds[1,:]-roundedTractBounds[0,:]).astype(int)
    #adding a +1 pad because it yells otherwise?
    dummyData=np.zeros(dataShape+1)
    dummyNifti= nib.nifti1.Nifti1Image(dummyData, constructedAffine)
    return dummyNifti
    

def findTractNeckNode(streamlines):
    #findTractNeckNode(streamlines):
    # finds the node index for each streamline which corresponds to the most tightly constrained
    # portion of the tract (i.e. the "neck).
    #
    # INPUTS
    #
    #-streamlines: appropriately formatted list of candidate streamlines, presumably corresponding to a coherent anatomical SUBSTRUCTURE (i.e. tract)
    # NOTE: this computation isn't really sensible for a whole brain tractome, and would probably take a long time as well 
    #
    # OUTPUTS
    #
    # -neckNodeVec:  a 1d int vector array that indicates, for each streamline, the node that is associated with the "neck" of the input streamline collection.
    #
    from dipy.segment.clustering import QuickBundles
    from dipy.segment.metric import ResampleFeature
    from dipy.segment.metric import AveragePointwiseEuclideanMetric
    from scipy.spatial.distance import cdist
    import numpy as np
    import dipy.tracking.utils as ut
    from scipy.ndimage import gaussian_filter
    import nibabel as nib
    
    #lets presuppose that the densest point in the density mask ocurrs within
    #the neck.  Thus we need a 
    dummyNifti=dummyNiftiForStreamlines(streamlines)
    tractMask=ut.density_map(streamlines, dummyNifti.affine, dummyNifti.shape)
    #we smooth it just in case there are weird local maxima
    #that sigma may need to be worked on
    smoothedDensity=gaussian_filter(np.square(tractMask),sigma=3)
    #now find the max point
    maxDensityLoc=np.asarray(np.where(smoothedDensity==np.max(smoothedDensity)))
    #pick the first one arbitrarily in case there are multiple
    maxDensityImgCoord=maxDensityLoc[:,0]
    #get the coordinate in subject space
    subjCoord = nib.affines.apply_affine(dummyNifti.affine,maxDensityImgCoord)

    #iterate across streamlines
    neckNodeIndexVecOut=[]
    for iStreamline in range(len(streamlines)):
        #distances for all nodes 
        curNodesDist = cdist(streamlines[iStreamline], np.atleast_2d(subjCoord), 'euclidean')
        #presumably the nodes most directly tangent to the highest density point would be the neck?
        neckNodeIndexVecOut.append(np.where(curNodesDist==np.min(curNodesDist))[0].astype(int))

    return neckNodeIndexVecOut

def removeStreamlineOutliersAtNeck(streamlines,cutStDev):
    # removeStreamlineOutliersAtNeck(streamlines,cutStDev):
    # INPUTS
    #
    #-streamlines: appropriately formatted list of candidate streamlines, presumably corresponding to a coherent anatomical SUBSTRUCTURE (i.e. tract)
    # NOTE: this computation isn't really sensible for a whole brain tractome, and would probably take a long time as well 
    #
    # OUTPUTS
    #
    # -streamlinesCleaned:  a subset of the input streamlines, corresponding to those which have survived the cleaning process.
    #
    # NOTE: given that we are using a lognormal distribution and the 
    #
    import scipy.stats as stats  
    import numpy as np
    from scipy.spatial.distance import cdist
    
    
    neckNodeIndexVecOut=findTractNeckNode(streamlines)
    
    #recover the nodes
    neckNodes=np.zeros((len(streamlines),3))
    for iStreamline in range(len(streamlines)):
        #distances for all nodes 
        neckNodes[iStreamline,:] =streamlines[iStreamline][neckNodeIndexVecOut[iStreamline]]
    
    #compute the statistics on the average neck point
    avgNeckPoint=np.zeros((1,3))
    avgNeckPoint[0,:]=np.mean(neckNodes,axis=0)
    curNearDistsFromAvg=cdist(neckNodes, avgNeckPoint, 'euclidean')
    #neckPointDistAvg=np.mean(curNearDistsFromAvg)
    #neckPointDistStDev=np.std(curNearDistsFromAvg)
    
    #deviation from centroid is typical lognorm?
    #lognormOut[0]=shape param, lognormOut[2]=scaleParam
    sSigma, loc, scale = stats.lognorm.fit(curNearDistsFromAvg, floc=0)
    muVar=np.log(scale)
    #https://www.mathworks.com/help/stats/lognormal-distribution.html
    computedMean=np.exp(muVar+np.square(sSigma)/2)
    computedStDev=muVar
    
    #confidence interval
    #np.sum(np.logical_or(curNearDistsFromAvg<computedMean-2*computedStDev,curNearDistsFromAvg<computedMean+2*computedStDev))
    #curNearDistsFromAvg[curNearDistsFromAvg>computedMean+5*computedStDev]
    
    #finish later, maybe not necessary
    
    streamlinesCleaned=streamlines[curNearDistsFromAvg.flatten()<computedMean+cutStDev*computedStDev]
    
    return streamlinesCleaned

    
def shiftBundleAssignment(clusters,targetCluster,streamIndexesToMove):
    #shiftBundleAssignment(clusters,targetCluster,streamIndexesToMove)
    #
    # This function is, in essence, a workaround for quickbundles, which has a method
    # for assigning streamlines to a cluster, but doesn't also take the additional
    # step of removing those streamlines from existing clusters.
    # https://github.com/dipy/dipy/blob/ed71831f6a9e048961b00af10f1f381e2da63efe/dipy/segment/clustering.py#L103
    #
    # clusters: the clusters object output from qb.cluster
    #
    # targetCluster: the index of the cluster that we will be adding stream indexes to
    #
    # streamIndexesToMove: the indexes that we will be adding to the targetCluster and removing from all other clusters
    from dipy.segment.clustering import QuickBundles
    import numpy as np
    
    indexesRecord=[]
    
    #lets begin by removing the indexes from all clusters
    for iClusters in range(len(clusters)):
        #if any of the to remove indexes are in the current cluster
        if np.any(np.isin(streamIndexesToMove,clusters.clusters[iClusters].indices)):
            #extract the current cluster indexes
            currIndexes=clusters.clusters[iClusters].indices
            
            #add to the record
            indexesRecord.append(currIndexes)
            currToRemoveIndexes=np.where(np.isin(clusters.clusters[iClusters].indices ,streamIndexesToMove))[0]
            fixedIndexes=np.delete(currIndexes,currToRemoveIndexes)
            clusters.clusters[iClusters].indices=fixedIndexes
            #is this necessary?
            clusters.clusters[iClusters].update()
            
    #now perform a check to ensure that the request was sensible
    #ugly way to program this check
    #if there are any indexes that you requested to move that ARE NOT in any of the associated clusters
    flattenIndexes = lambda t: [item for sublist in t for item in sublist]
    if len(np.where(np.logical_not(np.isin(streamIndexesToMove,np.asarray(flattenIndexes(indexesRecord)))))[0])>0:
        #throw an error, because something probably went wrong with your request
        #probably not formatted correctly to begin with, and will throw an error while throwing an error.  Dog.
     raise Exception("shiftBundleAssignment Error: requested indexes" + str(streamIndexesToMove[np.where(np.logical_not(np.isin(streamIndexesToMove,indexesRecord)))[0]]) +  " not found in any cluster.  Malformed request, possible track/tractome-cluster mismatch.")
     
    #indexes removed and request viability confirmed, now add requested streams to relevant cluster
    #luckily we have a built-in method for this
    #clusters.clusters[targetCluster].asign(streamIndexesToMove)
    
    #except I cant figure out how to get it to work so, brute force
    
    clusters.clusters[targetCluster].indices=np.union1d(clusters[targetCluster].indices,streamIndexesToMove)
    clusters.clusters[targetCluster].update()
    
    #fixed?
    return clusters

def neckmentation(streamlines):
    #neckmentation(streamlines)
    #
    # a neck-based segmentation using findTractNeckNode and quickbundles
    #
    # INPUTS
    #
    # -streamlines: an input tractome to be segmented
    #
    
    import numpy as np
    from scipy.spatial.distance import cdist
    import itertools
    
    #set tolerance for how far apart bundles can be to be merged
    #initial investigations indicate that mean distance from centroid is ~ 3, so given that this is on both sides,
    #we should half it to ensure that they are close to one another
    #we'll start with 2, just to be generous
    distanceThresh=2
    
    
    #import dipy and perform quickBundles
    from dipy.segment.clustering import QuickBundles
    from dipy.segment.metric import ResampleFeature
    from dipy.segment.metric import AveragePointwiseEuclideanMetric
    centroidNodesNum=100
    # Streamlines will be resampled to 24 points on the fly.
    feature = ResampleFeature(nb_points=centroidNodesNum)
    #?
    metric = AveragePointwiseEuclideanMetric(feature=feature)  # a.k.a. MDF
    #threshold set very high to return 1 bundle
    qb = QuickBundles(threshold=5., metric=metric)
    #get the centroid clusters or clusters, dont know which this is
    clusters = qb.cluster(streamlines)
    
    #do it twice
    clusters=mergeBundlesViaNeck(streamlines,clusters,distanceThresh)
    
    clusters=mergeBundlesViaNeck(streamlines,clusters,distanceThresh)
    
    return clusters
    
    #create a blank vector for the neck node coordinates
  
    
def mergeBundlesViaNeck(streamlines,clusters,distanceThresh):
    #mergeBundlesViaNeck(clusters,distanceThresh):
    #
    #merges bundles based on how close the necks of the bundles are
    #
    # -streamlines: an input tractome to be segmented
    #
    # -clusters:  a clusters object, an output from qb.cluster
    #
    # distanceThresh the threshold between neck centroids that is accepted for merging
    
    import numpy as np
    from scipy.spatial.distance import cdist
    import itertools
    
    
    from dipy.segment.clustering import QuickBundles
    from dipy.segment.metric import ResampleFeature
    from dipy.segment.metric import AveragePointwiseEuclideanMetric
    
    neckNodes=np.zeros((len(clusters),3))
    for iClusters in range(len(clusters)):
        print(iClusters)
        currentBundle=streamlines[clusters.clusters[iClusters].indices]
        if len (currentBundle)>1:
            currentNeckIndexes=findTractNeckNode(currentBundle)
            currentNeckNodes=np.zeros((len(currentNeckIndexes),3))
        
            for iStreams in range(len(currentBundle)):
                currentNeckNodes[iStreams,:]=currentBundle[iStreams][currentNeckIndexes[iStreams]]
        
            
            #if it's a singleton streamline, just guess the midpoint?
        else:
            currentNeckNodes=np.zeros((1,3))
            currentNeckNodes[0,:]=currentBundle[0][np.floor(currentBundle[0].shape[0]/2).astype(int),:]
        neckNodes[iClusters,:]=np.mean(currentNeckNodes,axis=0)
        currentNeckNodes=[]
        
    #now do the distance computation
    neckNodeDistanceArray=cdist(neckNodes,neckNodes,metric='euclidean')
    withinThreshNecks=np.asarray(np.where(neckNodeDistanceArray<distanceThresh))        
    withinThreshNecksNotIdent=withinThreshNecks[:,np.where(~np.equal(withinThreshNecks[0,:],withinThreshNecks[1,:]))[0]]
    #perform a check to ensure that we do not waste time on singleton merge attempts
    #now we need to find the clusters that are empty
    streamCountVec=np.zeros(len(clusters))    
    for iClusters in range(len(clusters)):
        streamCountVec[iClusters]=len(clusters.clusters[iClusters].indices)
    
    singletonIndexes=np.where(streamCountVec==1)
    np.where(np.all(~np.isin(withinThreshNecksNotIdent,singletonIndexes),axis=0))
    
    
    
    
    possibleMerges=list([])    
    for iMerges in range(withinThreshNecksNotIdent.shape[1]):
        currentCandidates=withinThreshNecksNotIdent[:,iMerges]
        clusterOneInstances=np.asarray(np.where(withinThreshNecksNotIdent==currentCandidates[0]))[1,:]
        clusterTwoInstances=np.asarray(np.where(withinThreshNecksNotIdent==currentCandidates[1]))[1,:]
        
        withinThreshIndexesToCheck=np.union1d(clusterOneInstances,clusterTwoInstances)
        
        currentCentroidIndexes=np.unique(withinThreshNecksNotIdent[:,withinThreshIndexesToCheck])
        
        newCentroidsArray=np.vstack((neckNodes[currentCentroidIndexes,:],np.mean(neckNodes[currentCentroidIndexes,:],axis=0)))
        
        curDistArray=cdist(newCentroidsArray,newCentroidsArray,metric='euclidean')
        
        #its within the bounds
        if np.max(curDistArray[:,-1])<np.max(curDistArray[:,-2]):
            possibleMerges.append(currentCentroidIndexes)
        else:
            possibleMerges.append(currentCandidates)
            
    possibleMerges.sort(key=len)     
    possibleMerges.reverse()
    
    mergedBundles=[]
    for iMerges in range(len(possibleMerges)):
        
        currentCandidates=possibleMerges[iMerges]
        remainToMerge=np.setdiff1d(currentCandidates,mergedBundles)
        if len(remainToMerge)>1:
            print(iMerges)
            print(remainToMerge)
            for iBundles in range(1,len(remainToMerge)):
                clusters=shiftBundleAssignment(clusters,currentCandidates[0],clusters.clusters[remainToMerge[iBundles]].indices)  
            mergedBundles=np.append(mergedBundles,remainToMerge)
        #otherwise
        #do nothing, there is no bundle to merge
    
    #now we need to find the clusters that are empty
    streamCountVec=np.zeros(len(clusters))    
    for iClusters in range(len(clusters)):
        streamCountVec[iClusters]=len(clusters.clusters[iClusters].indices)
        
    #now that we have those indicies we have to go through them IN REVERSE ORDER
    #in order to remove them, because deleting them changes the index sequence for all subsequent clusters.
    #there has to be a better implementation of this process, but this is where we are.
    #clusters.remove_cluster DOESNT WORK, due to "only integer scalar arrays can be converted to a scalar index"
    toDeleteClusters=np.where(streamCountVec==0)[0]

    flippedToDelete=np.flip(toDeleteClusters)
    #this is asinine, but I can't figure out another way to do it.
    for iDeletes in range(len(flippedToDelete)):
        currentToDelete=flippedToDelete[iDeletes]
        currentCluster=clusters.clusters[currentToDelete]
        clusters.remove_cluster(currentCluster)
    
    return clusters

def smoothStreamlines(tractogram):
    #smoothStreamlines(tractogram):
    #
    #Smooths streamlines using spline method.  
    #Probably hugely memory inefficient, and will resample all streamlines to 400 nodes
    #Resource intensive, but look at those smooth streamlines!
    #
    # -tractogram: an input stateful tractogram 
    #
    # -out_tractogram:  an output stateful tractogram with the streamlines smmothed and
    #                   resampled to 400 nodes
    #
    # distanceThresh the threshold between neck centroids that is accepted for merging
    import dipy
    import nibabel as nib
    #extract the streamlines, but not really because this is just linking
    inputStreamlines=tractogram.streamlines
    #get the count before anything is done
    initialLength=len(inputStreamlines)
    for iStreams in range(initialLength):
        #use the spline method to get the smoothed streamline
        dipySplineOut=dipy.tracking.metrics.spline(inputStreamlines[iStreams])
        #this is an ugly way to do this
        
        inputStreamlines.append(dipySplineOut)
    outStreamlines=inputStreamlines[initialLength-1:-1]
    out_tractogram = nib.streamlines.tractogram.Tractogram(outStreamlines)
    return out_tractogram

def cullViaClusters(clusters,tractogram,streamThresh):
    #cullViaClusters(clusters,tractogram,streamThresh)
    #
    #This function culls streamlines from a tractogram
    #based on the number of streamlines in their clusters
    #
    # INPUTS
    #
    # clusters: the output cluster object from quickbundles
    #
    # tractogram: a tractogram associated with the input clusters object
    #
    #streamThresh:  the minimum number of streamlines in a cluster bundle
    #               needed to survive the culling process
    #
    # OUTPUTS
    #
    # tractogram: the cleaned tractogram
    #
    # culledTractogram: a tractogram containing those streamlines which have
    # been culled.
    #
    # begin code    
    import numpy as np
    import copy
    #apparently this can cause some issues on linux machines with dtype u21?
    clustersSurviveThresh=np.greater(np.asarray(list(map(len, clusters))),streamThresh)
    survivingStreams=[]
    for iclusters in clusters[clustersSurviveThresh]:
        survivingStreams=survivingStreams + iclusters.indices
    culledStreamIndicies=list(set(list(range(1,len(tractogram.streamlines))))-set(survivingStreams))
    culledTractogram=copy.deepcopy(tractogram)
    culledTractogram.streamlines=culledTractogram.streamlines[culledStreamIndicies]
    #cull those streamlines
    #don't know what to do about those warnings
    tractogram.streamlines=tractogram.streamlines[survivingStreams]
    return tractogram, culledTractogram


def qbCullStreams(tractogram,qbThresh,streamThresh):
    #qbCullStreams(tractogram,qbThresh,streamThresh)
    #
    #this function uses dipy quickbundles to filter out streamlines which exhibt
    #unusual/extremely uncommon trajectories using a interstreamline distance
    #measure
    #
    # INPUTS
    #
    # tractogram: an input tractogram to be cleaned
    #
    # qbThresh: the distance parameter to be used for the quickbundles algorithm
    #
    #streamThresh:  the minimum number of streamlines in a cluster bundle
    #               needed to survive the culling process
    # OUTPUTS
    #
    # tractogram: the cleaned tractogram
    #
    # culledTractogram: a tractogram containing those streamlines which have
    # been culled.
    # 
    # Begin code
    from dipy.segment.clustering import QuickBundles
    #get the number of input streamlines
    inputStreamNumber=len(tractogram.streamlines)
    #good default value for quick clustering
    #qbThresh=15
    #perform quickBundles
    qb = QuickBundles(threshold=qbThresh)
    clusters = qb.cluster(tractogram.streamlines)
    #perform cull
    [outTractogram,culledTractogram]=cullViaClusters(clusters,tractogram,streamThresh)
    #report cull count
    numberCulled=inputStreamNumber-len(outTractogram.streamlines)
    print(str(numberCulled) + ' streamlines culled')
    return outTractogram, culledTractogram

def streamGeomQuantifications(tractogram):
    #streamGeomQuantifications(tractogram)
    #
    #This function quantifies a number of streamline-based quantities
    #in the same fashion as wma_tools's  ConnectomeTestQ
    #
    # INPUTS
    #
    # tractogram: an input stateful tractogram
    #
    # OUTPUTS
    # 
    # quantificationTable: a pandas table documenting the streamline based
    #                      quantificaton.  
    # see https://github.com/DanNBullock/wma_tools#connectometestq
    # for more details.
    #
    # begin code
    import pandas as pd
    import numpy as np
    #establish the dataframe
    column_names = ["length", "fullDisp", "efficiencyRat", "asymRat", "bioPriorCost"]
    quantificationTable = pd.DataFrame(columns = column_names)
    #begin the iteration
    from dipy.tracking.streamline import length
    import math
    for iStreamlines in tractogram.streamlines:
        #compute lengths
        streamLength=length(iStreamlines)
        firstHalfLength=length(iStreamlines[1:int(round(len(iStreamlines)/2)),:])
        secondHalfLength=length(iStreamlines[int(round(len(iStreamlines)/2))+1:-1,:])
    
        #compute displacements
        displacement=math.dist(iStreamlines[1,:],iStreamlines[-1,:]) 
        firstHalfDisp=math.dist(iStreamlines[1,:],iStreamlines[int(round(len(iStreamlines)/2)),:])
        secondHalfDisp=math.dist(iStreamlines[int(round(len(iStreamlines)/2))+1,:],iStreamlines[-1,:])
    
        #compute ratios
        efficiencyRatio=displacement/streamLength
        asymetryRatio=np.square((firstHalfDisp/firstHalfLength)-(secondHalfDisp/secondHalfLength))
        bioPriorCost=1/(1-asymetryRatio)
        
        #append to dataframe
        rowVector=[streamLength, displacement, efficiencyRatio, asymetryRatio, bioPriorCost]
        rowAsSeries = pd.Series(rowVector, index = quantificationTable.columns)
        quantificationTable.append(rowAsSeries,ignore_index=True)
    return quantificationTable

def crossSectionGIFsFromTract(tractogram,refAnatT1,saveDir):
    import nibabel as nib
    #use dipy to create the density mask
    from dipy.tracking import utils
    import numpy as np
    
    from nilearn.image import crop_img 
    #nilearn.image.resample_img ? to resample output
    
    croppedReference=crop_img(refAnatT1)
    
    densityMap=utils.density_map(tractogram.streamlines, croppedReference.affine, croppedReference.shape)
    densityNifti=nib.nifti1.Nifti1Image(densityMap,croppedReference.affine, croppedReference.header)
    
    #refuses to plot single slice, single image
    #from nilearn.plotting import plot_stat_map
    #outImg=plot_stat_map(stat_map_img=densityNifti,bg_img=refAnatT1, cut_coords= 1,display_mode='x',cmap='viridis')
   
    
    #obtain boundary coords in subject space in order to
    #use plane generation function
    convertedBoundCoords=subjectSpaceMaskBoundaryCoords(croppedReference)
    
    dimsList=['x','y','z']
    #brute force with matplotlib
    import matplotlib.pyplot as plt
    for iDims in list(range(len(croppedReference.shape))):
        #this assumes that get_zooms returns zooms in subject space and not image space orientation
        # which may not be a good assumption if the orientation is weird
        subjectSpaceSlices=np.arange(convertedBoundCoords[0,iDims],convertedBoundCoords[1,iDims],refAnatT1.header.get_zooms()[iDims])
        #get the desired broadcast shape and delete current dim value
        broadcastShape=list(croppedReference.shape)
        del broadcastShape[iDims]
        
        #iterate across slices
        for iSlices in list(range(len(subjectSpaceSlices))):
            #set the slice list entry to the appropriate singular value
            currentSlice=makePlanarROI(croppedReference, subjectSpaceSlices[iSlices], dimsList[iDims])

            #set up the figure
            fig,ax = plt.subplots()
            ax.axis('off')
            #kind of overwhelming to do this in one line
            refData=np.rot90(np.reshape(croppedReference.get_fdata()[currentSlice.get_fdata().astype(bool)],broadcastShape),3)
            plt.imshow(refData, cmap='gray', interpolation='nearest')
            #kind of overwhelming to do this in one line
            densityData=np.rot90(np.reshape(densityNifti.get_fdata()[currentSlice.get_fdata().astype(bool)],broadcastShape),3)
            plt.imshow(np.ma.masked_where(densityData<1,densityData), cmap='viridis', alpha=.5, interpolation='nearest')
            figName='dim_' + str(iDims) +'_'+  str(iSlices).zfill(3)
            plt.savefig(figName,bbox_inches='tight')
            plt.clf()
    
    import os        
    from PIL import Image
    import glob
    for iDims in list(range(len(croppedReference.shape))):
        dimStem='dim_' + str(iDims)
        img, *imgs = [Image.open(f) for f in sorted(glob.glob(dimStem+'*.png'))]
        img.save(os.path.join(saveDir,dimStem+'.gif'), format='GIF', append_images=imgs,
                 save_all=True, duration=len(imgs)*2, loop=0)
        os.remove(sorted(glob.glob(dimStem+'*.png')))

def endpointDispersionMapping(streamlines,referenceNifti,distanceParameter):
    """endpointDispersionMapping(streamlines,referenceNifti,distanceParameter)
    For each voxel in the streamline-derived white matter mask, computes the
    average distance of streamlines' (within some specified radial distance
    of the voxel) endpoints from the average coordinate of the endpoints.  
    Simply averages the metric for each of the two endpoint clusters.

    Parameters
    ----------
    streamlines : TYPE
        Steamlines which are to be subjected to this analyis, dervied from
        tractogram.streamlines
    referenceNifti : TYPE
        A reference nifti.  Possibly not necessary; see wmc2tracts for example
        dummy mechanism.
    distanceParameter : TYPE
        DESCRIPTION.

    Returns
    -------
    dispersionMeasurement [NiFTI image]
        A nifti object with the data block containing the measurements derived
        for each voxel in the corresponding locations

    """
    # To be determined:
    # should we be useing the mean centroid (i.e. raw averaged enpoint coordinate)
    # or the actual endpoint closest to this coordinate?
    
    
    
    import dipy.tracking.utils as ut
    import dipy.tracking.streamline as streamline
    import numpy as np
    import nibabel as nib
    from scipy.spatial.distance import cdist
    from dipy.tracking.vox2track import streamline_mapping
    import itertools
    from dipy.segment.clustering import QuickBundles
    
    # get a streamline index dict of the whole brain tract
    streamlineMapping=streamline_mapping(streamlines, referenceNifti.affine)
    #extract the dictionary keys as coordinates
    imgSpaceTractVoxels = list(streamlineMapping.keys())
    subjectSpaceTractCoords = nib.affines.apply_affine(referenceNifti.affine, np.asarray(imgSpaceTractVoxels))  
    
    print('computing statistics for ' + str(len(streamlines)) + ' occupying ' + str(len(imgSpaceTractVoxels)) + ' voxels.')
    
    returnValues=np.zeros(len(subjectSpaceTractCoords))
    #probably a more elegant way to do this
    for iCoords in range(len(subjectSpaceTractCoords)):
        #make a sphere
        currentSphere=createSphere(distanceParameter, subjectSpaceTractCoords[iCoords,:], referenceNifti)
        
        #get the sphere coords in image space
        currentSphereImgCoords = np.array(np.where(currentSphere.get_fdata())).T
        
        #find the roi coords which correspond to voxels within the streamline mask
        validCoords=list(set(list(tuple([tuple(e) for e in currentSphereImgCoords]))) & set(imgSpaceTractVoxels))
        
        #return flattened list of indexes
        streamIndexes=list(itertools.chain(*[streamlineMapping[iCoords] for iCoords in validCoords]))
        
        #extract those streamlines as a subset
        streamsSubset=streamlines[streamIndexes]
        
        #not actually sure how this will work with a messy bundle
        #reorient streamlines so that endpoints 1 and endpoints 2 mean something
        qb = QuickBundles(threshold=100)
        cluster = qb.cluster(streamsSubset)
        
        #there should be only one with the distance setting this high
        orientedStreams=streamline.orient_by_streamline(streamsSubset, cluster.centroids[0])
        
        
        #create blank structure for endpoints
        endpoints=np.zeros((len(orientedStreams),6))
        #get the endpoints, taken from
        #https://github.com/dipy/dipy/blob/f149c756e09f172c3b77a9e6c5b5390cc08af6ea/dipy/tracking/utils.py#L708
        for iStreamline in range(len(orientedStreams)):
            #remember, first 3 = endpoint 1, last 3 = endpoint 2    
            endpoints[iStreamline,:]= np.concatenate([orientedStreams[iStreamline][0,:], orientedStreams[iStreamline][-1,:]])
        
        Endpoints1=endpoints[:,0:3]
        Endpoints2=endpoints[:,3:7]
        
        avgEndPoint1=np.mean(Endpoints1,axis=0)
        curNearDistsFromAvg1=cdist(Endpoints1, np.reshape(avgEndPoint1, (1,3)), 'euclidean')
        endPoint1DistAvg=np.mean(curNearDistsFromAvg1)
        
        avgEndPoint2=np.mean(Endpoints2,axis=0)
        curNearDistsFromAvg2=cdist(Endpoints2, np.reshape(avgEndPoint2, (1,3)), 'euclidean')
        endPoint2DistAvg=np.mean(curNearDistsFromAvg2)
        
        returnValues[iCoords]=np.mean([endPoint2DistAvg,endPoint1DistAvg])

    
    outDataArray=np.zeros(referenceNifti.shape,dtype='float')
    for iCoords in range(len(subjectSpaceTractCoords)):
        outDataArray[imgSpaceTractVoxels[iCoords]] = returnValues[iCoords]
        
    return nib.nifti1.Nifti1Image(outDataArray, referenceNifti.affine, referenceNifti.header)

def endpointDispersionMapping_Bootstrap(streamlines,referenceNifti,distanceParameter,bootstrapNum):
    """endpointDispersionMapping_Bootstrap(streamlines,referenceNifti,distanceParameter,bootstrapNum)    
       For each voxel in the streamline-derived white matter mask, computes the
       average distance of streamlines' (within some specified radial distance
       of the voxel) endpoints from the average coordinate of the endpoints.  
       Simply averages the metric for each of the two endpoint clusters.  
       
       Distinct from non bootstrap version:  performs some number of iterated
       bootstrap measurments from a subset of the whole input streamline group
       in order to ascertain variability of resultant metrics.  Performs
       bootstrap operations on a 1/2 subset of the total input streamlines

       Parameters
       ----------
       streamlines : TYPE
           Steamlines which are to be subjected to this analyis, dervied from
           tractogram.streamlines
       referenceNifti : TYPE
           A reference nifti.  Possibly not necessary; see wmc2tracts for example
           dummy mechanism.
       distanceParameter : TYPE
           DESCRIPTION.

       Returns
       -------
       [returns 4 distinct niftis]
       
       meanOfMeans [NiFTI image]
           A nifti object with the data block containing the per voxel averages
           of the averages derived from the boot strap operations
           
       varianceOfMeans [NiFTI image]
           A nifti object with the data block containing the per voxel variances
           of the averages derived from the boot strap operations
       
       meanOfVariances [NiFTI image]
           A nifti object with the data block containing the per voxel averages
           of the variances derived from the boot strap operations
       
       varianceOfVariances [NiFTI image]
           A nifti object with the data block containing the per voxel variances
           of the variances derived from the boot strap operations

       """
    import dipy.tracking.utils as ut
    import dipy.tracking.streamline as streamline
    import numpy as np
    import nibabel as nib
    from scipy.spatial.distance import cdist
    from dipy.tracking.vox2track import streamline_mapping
    import itertools
    from dipy.segment.clustering import QuickBundles
    
    # get a streamline index dict of the whole brain tract
    streamlineMapping=streamline_mapping(streamlines, referenceNifti.affine)
    #extract the dictionary keys as coordinates
    imgSpaceTractVoxels = list(streamlineMapping.keys())
    subjectSpaceTractCoords = nib.affines.apply_affine(referenceNifti.affine, np.asarray(imgSpaceTractVoxels))  
    
    print('computing statistics for ' + str(len(streamlines)) + ' occupying ' + str(len(imgSpaceTractVoxels)) + ' voxels.')
    
    bootstrapStreamNum=int(len(streamlines)/2)
    meanOfMeans=np.zeros(len(subjectSpaceTractCoords))
    varianceOfMeans=np.zeros(len(subjectSpaceTractCoords))
    meanOfVariances=np.zeros(len(subjectSpaceTractCoords))
    varianceOfVariances=np.zeros(len(subjectSpaceTractCoords))
    #probably a more elegant way to do this
    for iCoords in range(len(subjectSpaceTractCoords)):
        #make a sphere
        currentSphere=createSphere(distanceParameter, subjectSpaceTractCoords[iCoords,:], referenceNifti)
        
        #get the sphere coords in image space
        currentSphereImgCoords = np.array(np.where(currentSphere.get_fdata())).T
        
        #find the roi coords which correspond to voxels within the streamline mask
        validCoords=list(set(list(tuple([tuple(e) for e in currentSphereImgCoords]))) & set(imgSpaceTractVoxels))
        
        #return flattened list of indexes
        streamIndexes=list(itertools.chain(*[streamlineMapping[iCoords] for iCoords in validCoords]))
        
        #extract those streamlines as a subset
        streamsSubset=streamlines[streamIndexes]
        
        #not actually sure how this will work with a messy bundle
        #reorient streamlines so that endpoints 1 and endpoints 2 mean something
        #using quickbundles to get a centroid, because the actual method
        #is buried in obscurity
        qb = QuickBundles(threshold=100)
        cluster = qb.cluster(streamsSubset)
        
        #there should be only one with the distance setting this high
        orientedStreams=streamline.orient_by_streamline(streamsSubset, cluster.centroids[0])
        
        #create blank structure for endpoints
        endpoints=np.zeros((len(orientedStreams),6))
        #get the endpoints, taken from
        #https://github.com/dipy/dipy/blob/f149c756e09f172c3b77a9e6c5b5390cc08af6ea/dipy/tracking/utils.py#L708
        for iStreamline in range(len(orientedStreams)):
            #remember, first 3 = endpoint 1, last 3 = endpoint 2    
            endpoints[iStreamline,:]= np.concatenate([orientedStreams[iStreamline][0,:], orientedStreams[iStreamline][-1,:]])
        
        #select the appropriate endpoints
        Endpoints1=endpoints[:,0:3]
        Endpoints2=endpoints[:,3:7]
        
        #create holders for both the dispersion means and the dispersion variances
        dispersionMeans=[]
        dispersionVariances=[]
        for iBoostrap in range (bootstrapNum):
            
            #select a subset of half the whole streamline group, then 
            #find the intersection fo that set and the current voxel's streamlines
            currentBootstrapStreamsAll=np.random.randint(0,len(streamlines),bootstrapStreamNum)
            currentBootstrapStreamsSubSelect=np.in1d(streamIndexes,currentBootstrapStreamsAll)
            
            #compute the subset mean distance and variance for endpoint cluster 1
            avgEndPoint1=np.mean(Endpoints1[currentBootstrapStreamsSubSelect],axis=0)
            curNearDistsFromAvg1=cdist(Endpoints1[currentBootstrapStreamsSubSelect], np.reshape(avgEndPoint1, (1,3)), 'euclidean')
            endPoint1DistAvg=np.mean(curNearDistsFromAvg1)
            endPoint1DistVar=np.var(curNearDistsFromAvg1)
            
            #compute the subset mean distance and variance for endpoint cluster 2
            avgEndPoint2=np.mean(Endpoints2[currentBootstrapStreamsSubSelect],axis=0)
            curNearDistsFromAvg2=cdist(Endpoints2[currentBootstrapStreamsSubSelect], np.reshape(avgEndPoint2, (1,3)), 'euclidean')
            endPoint2DistAvg=np.mean(curNearDistsFromAvg2)
            endPoint2DistVar=np.var(curNearDistsFromAvg2)
        
            #for this bootstrap iteration, compute the average distance and the variance
            dispersionMeans.append(np.mean([endPoint2DistAvg,endPoint1DistAvg]))
            dispersionVariances.append(np.mean([endPoint1DistVar,endPoint2DistVar]))
        
        #now place them in the appropriate location in their respective
        #storage vectors
        meanOfMeans[iCoords]=np.mean(dispersionMeans)
        varianceOfMeans[iCoords]=np.var(dispersionMeans)
        meanOfVariances[iCoords]=np.mean(dispersionVariances)
        varianceOfVariances[iCoords]=np.var(dispersionVariances)
    
    #Now that the metrics have been compute for all coordinates, create
    #3d arrays to store the output for the nifti object data
    outMeanOfMeansArray=np.zeros(referenceNifti.shape,dtype='float')
    outVarianceOfMeansArray=np.zeros(referenceNifti.shape,dtype='float')
    outMeanOfVariancesArray=np.zeros(referenceNifti.shape,dtype='float')
    outVarianceOfVariancesArray=np.zeros(referenceNifti.shape,dtype='float')
    
    #iterate across each voxel coordinate
    for iCoords in range(len(subjectSpaceTractCoords)):
        #fill in the corresponding voxel's value for each metric
        outMeanOfMeansArray[imgSpaceTractVoxels[iCoords]] = meanOfMeans[iCoords]
        outVarianceOfMeansArray[imgSpaceTractVoxels[iCoords]] = varianceOfMeans[iCoords]
        outMeanOfVariancesArray[imgSpaceTractVoxels[iCoords]] = meanOfVariances[iCoords]
        outVarianceOfVariancesArray[imgSpaceTractVoxels[iCoords]] = varianceOfVariances[iCoords]
    
    #create nifti objects for each metric
    meanOfMeansNifti=nib.nifti1.Nifti1Image(outMeanOfMeansArray, referenceNifti.affine, referenceNifti.header)
    varianceOfMeansNifti=nib.nifti1.Nifti1Image(outVarianceOfMeansArray, referenceNifti.affine, referenceNifti.header)
    meanOfVariancesNifti=nib.nifti1.Nifti1Image(outMeanOfVariancesArray, referenceNifti.affine, referenceNifti.header)
    varianceOfVariancesNifti=nib.nifti1.Nifti1Image(outVarianceOfVariancesArray, referenceNifti.affine, referenceNifti.header)
    
    return meanOfMeansNifti, varianceOfMeansNifti, meanOfVariancesNifti, varianceOfVariancesNifti

def endpointDispersionAsymmetryMapping_Bootstrap(streamlines,referenceNifti,distanceParameter,bootstrapNum):
    """endpointDispersionMapping_Bootstrap(streamlines,referenceNifti,distanceParameter,bootstrapNum)    
       For each voxel in the streamline-derived white matter mask, computes the
       average distance of streamlines' (within some specified radial distance
       of the voxel) endpoints from the average coordinate of the endpoints.  
       Simply averages the metric for each of the two endpoint clusters.  
       
       Distinct from non bootstrap version:  performs some number of iterated
       bootstrap measurments from a subset of the whole input streamline group
       in order to ascertain variability of resultant metrics.  Performs
       bootstrap operations on a 1/2 subset of the total input streamlines
       
       Asymmetry version:  in addition to computing the mean of the relevant
       values for each voxel-subset of streamlines, also computes the ratio
       of the endpoint clusters.
       This is computed thusly:
           
           (A-B) / (A+B) 
           
           Where A = endpointCluster1Value and B = endpointClusterBValue
       
       In this way, the span of possible (non inf, non nan) values is 1 to -1,
       where 1 is the case in which A is substantially larger than B (e.g. B~=0),
       -1 is the case in which B is substantially larger than A (e.g. A~=0),
       and 0 is the case in which A and B are roughly equivalent. 

       Parameters
       ----------
       streamlines : TYPE
           Steamlines which are to be subjected to this analyis, dervied from
           tractogram.streamlines
       referenceNifti : TYPE
           A reference nifti.  Possibly not necessary; see wmc2tracts for example
           dummy mechanism.
       distanceParameter : TYPE
           DESCRIPTION.

       Returns
       -------
       [returns 8 distinct niftis]
       
       meanOfMeans [NiFTI image]
           A nifti object with the data block containing the per voxel averages
           of the averages derived from the boot strap operations
           
       varianceOfMeans [NiFTI image]
           A nifti object with the data block containing the per voxel variances
           of the averages derived from the boot strap operations
       
       meanOfVariances [NiFTI image]
           A nifti object with the data block containing the per voxel averages
           of the variances derived from the boot strap operations
       
       varianceOfVariances [NiFTI image]
           A nifti object with the data block containing the per voxel variances
           of the variances derived from the boot strap operations
           
       meanOfMeansAsym [NiFTI image]
           A nifti object with the data block containing the asymmetry measurment of
           per voxel averages of the averages derived from the boot strap operations
           
       varianceOfMeansAsym [NiFTI image]
           A nifti object with the data block containing the asymmetry measurment of
           the per voxel variances of the averages derived from the boot strap operations
       
       meanOfVariancesAsym [NiFTI image]
           A nifti object with the data block containing the asymmetry measurment of
           the per voxel averages of the variances derived from the boot strap operations
       
       varianceOfVariancesAsym [NiFTI image]
           A nifti object with the data block containing the asymmetry measurment of
           the per voxel variances of the variances derived from the boot strap operations

       """
    import dipy.tracking.utils as ut
    import dipy.tracking.streamline as streamline
    import numpy as np
    import nibabel as nib
    from scipy.spatial.distance import cdist
    from dipy.tracking.vox2track import streamline_mapping
    import itertools
    from dipy.segment.clustering import QuickBundles
    
    # get a streamline index dict of the whole brain tract
    streamlineMapping=streamline_mapping(streamlines, referenceNifti.affine)
    #extract the dictionary keys as coordinates
    imgSpaceTractVoxels = list(streamlineMapping.keys())
    subjectSpaceTractCoords = nib.affines.apply_affine(referenceNifti.affine, np.asarray(imgSpaceTractVoxels))
    
    print('computing statistics for ' + str(len(streamlines)) + ' occupying ' + str(len(imgSpaceTractVoxels)) + ' voxels.')
    
    bootstrapStreamNum=int(len(streamlines)/2)
    meanOfMeans=np.zeros(len(subjectSpaceTractCoords))
    varianceOfMeans=np.zeros(len(subjectSpaceTractCoords))
    meanOfVariances=np.zeros(len(subjectSpaceTractCoords))
    varianceOfVariances=np.zeros(len(subjectSpaceTractCoords))
    
    #asym
    meanOfMeansAsym=np.zeros(len(subjectSpaceTractCoords))
    varianceOfMeansAsym=np.zeros(len(subjectSpaceTractCoords))
    meanOfVariancesAsym=np.zeros(len(subjectSpaceTractCoords))
    varianceOfVariancesAsym=np.zeros(len(subjectSpaceTractCoords))
    #probably a more elegant way to do this
    for iCoords in range(len(subjectSpaceTractCoords)):
        #make a sphere
        currentSphere=createSphere(distanceParameter, subjectSpaceTractCoords[iCoords,:], referenceNifti)
        
        #get the sphere coords in image space
        currentSphereImgCoords = np.array(np.where(currentSphere.get_fdata())).T
        
        #find the roi coords which correspond to voxels within the streamline mask
        validCoords=list(set(list(tuple([tuple(e) for e in currentSphereImgCoords]))) & set(imgSpaceTractVoxels))
        
        #return flattened list of indexes
        streamIndexes=list(itertools.chain(*[streamlineMapping[iCoords] for iCoords in validCoords]))
        
        #extract those streamlines as a subset
        streamsSubset=streamlines[streamIndexes]
        
        #not actually sure how this will work with a messy bundle
        #reorient streamlines so that endpoints 1 and endpoints 2 mean something
        #using quickbundles to get a centroid, because the actual method
        #is buried in obscurity
        qb = QuickBundles(threshold=100)
        cluster = qb.cluster(streamsSubset)
        
        #there should be only one with the distance setting this high
        orientedStreams=streamline.orient_by_streamline(streamsSubset, cluster.centroids[0])
        
        #create blank structure for endpoints
        endpoints=np.zeros((len(orientedStreams),6))
        #get the endpoints, taken from
        #https://github.com/dipy/dipy/blob/f149c756e09f172c3b77a9e6c5b5390cc08af6ea/dipy/tracking/utils.py#L708
        for iStreamline in range(len(orientedStreams)):
            #remember, first 3 = endpoint 1, last 3 = endpoint 2    
            endpoints[iStreamline,:]= np.concatenate([orientedStreams[iStreamline][0,:], orientedStreams[iStreamline][-1,:]])
        
        #select the appropriate endpoints
        Endpoints1=endpoints[:,0:3]
        Endpoints2=endpoints[:,3:7]
        
        #create holders for both the dispersion means and the dispersion variances
        dispersionMeans=[]
        dispersionVariances=[]
        #asym
        dispersionMeansAsym=[]
        dispersionVariancesAsym=[]
        for iBoostrap in range (bootstrapNum):
            
            #select a subset of half the whole streamline group, then 
            #find the intersection fo that set and the current voxel's streamlines
            currentBootstrapStreamsAll=np.random.randint(0,len(streamlines),bootstrapStreamNum)
            currentBootstrapStreamsSubSelect=np.in1d(streamIndexes,currentBootstrapStreamsAll)
            
            #compute the subset mean distance and variance for endpoint cluster 1
            avgEndPoint1=np.mean(Endpoints1[currentBootstrapStreamsSubSelect],axis=0)
            curNearDistsFromAvg1=cdist(Endpoints1[currentBootstrapStreamsSubSelect], np.reshape(avgEndPoint1, (1,3)), 'euclidean')
            endPoint1DistAvg=np.mean(curNearDistsFromAvg1)
            endPoint1DistVar=np.var(curNearDistsFromAvg1)
            
            #compute the subset mean distance and variance for endpoint cluster 2
            avgEndPoint2=np.mean(Endpoints2[currentBootstrapStreamsSubSelect],axis=0)
            curNearDistsFromAvg2=cdist(Endpoints2[currentBootstrapStreamsSubSelect], np.reshape(avgEndPoint2, (1,3)), 'euclidean')
            endPoint2DistAvg=np.mean(curNearDistsFromAvg2)
            endPoint2DistVar=np.var(curNearDistsFromAvg2)
        
            #for this bootstrap iteration, compute the average distance and the variance
            dispersionMeans.append(np.mean([endPoint2DistAvg,endPoint1DistAvg]))
            dispersionVariances.append(np.mean([endPoint1DistVar,endPoint2DistVar]))
            #asym
            dispersionMeansAsym.append((endPoint1DistAvg-endPoint2DistAvg)/(endPoint1DistAvg+endPoint2DistAvg))
            dispersionVariancesAsym.append((endPoint1DistVar-endPoint2DistVar)/(endPoint1DistVar+endPoint2DistVar))
        
        #now place them in the appropriate location in their respective
        #storage vectors
        meanOfMeans[iCoords]=np.mean(dispersionMeans)
        varianceOfMeans[iCoords]=np.var(dispersionMeans)
        meanOfVariances[iCoords]=np.mean(dispersionVariances)
        varianceOfVariances[iCoords]=np.var(dispersionVariances)
        
        #asym
        meanOfMeansAsym[iCoords]=np.mean(dispersionMeansAsym)
        varianceOfMeansAsym[iCoords]=np.var(dispersionMeansAsym)
        meanOfVariancesAsym[iCoords]=np.mean(dispersionVariancesAsym)
        varianceOfVariancesAsym[iCoords]=np.var(dispersionVariancesAsym)
    
    #Now that the metrics have been compute for all coordinates, create
    #3d arrays to store the output for the nifti object data
    outMeanOfMeansArray=np.zeros(referenceNifti.shape,dtype='float')
    outVarianceOfMeansArray=np.zeros(referenceNifti.shape,dtype='float')
    outMeanOfVariancesArray=np.zeros(referenceNifti.shape,dtype='float')
    outVarianceOfVariancesArray=np.zeros(referenceNifti.shape,dtype='float')
    
    #asym
    outMeanOfMeansAsymArray=np.zeros(referenceNifti.shape,dtype='float')
    outVarianceOfMeansAsymArray=np.zeros(referenceNifti.shape,dtype='float')
    outMeanOfVariancesAsymArray=np.zeros(referenceNifti.shape,dtype='float')
    outVarianceOfVariancesAsymArray=np.zeros(referenceNifti.shape,dtype='float')
    
    #iterate across each voxel coordinate
    for iCoords in range(len(subjectSpaceTractCoords)):
        #fill in the corresponding voxel's value for each metric
        outMeanOfMeansArray[imgSpaceTractVoxels[iCoords]] = meanOfMeans[iCoords]
        outVarianceOfMeansArray[imgSpaceTractVoxels[iCoords]] = varianceOfMeans[iCoords]
        outMeanOfVariancesArray[imgSpaceTractVoxels[iCoords]] = meanOfVariances[iCoords]
        outVarianceOfVariancesArray[imgSpaceTractVoxels[iCoords]] = varianceOfVariances[iCoords]
        
        #asym
        outMeanOfMeansAsymArray[imgSpaceTractVoxels[iCoords]] = meanOfMeansAsym[iCoords]
        outVarianceOfMeansAsymArray[imgSpaceTractVoxels[iCoords]] = varianceOfMeansAsym[iCoords]
        outMeanOfVariancesAsymArray[imgSpaceTractVoxels[iCoords]] = meanOfVariancesAsym[iCoords]
        outVarianceOfVariancesAsymArray[imgSpaceTractVoxels[iCoords]] = varianceOfVariancesAsym[iCoords]
    
    #create nifti objects for each metric
    meanOfMeansNifti=nib.nifti1.Nifti1Image(outMeanOfMeansArray, referenceNifti.affine, referenceNifti.header)
    varianceOfMeansNifti=nib.nifti1.Nifti1Image(outVarianceOfMeansArray, referenceNifti.affine, referenceNifti.header)
    meanOfVariancesNifti=nib.nifti1.Nifti1Image(outMeanOfVariancesArray, referenceNifti.affine, referenceNifti.header)
    varianceOfVariancesNifti=nib.nifti1.Nifti1Image(outVarianceOfVariancesArray, referenceNifti.affine, referenceNifti.header)
    
    meanOfMeansAsymNifti=nib.nifti1.Nifti1Image(outMeanOfMeansArray, referenceNifti.affine, referenceNifti.header)
    varianceOfMeansAsymNifti=nib.nifti1.Nifti1Image(outVarianceOfMeansArray, referenceNifti.affine, referenceNifti.header)
    meanOfVariancesAsymNifti=nib.nifti1.Nifti1Image(outMeanOfVariancesArray, referenceNifti.affine, referenceNifti.header)
    varianceOfVariancesAsymNifti=nib.nifti1.Nifti1Image(outVarianceOfVariancesArray, referenceNifti.affine, referenceNifti.header)
    
    return meanOfMeansNifti, varianceOfMeansNifti, meanOfVariancesNifti, varianceOfVariancesNifti, meanOfMeansAsymNifti, varianceOfMeansAsymNifti, meanOfVariancesAsymNifti, varianceOfVariancesAsymNifti

def complexStreamlinesIntersect(streamlines, maskNifti):
        import dipy.tracking.utils as ut
        import copy
        import numpy as np
        voxelInds=np.asarray(np.where(maskNifti.get_fdata())).T
        doubleResAffine=np.copy(maskNifti.affine)
        doubleResAffine[0:3,0:3]=doubleResAffine[0:3,0:3]*.5
        lin_T, offset =ut._mapping_to_voxel(doubleResAffine)
        inds = ut._to_voxel_coordinates(streamlines._data, lin_T, offset)
        streamlineCoords=np.floor((inds*.5))

def subsetStreamsNodesByROIboundingBox_test(streamlines, maskNifti):
    """subsetStreamsByROIboundingBox(streamlines, maskNifti):
    #subsets the input set of streamlines to only those that have nodes within the box
    #
    # INPUTS
    #
    # -streamlines: streamlines to be subset
    #
    # -maskNifti:  the mask nifti from which a bounding box is to be extracted, which will be used to subset the streamlines
    #
    # OUTPUTS
    #
    # -criteriaVec:  a boolean vector indicating which streamlines contain nodes within the bounding box.
    #
    """
    #compute distance tolerance
    from dipy.core.geometry import dist_to_corner
    from dipy.tracking.streamline import Streamlines
    import numpy as np
    
    import time
    
    #begin timing
    t1_start=time.process_time()
    
    #use distance to corner to set tolerance
    dtc = dist_to_corner(maskNifti.affine)
    
    #convert them to subject space
    subjectSpaceBounds=subjectSpaceMaskBoundaryCoords(maskNifti)
    #expand to accomidate tolerance
    subjectSpaceBounds[0,:]=subjectSpaceBounds[0,:]-dtc
    subjectSpaceBounds[1,:]=subjectSpaceBounds[1,:]+dtc
    
    nodeArray=[]
    for iStreamlines in streamlines:
        nodeArray.append(iStreamlines[np.all(np.asarray([np.logical_and(iStreamlines[:,iDems]>subjectSpaceBounds[0,iDems],iStreamlines[:,iDems]<subjectSpaceBounds[1,iDems]) for iDems in list(range(subjectSpaceBounds.shape[1])) ]),axis=0)])
 
    
    #map and lambda function to extract the nodes within the bounds
    outIndexes=np.where(list(map(lambda x: x.size>0, nodeArray)))[0]
    outStreams=Streamlines(nodeArray)
    
    #stop timing
    t1_stop=time.process_time()
    # get the elapsed time
    modifiedTime=t1_stop-t1_start
    
    print('Tractogram subseting complete in ' +str(modifiedTime) +', '+str(len(outIndexes)) + ' of ' + str(len(streamlines)) + ' within mask boundaries')
    return outIndexes, outStreams   
    

def applyNiftiCriteriaToTract_DIPY_Cython(streamlines, maskNifti, includeBool, operationSpec):
    """segmentTractMultiROI(streamlines, roisvec, includeVec, operationsVec):
    #Iteratively applies ROI-based criteria, uses a range of dipy functions
    #and custom made functions to expedite the typically slow segmentation process
    #
    #adapted from https://github.com/dipy/dipy/blob/master/dipy/tracking/streamline.py#L200
    #basically a variant of
    #https://github.com/DanNBullock/wma/blob/33a02c0373d6742ddf07fd8ac3c8481662577743/utilities/wma_SegmentFascicleFromConnectome.m
    #
    #INPUTS
    #
    # -streamlines: appropriately formatted list of candidate streamlines, e.g. a candidate tractome
    #
    # -maskNifti: a nifti Mask containing only 1s and 0s
    #
    # -includeBool: a boolean indicator of whether you want the associated ROI to act as an INCLUSION or EXCLUSION ROI (True=inclusion)
    #
    # -operationSpec: operation specification, one following instructions on which streamline nodes to asses (and how)
    #    "any" : any point is within tol from ROI. Default.
    #    "all" : all points are within tol from ROI.
    #    "either_end" : either of the end-points is within tol from ROI
    #    "both_end" : both end points are within tol from ROI.
    #
    # OUTPUTS
    #
    # - outBoolVec: boolean vec indicating streamlines that survived operation
    """
    #still learning how to import from modules
    from dipy.tracking.utils import near_roi
    import numpy as np
    import dipy.tracking.utils as ut
    import nibabel as nib
    from nilearn import masking 
    import scipy
    from dipy.tracking.vox2track import _streamlines_in_mask
    
    #perform some input checks
    validOperations=["any","all","either_end","both_end"]
    if np.logical_not(np.in1d(operationSpec, validOperations)):
         raise Exception("applyNiftiCriteriaToTract Error: input operationSpec not understood.")
    
    if np.logical_not(type(maskNifti).__name__=='Nifti1Image'):
        raise Exception("applyNiftiCriteriaToTract Error: input maskNifti not a nifti.")
    
    #the conversion to int may cause problems if the input isn't convertable to int.  Then again, the point of this is to raise an error, so...
    elif np.logical_not(np.all(np.unique(maskNifti.get_fdata()).astype(int)==[0, 1])): 
        raise Exception("applyNiftiCriteriaToTract Error: input maskNifti not convertable to 0,1 int mask.  Likely not a mask.")
        
    if np.logical_not(isinstance(includeBool, bool )):
        raise Exception("applyNiftiCriteriaToTract Error: input includeBool not a bool.  See input description for usage")
        
    lin_T, offset =ut._mapping_to_voxel(maskNifti.affine)
    criteriaStreamsBool=_streamlines_in_mask( list(streamlines), maskNifti.get_fdata().astype(np.uint8), lin_T, offset)
    
    if includeBool==True:
        #initalize an out bool vec
        outBoolVec=np.zeros(len(streamlines), dtype=bool)
        #set the relevant entries to true
        outBoolVec[criteriaStreamsBool.astype(bool)]=True
    elif includeBool==False:          
        #initalize an out bool vec
        outBoolVec=np.ones(len(streamlines), dtype=bool)
        #set the relevant entries to true
        outBoolVec[criteriaStreamsBool.astype(bool)]=False
    
    return outBoolVec
   
def crossSectionGIFsFromNifti(overlayNifti,refAnatT1,saveDir, blendOption=False):
    import nibabel as nib
    #use dipy to create the density mask
    from dipy.tracking import utils
    import numpy as np
    from glob import glob
    import os
    from nilearn.image import reorder_img  
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
    from matplotlib import figure
    
    
    #resample crop (doesn't seem to work)
    #[refAnatT1,overlayNifti]=dualCropNifti(refAnatT1,overlayNifti)
    
    #RAS reoreintation
    refAnatT1=reorder_img(refAnatT1)
    overlayNifti=reorder_img(overlayNifti)
                 
    
    #refuses to plot single slice, single image
    #from nilearn.plotting import plot_stat_map
    #outImg=plot_stat_map(stat_map_img=densityNifti,bg_img=refAnatT1, cut_coords= 1,display_mode='x',cmap='viridis')
   
    
    #obtain boundary coords in subject space in order to
    #use plane generation function
    convertedBoundCoords=subjectSpaceMaskBoundaryCoords(refAnatT1)
    
    dimsList=['x','y','z']
    #brute force with matplotlib
    import matplotlib.pyplot as plt
    for iDims in list(range(len(refAnatT1.shape))):
        #this assumes that get_zooms returns zooms in subject space and not image space orientation
        # which may not be a good assumption if the orientation is weird
        subjectSpaceSlices=np.arange(convertedBoundCoords[0,iDims],convertedBoundCoords[1,iDims],refAnatT1.header.get_zooms()[iDims])
        #get the desired broadcast shape and delete current dim value
        broadcastShape=list(refAnatT1.shape)
        del broadcastShape[iDims]
        
        #iterate across slices
        for iSlices in list(range(len(subjectSpaceSlices))):
            #set the slice list entry to the appropriate singular value
            currentSlice=makePlanarROI(refAnatT1, subjectSpaceSlices[iSlices], dimsList[iDims])

            #set up the figure
            fig,ax = plt.subplots()
            ax.axis('off')
            #kind of overwhelming to do this in one line
            refData=np.rot90(np.reshape(refAnatT1.get_fdata()[currentSlice.get_fdata().astype(bool)],broadcastShape),1)
            plt.imshow(refData, cmap='gray', interpolation='nearest')
            #kind of overwhelming to do this in one line
            overlayData=np.rot90(np.reshape(overlayNifti.get_fdata()[currentSlice.get_fdata().astype(bool)],broadcastShape),1)
            plt.imshow(np.ma.masked_where(overlayData<=0,overlayData), cmap='jet', alpha=.75, interpolation='nearest',vmin=1,vmax=np.nanmax(overlayNifti.get_fdata()))
            curFig=plt.gcf()
            cbaxes = inset_axes(curFig.gca(), width="5%", height="80%", loc=5) 
            plt.colorbar(cax=cbaxes, ticks=[0.,np.nanmax(overlayNifti.get_fdata())], orientation='vertical')
            curFig.gca().yaxis.set_ticks_position('left')
            curFig.gca().tick_params( colors='white')
            # we use *2 in order to afford room for the subsequent blended images
            figName='dim_' + str(iDims) +'_'+  str(iSlices*2).zfill(3)+'.png'
            plt.savefig(figName,bbox_inches='tight',pad_inches=0.0)
            plt.clf()
            
    import os        
    from PIL import Image
    from glob import glob
    #create blened images to smooth transitions between slices
    if blendOption:
        for iDims in list(range(len(refAnatT1.shape))):
            dimStem='dim_' + str(iDims)
            imageList=sorted(glob(dimStem+'*.png'))
            for iImages in list(range(len(imageList)-1)):
                thisImage=Image.open(imageList[iImages])
                nextImage=Image.open(imageList[iImages+1])
                blendedImage = Image.blend(thisImage, nextImage, alpha=0.5)
                # 1 + 2 * iImages fills in the name space we left earlier
                figName='dim_' + str(iDims) +'_'+  str(1+iImages*2).zfill(3)+'.png'
                blendedImage.save(figName,'png')
  
    for iDims in list(range(len(refAnatT1.shape))):
        dimStem='dim_' + str(iDims)
        img, *imgs = [Image.open(f) for f in sorted(glob(dimStem+'*.png'))]
        img.save(os.path.join(saveDir,dimStem+'.gif'), format='GIF', append_images=imgs,
                 save_all=True, duration=1, loop=0)
        plt.close('all')

        [os.remove(ipaths) for ipaths in sorted(glob(dimStem+'*.png'))]

def densityGifsOfTract(tractStreamlines,referenceAnatomy,saveDir,tractName):
    import os
    import nibabel as nib
    from glob import glob
    import numpy as np
    import dipy   

    import dipy.tracking.utils as ut
    
    tractMask=ut.density_map(tractStreamlines, referenceAnatomy.affine, referenceAnatomy.shape)
    densityNifti = nib.nifti1.Nifti1Image(tractMask, referenceAnatomy.affine, referenceAnatomy.header)
    
    #now make the niftiGifs
    crossSectionGIFsFromNifti(densityNifti,referenceAnatomy,saveDir)   

    filesToRename=[os.path.join(saveDir,'dim_'+ str(iDim) +'.gif') for iDim in range(3)]
    
    for iFiles in filesToRename:
        [path, file]=os.path.split(iFiles)
        os.rename(iFiles,os.path.join(path,tractName+'_'+file))
        
def dualCropNifti(nifti1,nifti2):
    """dualCropNifti(nifti1,nifti2):
    This function crops two niftis to the same size, using the largest of the
    two post cropped niftis to establish the consensus dimensions of the output
    nifti data blocks.
    
    Note:  this won't do much if the background values of your images haven't
    been masked / set to zero.
  
    INPUTS
    nifti1 / nifti2:  The niftis that you would like cropped to the same size
    
    OUTPUTS
    nifti1 / nifti2:  The cropped niftis

    """
    import nilearn
    from nilearn.image import crop_img, resample_to_img 
    import numpy as np
    import nibabel as nib
    
    inShape1=nifti1.shape
    inShape2=nifti2.shape

    #get 
    #nilearn doesn't handle NAN gracefully, so we have to be inelegant
    nifti1=nib.nifti1.Nifti1Image(np.nan_to_num(nifti1.get_fdata()), nifti1.affine, nifti1.header)
    nifti2=nib.nifti1.Nifti1Image(np.nan_to_num(nifti2.get_fdata()), nifti2.affine, nifti2.header)
    
    cropped1=crop_img(nifti1)
    cropped2=crop_img(nifti2)
    
    # find max values in each dimension and create a dummy
    maxDimShape=np.max(np.asarray([cropped1.shape,cropped2.shape]),axis=0)
    dummyArray=np.zeros(maxDimShape)
    #arbitrarily selecting the first nifit should be fine, they should be aligned
    dummyNifti= nib.nifti1.Nifti1Image(dummyArray, nifti1.affine, nifti1.header)
    
    outNifti1=resample_to_img(cropped1,dummyNifti)
    outNifti2=resample_to_img(cropped2,dummyNifti)
    
    return outNifti1, outNifti2


def wmc2tracts(inputTractogram,classification,outdir):
    """wmc2tracts(trk_file,classification,outdir):
     convert a wmc .mat + tract input into separate files for tracts 
    based on @giulia-berto's
 https://github.com/FBK-NILab/app-classifyber-segmentation/blob/1.3/wmc2trk.py
 
    INPUTS
    
    inputTractogram: an input tractogram
    
    classification: a .mat WMC input that corresponds to the input tractogram
    WMC described here: https://brainlife.io/datatype/5cc1d64c44947d8aea6b2d8b
    
    outdir: the output directory in which to save the output files
 
    """
    import nibabel as nib
    from scipy.io import loadmat
    import dipy
    import numpy as np
    from dipy.io.stateful_tractogram import Space, StatefulTractogram
    from dipy.io.streamline import load_tractogram, save_tractogram
    import dipy.tracking.utils as ut
    import os
    
    if isinstance(inputTractogram,str):
        inputTractogram=inputTractogram=nib.streamlines.load(inputTractogram)
        print('input tractogram loaded')
    
    if isinstance(classification,str):
        #load the .mat object
        classification=loadmat(classification)
        #it comes back as an eldridch horror, so parse it appropriately
        #get the index vector
        indices=classification['classification'][0][0]['index'][0]
        #get the names vector
        tractIdentities=[str(iIdenties) for iIdenties in classification['classification'][0][0][0][0]]
    
    for tractID in range(len(tractIdentities)):
        #remove unncessary characters, adds unnecessary '[]'
        t_name = tractIdentities[tractID][2:-2]
        tract_name = t_name.replace(' ', '_')
        idx_tract = np.array(np.where(indices==tractID+1))[0]
        tract = inputTractogram.streamlines[idx_tract]
        
        #dipy is stubborn and wants a reference nifti for some reason
        #fineI'llDoItMyself.jpg
        tractBounds=np.asarray([np.min(tract._data,axis=0),np.max(tract._data,axis=0)])
        roundedTractBounds=np.asarray([np.floor(tractBounds[0,:]),np.ceil(tractBounds[1,:])])
        constructedAffine=np.eye(4)
        constructedAffine[0:3,3]=tractBounds[0,:]
 
        lin_T, offset =ut._mapping_to_voxel(constructedAffine)
        inds = ut._to_voxel_coordinates(tract._data, lin_T, offset)
        
        testBounds=np.asarray([np.min(inds,axis=0),np.max(inds,axis=0)])
        
        #now create a dummy nifit, because that's what dipy demands
        dataShape=(roundedTractBounds[1,:]-roundedTractBounds[0,:]).astype(int)
        #adding a +1 pad because it yells otherwise?
        dummyData=np.zeros(dataShape+1)
        dummyNifti= nib.nifti1.Nifti1Image(dummyData, constructedAffine)
        
        
        voxStreams=dipy.tracking.streamline.transform_streamlines(tract,np.linalg.inv(constructedAffine))
        statefulTractogramOut=StatefulTractogram(voxStreams, dummyNifti, Space.VOX)
        
        #save it in the same format as the input
        if isinstance(inputTractogram, nib.streamlines.tck.TckFile):
            out_filename=os.path.join(outdir,tract_name + '.tck')
        elif  isinstance(inputTractogram, nib.streamlines.trk.TrkFile):
            out_filename=os.path.join(outdir,tract_name + '.trk')
        
        save_tractogram(statefulTractogramOut,out_filename)

def radialTractEndpointFingerprintPlot(tractStreamlines,atlas,atlasLookupTable,tractName=None,saveDir=None):
    """radialTractEndpointFingerprintPlot(tractStreamlines,atlas,atlasLookupTable,tractName=None,saveDir=None)
    A function used to generate radial fingerprint plots for input tracts, as 
    found in Folloni 2021

    Parameters
    ----------
    tractStreamlines : streamlines type
        Streamlines corresponding to the tract of interest
    atlas : Nifti, int based
        A nifti atlas that will be used to determine the endpoint connectivity
    atlasLookupTable : pandas dataframe or file loadable to pandas dataframe
        A dataframe of the atlas lookup table which includes the labels featured
        in the atlas and their identities.  These identities will be used
        to label the periphery of the radial plot.
    tractName : string, optional
        The name of the tract to be used as a label in the output figure. No 
        input will result in there being no corresponding label. The default is None.
    saveDir : TYPE, optional
        The directory in which to save the resultant radial plot. No input
        will result in no save. The default is None.

    Returns
    -------
    The figure generated

    """ 
    import pandas as pd
    import seaborn as sns
    import matplotlib.pyplot as plt
    import nibabel as nib
    import dipy
    import numpy as np
    from dipy.segment.clustering import QuickBundles
    from dipy.tracking.utils import reduce_labels
    from dipy.tracking import utils
    import dipy.tracking.streamline as streamline
    from dipy.segment.metric import ResampleFeature
    from dipy.segment.metric import AveragePointwiseEuclideanMetric
    from dipy.segment.metric import MinimumAverageDirectFlipMetric
    import itertools
    
    #use dipy function to reduce labels to contiguous values
    relabeledAtlasData=reduce_labels(atlas.get_fdata())[0]
    #create new nifti object
    renumberedAtlasNifti=nib.Nifti1Image(relabeledAtlasData, atlas.affine, atlas.header)
    
    #take care of tractogram and treamline issues
    if isinstance(tractStreamlines,str):
        loadedTractogram=nib.streamlines.load(tractStreamlines)
        tractStreamlines=loadedTractogram.streamlines
    elif  isinstance(tractStreamlines,nib.streamlines.tck.TckFile):
        tractStreamlines=tractStreamlines.streamlines
    
    
    feature = ResampleFeature(nb_points=100)
    #metric = MinimumAverageDirectFlipMetric(feature)
    metric = AveragePointwiseEuclideanMetric(feature)
    qb = QuickBundles(threshold=100,metric=metric)
    cluster = qb.cluster(tractStreamlines)
    #there should be only one with the distance setting this high
    tractStreamlines=streamline.orient_by_streamline(tractStreamlines, cluster.centroids[0])
    
    #test endpoints
    endpoints1=[istreamlines[0,:] for istreamlines in tractStreamlines]
    endpoints2=[istreamlines[-1,:] for istreamlines in tractStreamlines]
    
    #segment tractome into connectivity matrix from parcellation
    M, grouping=utils.connectivity_matrix(tractStreamlines, atlas.affine, label_volume=renumberedAtlasNifti.get_fdata().astype(int),
                            return_mapping=True,
                            mapping_as_streamlines=False)
    #get the keys so that you can iterate through them later
    keyTargets=list(grouping.keys())
    keyTargetsArray=np.asarray(keyTargets)
    
    #work with the input lookup table
    if isinstance(atlasLookupTable,str):
        if atlasLookupTable[-4:]=='.csv':
            atlasLookupTable=pd.read_csv(atlasLookupTable)
        elif (atlasLookupTable[-4:]=='.xls',atlasLookupTable[-5:]=='.xlsx'):
            atlasLookupTable=pd.read_excel(atlasLookupTable)
    
    if len(atlasLookupTable)>len(np.unique(relabeledAtlasData)):
        #infer which column contains the original identities
        #presumably, this would be the LUT column with the largest number of matching labels with the original atlas.
        matchingLabelsCount=[len(list(set(atlasLookupTable[iColumns]).intersection(set(np.unique(atlas.get_fdata()).astype(int))))) for iColumns in atlasLookupTable.columns.to_list()]
        #there's an edge case here relabeled atlas == the original atlas AND the provided LUT was larger (what would the extra entries be?)
        #worry about that later
        columnBestGuess=atlasLookupTable.columns.to_list()[matchingLabelsCount.index(np.max(matchingLabelsCount))]
        #we can also take this opportunity to pick the longest average column, which is likely the optimal label name
        entryLengths=atlasLookupTable.applymap(str).applymap(len)
        labelColumnGuess=entryLengths.mean(axis=0).idxmax()
        
        #now that we have the guess, get the corresponding row entries, and reset the index.
        #This should make the index match the renumbered label values.
        LUTWorking=atlasLookupTable[atlasLookupTable[columnBestGuess].isin(np.unique(atlas.get_fdata()).astype(int)).values].reset_index(drop=True)
        
    for iEndpoints in range(keyTargetsArray.shape[1]):
        uniqueLabelValues=np.unique(keyTargetsArray[:,iEndpoints])
        plotLabels=[]
        plotValues=[]
        for iUniqueLabelValues in uniqueLabelValues:
            targetKeys=list(itertools.compress(keyTargets,[keyTargetsArray[:,iEndpoints]==iUniqueLabelValues][0]))
            #could also probably just sum up the column in the matrix
            counts=[len(grouping[iKeys]) for iKeys in targetKeys]
            #append to the plotValue list
            plotValues.append(np.sum(counts))
            plotLabels.append(LUTWorking[labelColumnGuess].iloc[iUniqueLabelValues])
        
def basicRadarPlot(values, labels):
    """
    https://www.python-graph-gallery.com/web-circular-barplot-with-matplotlib
    

    Parameters
    ----------
    values : TYPE
        DESCRIPTION.
    labels : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    import numpy as np
    from textwrap import wrap
    
    #convert the values to log scale
    values=np.log10(values)
    
    # Values for the x axis
    ANGLES = np.linspace(0.05, 2 * np.pi - 0.05, len(labels), endpoint=False)
    
    # Set default font to Bell MT
    plt.rcParams.update({"font.family": "Bell MT"})

    GREY12 = "#1f1f1f"
    # Set default font color to GREY12
    plt.rcParams["text.color"] = GREY12

    # The minus glyph is not available in Bell MT
    # This disables it, and uses a hyphen
    plt.rc("axes", unicode_minus=False)

    # Colors
    COLORS = ["#6C5B7B","#C06C84","#F67280","#F8B195"]

    # Colormap
    cmap = mpl.colors.LinearSegmentedColormap.from_list("my color", COLORS, N=256)

    # Normalizer
    #norm = mpl.colors.Normalize(vmin=TRACKS_N.min(), vmax=TRACKS_N.max())

    # Normalized colors. Each number of tracks is mapped to a color in the 
    # color scale 'cmap'
    #COLORS = cmap(norm(TRACKS_N))

    # Some layout stuff ----------------------------------------------
    # Initialize layout in polar coordinates
    fig, ax = plt.subplots(figsize=(9, 12.6), subplot_kw={"projection": "polar"})

    # Set background color to white, both axis and figure.
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.set_theta_offset(1.2 * np.pi / 2)
    ax.set_ylim(-.5, np.max(values)*1.3)

    # Add geometries to the plot -------------------------------------
    # See the zorder to manipulate which geometries are on top

    # Add bars to represent the cumulative track lengths
    ax.bar(ANGLES, values, color=COLORS, alpha=0.9, width=(3.1415/(len(values)))*1.5 )
    
    #overly specific to aparcaseg, fix later
    #try and do split lines
    for iREGION in range(len(labels)):
        if 'ctx_lh_G_' in labels[iREGION]:
            labels[iREGION]=labels[iREGION].replace('ctx_lh_G_','ctx_lh_G\n')
        elif 'ctx_lh_S_' in labels[iREGION]:
            labels[iREGION]=labels[iREGION].replace('ctx_lh_S_','ctx_lh_S\n')
        elif 'ctx_lh_G\nand_S_' in labels[iREGION]:
            labels[iREGION]=labels[iREGION].replace('ctx_lh_G\nand_S_','ctx_lh_G_and_S\n')
            
    for iREGION in range(len(labels)):
        if 'ctx_rh_G_' in labels[iREGION]:
            labels[iREGION]=labels[iREGION].replace('ctx_rh_G_','ctx_rh_G\n')
        elif 'ctx_rh_S_' in labels[iREGION]:
            labels[iREGION]=labels[iREGION].replace('ctx_rh_S_','ctx_rh_S\n')
        elif 'ctx_rh_G\nand_S_' in labels[iREGION]:
            labels[iREGION]=labels[iREGION].replace('ctx_rh_G\nand_S_','ctx_rh_G_and_S\n')

    REGION = ["\n".join(wrap(r, 5, break_long_words=False)) for r in labels]
    
    #XTICKS = ax.xaxis.get_major_ticks()
    #for tick in XTICKS:
    #    tick.set_pad(10)
    
    YTICKS = ax.yaxis.get_major_ticks()
    YTICKS[-2].set_visible(False)
    YTICKS[-1].set_visible(False)
    
    #ax.spines["start"].set_color("none")
    ax.spines["polar"].set_color("none")
    
    ax.xaxis.grid(False)
    ax.set_xticks(ANGLES)
    ax.set_xticklabels(REGION, size=14);
    ax.text(0, np.max(values)-.5, "Log10  # \n of streamlines", rotation=-69, 
        ha="center", va="center", size=12, zorder=12)

def dipyPlotTract(streamlines):
    import numpy as np
    from fury import actor, window
    from dipy.tracking.streamline import transform_streamlines
    import matplotlib
    from matplotlib import cm

    scene = window.Scene()
    scene.clear()
    
    #colormap for main tract
    cmap = matplotlib.cm.get_cmap('seismic')
    #colormap for neck
    neckCmap = matplotlib.cm.get_cmap('spring')
       
    colors = [cmap(np.array(range(streamline.shape[0]))/streamline.shape[0]) for streamline in streamlines]
    
    #find the neck nodes
    neckNodes=findTractNeckNode(streamlines)
    
    #steal come code from orientTractUsingNeck to color the neck
    #now get the node that's 5 "ahead" and 5 "behind" the neck node
    lookDistance=10
    aheadNodes=[]
    behindNodes=[]
    for iStreamlines in range(len(streamlines)):
       #A check to make sure you've got room to do this indexing on both sides
       if np.logical_and((len(streamlines[iStreamlines])-neckNodes[iStreamlines])>lookDistance,(len(streamlines[iStreamlines])-(len(streamlines[iStreamlines])-neckNodes[iStreamlines]))>lookDistance):
           aheadNodes.append(neckNodes[iStreamlines]+lookDistance)
           behindNodes.append(neckNodes[iStreamlines]-lookDistance)
       #otherwise do the best you can
       else:
           #if there's a limit to how many nodes are available ahead, do the best you can
           spaceAhead=np.abs(neckNodes[iStreamlines][0]-len(streamlines[iStreamlines]))
           if spaceAhead<lookDistance:
               aheadWindow=spaceAhead-1
           else:
               aheadWindow=lookDistance
           #if there's a limit to how many nodes are available behind, do the best you can
           spaceBehind=np.abs(len(streamlines[iStreamlines])-(len(streamlines[iStreamlines])-neckNodes[iStreamlines][0]))
           if spaceBehind<lookDistance:
               behindWindow=spaceBehind-1
           else:
               behindWindow=lookDistance
           
           #append the relevant values
           aheadNodes.append(neckNodes[iStreamlines]+(aheadWindow))
           behindNodes.append(neckNodes[iStreamlines]-(behindWindow))
    
    aheadNodes=np.asarray(aheadNodes).flatten()
    behindNodes=np.asarray(behindNodes).flatten()
           
    for iStreamlines in range(len(streamlines)):
        colors[iStreamlines][behindNodes[iStreamlines]:aheadNodes[iStreamlines]]=neckCmap(np.array(range(aheadNodes[iStreamlines]-behindNodes[iStreamlines]))/(aheadNodes[iStreamlines]-behindNodes[iStreamlines]))
    
    stream_actor = actor.line(streamlines, colors, linewidth=0.2)

    scene.add(stream_actor)

    scene.set_camera(position=(-176.42, 118.52, 128.20),
                 focal_point=(113.30, 128.31, 76.56),
                 view_up=(0.18, 0.00, 0.98))    

    # window.show(scene, size=(600, 600), reset_camera=False)
    window.record(scene, out_path='badStreamsFigure.png', size=(600, 600))
    window.exit()

def orientTractUsingNeck(streamlines):
    """orientTractUsingNeck(streamlines)
    A function which uses the neck of a (presumed) tract to flip consituent
    streamlines so that they are all in the same orientation.  This function
    exists because dipy's streamline.orient_by_streamline doesn't work, at
    at least not when used with a centroid streamline

    Parameters
    ----------
    streamlines : nibabel.streamlines.array_sequence.ArraySequence
        A collection of streamlines presumably corresponding to a tract.
        Unknown functionality if a random collection of streamlines is used

    Returns
    -------
    streamlines : nibabel.streamlines.array_sequence.ArraySequence 
        The input streamlines, but with the appropriate streamlines flipped 
        such that all streamlines proceed in the same orientation

    """
    import numpy as np
    from scipy.spatial.distance import cdist
    
    #get the neck nodes for the tract
    neckNodes=findTractNeckNode(streamlines)
    
    #obtain the coordinates for each of these neck nodes
    neckCoords=[]
    for iStreamlines in range(len(streamlines)):
        neckCoords.append(streamlines[iStreamlines][neckNodes[iStreamlines]])
    
    #now get the node that's 5 "ahead" and 5 "behind" the neck node
    lookDistance=10
    aheadNodes=[]
    behindNodes=[]
    for iStreamlines in range(len(streamlines)):
       #A check to make sure you've got room to do this indexing on both sides
       if np.logical_and((len(streamlines[iStreamlines])-neckNodes[iStreamlines])>lookDistance,(len(streamlines[iStreamlines])-(len(streamlines[iStreamlines])-neckNodes[iStreamlines]))>lookDistance):
           aheadNodes.append(streamlines[iStreamlines][neckNodes[iStreamlines]+lookDistance])
           behindNodes.append(streamlines[iStreamlines][neckNodes[iStreamlines]-lookDistance])
       #otherwise do the best you can
       else:
           #if there's a limit to how many nodes are available ahead, do the best you can
           spaceAhead=np.abs(neckNodes[iStreamlines][0]-len(streamlines[iStreamlines]))
           if spaceAhead<lookDistance:
               aheadWindow=spaceAhead-1
           else:
               aheadWindow=lookDistance
           #if there's a limit to how many nodes are available behind, do the best you can
           spaceBehind=np.abs(len(streamlines[iStreamlines])-(len(streamlines[iStreamlines])-neckNodes[iStreamlines][0]))
           if spaceBehind<lookDistance:
               behindWindow=spaceBehind-1
           else:
               behindWindow=lookDistance
           
           #append the relevant values
           aheadNodes.append(streamlines[iStreamlines][neckNodes[iStreamlines]+(aheadWindow)])
           behindNodes.append(streamlines[iStreamlines][neckNodes[iStreamlines]-(behindWindow)])
           
    # use the coords that are at the heart of the tract
    neckCoords=np.zeros([len(streamlines),3])

    for iStreamlines in range(len(streamlines)):
         neckCoords[iStreamlines,:]=(streamlines[iStreamlines][neckNodes[iStreamlines]])
         
    neckNodeDistances=cdist(np.atleast_2d(np.mean(neckCoords,axis=0)),neckCoords)
    aheadDistances=np.squeeze(cdist(np.atleast_2d(np.mean(np.squeeze(np.asarray(aheadNodes)),axis=0)),np.squeeze(np.asarray(aheadNodes))))
    behindDistances=np.squeeze(cdist(np.atleast_2d(np.mean(np.squeeze(np.asarray(behindNodes)),axis=0)),np.squeeze(np.asarray(behindNodes))))

    orientationGuideAheadNode=aheadNodes[np.where(np.min(aheadDistances)==aheadDistances)[0][0]].flatten()
    orientationGuideBehindNode=behindNodes[np.where(np.min(behindDistances)==behindDistances)[0][0]].flatten()
    #iterate across streamlines
    flipCount=0
    for iStreamlines in range(len(streamlines)):
        #compute the distances from the comparison orientation for both possible
        #orientations
        sumDistanceOrientation1=np.sum([cdist(np.atleast_2d(orientationGuideAheadNode),np.atleast_2d(aheadNodes[iStreamlines])),cdist(np.atleast_2d(orientationGuideBehindNode),np.atleast_2d(behindNodes[iStreamlines]))])
        sumDistanceOrientation2=np.sum([cdist(np.atleast_2d(orientationGuideAheadNode),np.atleast_2d(behindNodes[iStreamlines])),cdist(np.atleast_2d(orientationGuideBehindNode),np.atleast_2d(aheadNodes[iStreamlines]))])
        #flip if necessary
        if sumDistanceOrientation2<sumDistanceOrientation1:
            streamlines[iStreamlines]= streamlines[iStreamlines][::-1]
            flipCount=flipCount+1
            
            
    #there's still a few that aren't flipping right, so now we use peer pressure
    
            
    print(str(flipCount) + ' of ' + str(len(streamlines)) + ' streamlines flipped')
    #I don't know that I trust the whole in place flipping mechanism, so
    #we will return the modified streamline object from this function
    return streamlines
        
        