//
//  FusionRenderer.m
//  IPhoneFusion
//
//  Created by Rom Herskovitz on 8/8/14.
//  Copyright (c) 2014 Technion. All rights reserved.
//

#import "FusionRenderer.h"
#import "Shaders.h"
#import "Consts.h"
#import <Accelerate/Accelerate.h>

//#import <eigen3/Eigen/Cholesky>
//#import <eigen3/Eigen/SVD>

@interface FusionRenderer () {
    GLuint _depthImageDisplayProgram;
    EAGLContext* _context;
    Shaders* _shaders;
    GLuint _iteration;
    
    int _imageWidth;
    int _imageHeight;
    int _imageSize;
    int _ICPWindowSize;
    int _ICPSize;
    int _volumeEdge;
    int _cubeEdge;
    int _ICPIters;
    float _cubeZPos;
    
    GLKMatrix4 _TMat;
    GLKMatrix4 _TMatInv;
    GLKMatrix4 _prevTMatInv;
    GLKMatrix3 _calMat;
    GLKMatrix3 _calMatInv;
    GLKMatrix4 _perspMat;
    GLKMatrix4 _MVPMat;
    GLKMatrix4 _cubeToGlobalMat;
    GLKMatrix4 _cubeToGlobalMatInv;
    
    double *_matA;
    double *_matATrans;
    double *_matB;
    
    GLuint _vArr;
    GLuint _quadVArr;
    GLuint _imageVArr;
    
    GLuint _vBuff;
    GLuint _quadVBuff;
    GLuint _matBuff;
    GLuint _imageVBuff;
    
    GLuint _backfaceRBuff;
    GLuint _rayCastRBuff;
    GLuint _ICPRBuff;
    
    GLuint _depthTexID;
    GLuint _depthTex;
    GLuint _volumeTexID;
    GLuint _volumeTex;
    GLuint _rayCastVTexID;
    GLuint _rayCastVTex;
    GLuint _rayCastNTexID;
    GLuint _rayCastNTex;
    GLuint _backFaceTexID;
    GLuint _backFaceTex;
    GLuint _vTexID;
    GLuint _vTex;
    GLuint _nTexID;
    GLuint _nTex;
    GLuint _filteredDepthTexID;
    GLuint _filteredDepthTex;
    
    GLuint _rayCastFBO;
    GLuint _rayCastNewFBO;
    GLuint _backFaceFBO;
    GLuint _depthToVertexFBO;
    GLuint _vertexToNormalsFBO;
    GLuint _vertexToVolumeFBO;
    GLuint _ICPFBO;
    GLuint _bilateralFilterFBO;
    
    NSLock *_openglLock;
    
    //For debug
    NSString *dir;
    NSString *file;
    
}

@end

@implementation FusionRenderer

#pragma mark - GLKViewDelegate

- (id)initWithContext:(EAGLContext*)context
           ImageWidth:(int)width
          ImageHeight:(int)height
       VolumeEdgeSize:(int)volumeEdge
         CubeEdgeSize:(int)cubeEdge
     CubeXMidPosition:(float)xPos
     CubeYMidPosition:(float)yPos
   CubeZStartPosition:(float)zPos
        ICPIterations:(int)iterations
        ICPWindowSize:(int)windowSize
{
    if (self = [super init]) {
        _context = context;
        [EAGLContext setCurrentContext:_context];
        _shaders = [[Shaders alloc] init];
        
        _imageWidth = width;
        _imageHeight = height;
        _imageSize = _imageWidth * _imageHeight;
        _ICPWindowSize = windowSize;
        _ICPSize = _imageSize / _ICPWindowSize;
        
        _volumeEdge = volumeEdge;
        _cubeEdge = cubeEdge;
        _cubeZPos = zPos;
        _ICPIters = iterations;
        
        _calMat = GLKMatrix3MakeWithArrayAndTranspose(gCalibrationMatrix);
        bool isInv;
        _calMatInv = GLKMatrix3Invert(_calMat, &isInv);
        if (!isInv) {
            NSLog(@"Failed to invert calibration matrix!!");
        }
        
        _perspMat = GLKMatrix4MakeWithArrayAndTranspose(gPerspectiveMatrix);
        _matA = (double*)calloc(_ICPSize * 6, sizeof(double));
        _matATrans = (double*)calloc(_ICPSize * 6, sizeof(double));
        _matB = (double*)calloc(_ICPSize, sizeof(double));
        
        
        _cubeToGlobalMat = GLKMatrix4Multiply(GLKMatrix4MakeTranslation(xPos, yPos, _cubeZPos),
                                               GLKMatrix4Multiply(GLKMatrix4MakeTranslation(-_cubeEdge/2.0, -_cubeEdge/2.0, 0.0),
                                               GLKMatrix4MakeScale(_cubeEdge, _cubeEdge, _cubeEdge)));
        _cubeToGlobalMatInv = GLKMatrix4Invert(_cubeToGlobalMat, &isInv);
        if (!isInv) {
            NSLog(@"Failed to invert cube to global transformation matrix!!");
        }
        
        // DEBUG
        dir = [NSSearchPathForDirectoriesInDomains(NSLibraryDirectory, NSUserDomainMask, YES) objectAtIndex:0];
        
        [self setupGL];
        
        [self restart];
        
        _openglLock = [[NSLock alloc] init];
        
        return self;
    }
    else
        return nil;
}

const GLenum discards[]  = {GL_DEPTH_ATTACHMENT};

- (void)restart
{
    //Init Variables.
    _iteration = 0;
    
    //Init matrices.
    _TMat = GLKMatrix4Identity;
    _TMatInv = GLKMatrix4Identity;
    
    //Initialize cube data with zeros.
    glUseProgram(_shaders.initVolumeProgram);
    glBindFramebuffer(GL_FRAMEBUFFER, _vertexToVolumeFBO);
    glBindVertexArray(_quadVArr);
    glViewport(0, 0, _volumeEdge, _volumeEdge);
    
    for (int i = 0; i < _volumeEdge; i++) {
        glFramebufferTextureLayer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, _volumeTex, 0, i);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    }
}


- (void)setupGL
{
    [self setupArraysAndBuffers];
    [self setupTextures];
    [self setupFBOs];
}

- (void)setupArraysAndBuffers
{
    // Initialize Cube vertex data for raycasting.
    glGenVertexArrays(1, &_vArr);
    glBindVertexArray(_vArr);
    glGenBuffers(1, &_vBuff);
    glBindBuffer(GL_ARRAY_BUFFER, _vBuff);
    glBufferData(GL_ARRAY_BUFFER, sizeof(gCubeVertexData), gCubeVertexData, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 24, BUFFER_OFFSET(0));
    glEnableVertexAttribArray(0);
//    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 24, BUFFER_OFFSET(0));
//    glEnableVertexAttribArray(1);
    glBindVertexArray(0);
    
    // Initialize Vertex data for full screen texture display.
    glGenVertexArrays(1, &_quadVArr);
    glBindVertexArray(_quadVArr);
    glGenBuffers(1, &_quadVBuff);
    glBindBuffer(GL_ARRAY_BUFFER, _quadVBuff);
    glBufferData(GL_ARRAY_BUFFER, sizeof(gQuadVertexData), gQuadVertexData, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, BUFFER_OFFSET(0));
    glEnableVertexAttribArray(0);
    glBindVertexArray(0);
    
    //Generate buffer for the matrix output.
    glGenBuffers(1, &_matBuff);
    glBindBuffer(GL_ARRAY_BUFFER, _matBuff);
    glBufferData(GL_ARRAY_BUFFER, _ICPSize * 7 * sizeof(float), NULL, GL_DYNAMIC_DRAW);
    
    glGenVertexArrays(1, &_imageVArr);
    glBindVertexArray(_imageVArr);
    
//    //Create image vertex data.
//    GLint imageVertexData[2 * _imageSize];
//    int k = 0;
//    for (int i = 0; i < _imageHeight; i++) {
//        for (int j = 0; j < _imageWidth; j++) {
//            imageVertexData[k++] = i;
//            imageVertexData[k++] = j;
//        }
//    }
//    
//    glGenBuffers(1, &_imageVBuff);
//    glBindBuffer(GL_ARRAY_BUFFER, _imageVBuff);
//    glBufferData(GL_ARRAY_BUFFER, sizeof(imageVertexData), imageVertexData, GL_STATIC_DRAW);
//    
//    glVertexAttribIPointer(0, 2, GL_INT, 0, BUFFER_OFFSET(0));
//    glEnableVertexAttribArray(0);

    //Create image vertex data.
    GLint imageVertexData[2 * _ICPSize];
    int k = 0;
    for (int i = 0; i < _imageHeight; i+=_ICPWindowSize) {
        for (int j = 0; j < _imageWidth; j+=_ICPWindowSize) {
            imageVertexData[k++] = i;
            imageVertexData[k++] = j;
        }
    }
    
    glGenBuffers(1, &_imageVBuff);
    glBindBuffer(GL_ARRAY_BUFFER, _imageVBuff);
    glBufferData(GL_ARRAY_BUFFER, sizeof(imageVertexData), imageVertexData, GL_STATIC_DRAW);
    
    glVertexAttribIPointer(0, 2, GL_INT, 0, BUFFER_OFFSET(0));
    glEnableVertexAttribArray(0);
    
    
    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);
}

- (void)setupTextures
{
    int i = 1;
    
    // Create a texture for the current depth image.
    _depthTexID = i++;
//    glActiveTexture(GL_TEXTURE0 + _depthTexID);
    glGenTextures(1, &_depthTex);
    glBindTexture(GL_TEXTURE_2D, _depthTex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexStorage2D(GL_TEXTURE_2D, 1, GL_R16F, _imageWidth, _imageHeight);
    glBindTexture(GL_TEXTURE_2D, 0);
    
    // Create the bilateral filtered depth image texture.
    _filteredDepthTexID = i++;
    glGenTextures(1, &_filteredDepthTex);
    glBindTexture(GL_TEXTURE_2D, _filteredDepthTex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexStorage2D(GL_TEXTURE_2D, 1, GL_R16F, _imageWidth, _imageHeight);
    glBindTexture(GL_TEXTURE_2D, 0);
    
    // Create the vertex data texture.
    _vTexID = i++;
//    glActiveTexture(GL_TEXTURE0 + _vTexID);
    glGenTextures(1, &_vTex);
    glBindTexture(GL_TEXTURE_2D, _vTex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA16F, _imageWidth, _imageHeight);
    glBindTexture(GL_TEXTURE_2D, 0);
    
    // Create the normals data texture.
    _nTexID = i++;
//    glActiveTexture(GL_TEXTURE0 + _nTexID);
    glGenTextures(1, &_nTex);
    glBindTexture(GL_TEXTURE_2D, _nTex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGB16F, _imageWidth, _imageHeight);
    glBindTexture(GL_TEXTURE_2D, 0);
    
    // Create the volume texture.
    _volumeTexID = i++;
//    glActiveTexture(GL_TEXTURE0 + _volumeTexID);
    glGenTextures(1, &_volumeTex);
    glBindTexture(GL_TEXTURE_3D, _volumeTex);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexStorage3D(GL_TEXTURE_3D, 1, GL_RG16F, _volumeEdge, _volumeEdge, _volumeEdge);
    glBindTexture(GL_TEXTURE_3D, 0);
    
    // Create the raycasting vertex data texture.
    _rayCastVTexID = i++;
//    glActiveTexture(GL_TEXTURE0 + _rayCastVTexID);
    glGenTextures(1, &_rayCastVTex);
    glBindTexture(GL_TEXTURE_2D, _rayCastVTex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA16F, _imageWidth, _imageHeight);
    glBindTexture(GL_TEXTURE_2D, 0);
    
    // Create the raycasting normal data texture.
    _rayCastNTexID = i++;
//    glActiveTexture(GL_TEXTURE0 + _rayCastNTexID);
    glGenTextures(1, &_rayCastNTex);
    glBindTexture(GL_TEXTURE_2D, _rayCastNTex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGB16F, _imageWidth, _imageHeight);
    glBindTexture(GL_TEXTURE_2D, 0);
    
    // Create the raycasting normal data texture.
    _backFaceTexID = i++;
//    glActiveTexture(GL_TEXTURE0 + _backFaceTexID);
    glGenTextures(1, &_backFaceTex);
    glBindTexture(GL_TEXTURE_2D, _backFaceTex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA16F, _imageWidth, _imageHeight);
    glBindTexture(GL_TEXTURE_2D, 0);
}

- (void) setupFBOs
{
    // Create FBO for bilateral filtering.
    glGenFramebuffers(1, &_bilateralFilterFBO);
    glBindFramebuffer(GL_FRAMEBUFFER, _bilateralFilterFBO);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, _filteredDepthTex, 0);
    
    //Check FBO Status for failures.
    GLenum status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
    if (status != GL_FRAMEBUFFER_COMPLETE) {
        NSLog(@"Failed to create frame buffer object: %u", status);
    }
    
    // Create FBO for the depth to vertex rendering.
    glGenFramebuffers(1, &_depthToVertexFBO);
    glBindFramebuffer(GL_FRAMEBUFFER, _depthToVertexFBO);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, _vTex, 0);
    
    //Check FBO Status for failures.
    status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
    if (status != GL_FRAMEBUFFER_COMPLETE) {
        NSLog(@"Failed to create frame buffer object: %u", status);
    }
    
    
    // New FBO for raycasting!
    glGenFramebuffers(1, &_rayCastNewFBO);
    glBindFramebuffer(GL_FRAMEBUFFER, _rayCastNewFBO);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, _rayCastVTex, 0);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT1, GL_TEXTURE_2D, _rayCastNTex, 0);
    
    GLuint attachments[2] = { GL_COLOR_ATTACHMENT0, GL_COLOR_ATTACHMENT1};
    glDrawBuffers(2,  attachments);
    
    //Check FBO Status for failures.
    status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
    if (status != GL_FRAMEBUFFER_COMPLETE) {
        NSLog(@"Failed to create frame buffer object: %u", status);
    }
    
    
    // Create FBO for the raycasting.
    glGenFramebuffers(1, &_rayCastFBO);
    glBindFramebuffer(GL_FRAMEBUFFER, _rayCastFBO);
    
    glGenRenderbuffers(1, &_rayCastRBuff);
    glBindRenderbuffer(GL_RENDERBUFFER, _rayCastRBuff);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, _imageWidth, _imageHeight);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, _rayCastRBuff);
    
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, _rayCastVTex, 0);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT1, GL_TEXTURE_2D, _rayCastNTex, 0);
    
    glDrawBuffers(2,  attachments);
    
    //Check FBO Status for failures.
    status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
    if (status != GL_FRAMEBUFFER_COMPLETE) {
        NSLog(@"Failed to create frame buffer object: %u", status);
    }
    
    // Create FBO for the raycasting - used to store the cube backface data in the texture.
    glGenFramebuffers(1, &_backFaceFBO);
    glBindFramebuffer(GL_FRAMEBUFFER, _backFaceFBO);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, _backFaceTex, 0);
    
    glGenRenderbuffers(1, &_backfaceRBuff);
    glBindRenderbuffer(GL_RENDERBUFFER, _backfaceRBuff);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, _imageWidth, _imageHeight);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, _backfaceRBuff);
    
    //Check FBO Status for failures.
    status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
    if (status != GL_FRAMEBUFFER_COMPLETE) {
        NSLog(@"Failed to create frame buffer object: %u", status);
    }
    
    // Create FBO for the vertex to normals rendering.
    glGenFramebuffers(1, &_vertexToNormalsFBO);
    glBindFramebuffer(GL_FRAMEBUFFER, _vertexToNormalsFBO);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, _nTex, 0);
    
    //Check FBO Status for failures.
    status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
    if (status != GL_FRAMEBUFFER_COMPLETE) {
        NSLog(@"Failed to create frame buffer object: %u", status);
    }
    
    // Create FBO for the depth to volume rendering.
    glGenFramebuffers(1, &_vertexToVolumeFBO);
    
    // Create FBO for the ICP.
    glGenFramebuffers(1, &_ICPFBO);
    glBindFramebuffer(GL_FRAMEBUFFER, _ICPFBO);
    glGenRenderbuffers(1, &_ICPRBuff);
    glBindRenderbuffer(GL_RENDERBUFFER, _ICPRBuff);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT16, _imageWidth, _imageHeight);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, _ICPRBuff);
    
    //Check FBO Status for failures.
    status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
    if (status != GL_FRAMEBUFFER_COMPLETE) {
        NSLog(@"Failed to create frame buffer object: %u", status);
    }
}

- (int)createMats:(float*)memoryBuffer
{
    int matAIndex = 0;
    int matBIndex = 0;
    int zeros = 0;
    for (int i = 0; i < _ICPSize; i++) {
        if (memoryBuffer[7*i] == 0.0 && memoryBuffer[7*i+1] == 0.0 && memoryBuffer[7*i+2] == 0.0) {
            zeros++;
        } else {
            for (int j = 0; j < 6; j++) {
                _matA[matAIndex++] = memoryBuffer[7*i+j];
            }
            _matB[matBIndex++] = memoryBuffer[7*i+6];
        }
    }
    return _ICPSize - zeros;
}


// TODO: Try to implement straight column wise and check performance.
- (GLKMatrix4)findMatrixWithSVD:(float*)memoryBuffer
{
    __CLPK_integer m = [self createMats:memoryBuffer];
    
    if (m <= 5) {
        return GLKMatrix4Identity;
    }
    NSLog(@"Matches: %f", ((float)m)/_ICPSize);
    
    vDSP_mtransD(_matA, 1, _matATrans, 1, 6, m);
    
    __CLPK_integer n = 6;
    __CLPK_integer nrhs = 1;
    __CLPK_integer lda = m;
    __CLPK_integer ldb = m;
    __CLPK_doublereal s[n];
    __CLPK_doublereal rcond = -1.0;
    __CLPK_integer rank;
    __CLPK_doublereal *work;
    __CLPK_integer lwork = -1.0;
    __CLPK_integer iwork[11 * 6];
    __CLPK_integer info;
    __CLPK_doublereal wkopt;
    
    dgelsd_( &m, &n, &nrhs, _matATrans, &lda, _matB, &ldb, s, &rcond, &rank, &wkopt, &lwork, iwork, &info);
    lwork = (int)wkopt;
    work = (__CLPK_doublereal*)malloc( lwork*sizeof(__CLPK_doublereal) );
    /* Solve the equations A*X = B */
    dgelsd_(&m, &n, &nrhs, _matATrans, &lda, _matB, &ldb, s, &rcond, &rank, work, &lwork, iwork, &info);
    free(work);
    
    if (info != 0) {
        NSLog(@"least squares matrix extraction failed!");
        return GLKMatrix4Identity;
    }
    
    float alpha = _matB[0];
    float beta = _matB[1];
    float gamma = _matB[2];
    float tx = _matB[3];
    float ty = _matB[4];
    float tz = _matB[5];
    
    GLKMatrix4 xRotation = GLKMatrix4MakeXRotation(alpha);
    GLKMatrix4 yRotation = GLKMatrix4MakeYRotation(beta);
    GLKMatrix4 zRotation = GLKMatrix4MakeZRotation(gamma);
    GLKMatrix4 translation = GLKMatrix4MakeTranslation(tx, ty, tz);
    return GLKMatrix4Multiply(translation, GLKMatrix4Multiply(zRotation, GLKMatrix4Multiply(yRotation, xRotation)));
}

//- (GLKMatrix4)findMatrixWithSVD:(float*)memoryBuffer
//{
//    Eigen::MatrixXd A(_ICPSize, 6);
//    Eigen::MatrixXd b(_ICPSize, 1);
//    
//    int row = 0;
//    
//    for (int i = 0; i < _ICPSize; i++) {
////        if (memoryBuffer[7*i] == 0.0 && memoryBuffer[7*i+1] == 0.0 && memoryBuffer[7*i+2] == 0.0) {
////            continue;
////        } else {
//            for (int j = 0; j < 6; j++) {
//                A(row, j) = memoryBuffer[7*i+j];
//            }
//            b(row++) = memoryBuffer[7*i+6];
////        }
//    }
//    
//    Eigen::MatrixXd AA = A.transpose() * A;
//    Eigen::MatrixXd bb = A.transpose() * b;
//    
//    Eigen::Matrix<double, 6, 1> res = AA.llt().solve(bb);
////    Eigen::Matrix<double, 6, 1> res = A.jacobiSvd(Eigen::ComputeThinU | Eigen::ComputeThinV).solve(b);
//    
//    double alpha = res(0);
//    double beta = res(1);
//    double gamma = res(2);
//    double tx = res(3);
//    double ty = res(4);
//    double tz = res(5);
//    
//    GLKMatrix4 xRotation = GLKMatrix4MakeXRotation(alpha);
//    GLKMatrix4 yRotation = GLKMatrix4MakeYRotation(beta);
//    GLKMatrix4 zRotation = GLKMatrix4MakeZRotation(gamma);
//    GLKMatrix4 translation = GLKMatrix4MakeTranslation(tx, ty, tz);
//    return GLKMatrix4Multiply(translation, GLKMatrix4Multiply(zRotation, GLKMatrix4Multiply(yRotation, xRotation)));
//}


- (void)updateWithDepthImage:(const float*)depthImage
{
//    [_openglLock lock];
    
    if (_iteration == 0) {
        glActiveTexture(GL_TEXTURE0 + _vTexID);
        glBindTexture(GL_TEXTURE_2D, _vTex);
        
        glActiveTexture(GL_TEXTURE0 + _nTexID);
        glBindTexture(GL_TEXTURE_2D, _nTex);
        
        glActiveTexture(GL_TEXTURE0 + _backFaceTexID);
        glBindTexture(GL_TEXTURE_2D, _backFaceTex);
        
        glActiveTexture(GL_TEXTURE0 + _rayCastVTexID);
        glBindTexture(GL_TEXTURE_2D, _rayCastVTex);
        
        glActiveTexture(GL_TEXTURE0 + _rayCastNTexID);
        glBindTexture(GL_TEXTURE_2D, _rayCastNTex);
        
        glActiveTexture(GL_TEXTURE0 + _volumeTexID);
        glBindTexture(GL_TEXTURE_3D, _volumeTex);
        
        glActiveTexture(GL_TEXTURE0 + _filteredDepthTexID);
        glBindTexture(GL_TEXTURE_2D, _filteredDepthTex);
    }
    
    // DEBUG
    float data_f[_imageSize];
//    file = [NSString stringWithFormat:@"%@/im%d", dir, _iteration];
//        file = [NSString stringWithFormat:@"%@/im%d", dir, 1];
    
    NSString *fn = [NSString stringWithFormat:@"im%d", _iteration];
    
    file = [[NSBundle mainBundle] pathForResource:fn ofType:nil inDirectory:@"Data"];

    NSData *data = [NSData dataWithContentsOfFile:file];
    [data getBytes:data_f length:data.length];
    file = nil;
    data = nil;
    
    //Update the depth image texture to current image.
    glActiveTexture(GL_TEXTURE0 + _depthTexID);
    glBindTexture(GL_TEXTURE_2D, _depthTex);
//    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, _imageWidth, _imageHeight,
//                    GL_RED, GL_FLOAT, depthImage);
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, _imageWidth, _imageHeight, GL_RED, GL_FLOAT, data_f);
    
    //Create vertices from the depth image.
    glBindVertexArray(_quadVArr);
 
    
    glUseProgram(_shaders.bilateralFilterProgram);
    glBindFramebuffer(GL_FRAMEBUFFER, _bilateralFilterFBO);
    glViewport(0, 0, _imageWidth, _imageHeight);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glUniform2i(bilateralFilterUniforms[UNIFORM_IMAGE_SIZE], _imageWidth, _imageHeight);
    glUniform1f(bilateralFilterUniforms[UNIFORM_SIGMA_PIXEL_INV2], 1.0 / (5.0 * 5.0));
    glUniform1f(bilateralFilterUniforms[UNIFORM_SIGMA_VAL_INV2], 1.0 / (30 * 30));
    glUniform1i(bilateralFilterUniforms[UNIFORM_DEPTH_TEXTURE], _depthTexID);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    
    glUseProgram(_shaders.depthToVertexProgram);
    glBindFramebuffer(GL_FRAMEBUFFER, _depthToVertexFBO);
    glInvalidateFramebuffer(GL_FRAMEBUFFER, 1, discards);
    glViewport(0, 0, _imageWidth, _imageHeight);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glUniform1i(depthToVertexUniforms[UNIFORM_DEPTH_TEXTURE], _depthTexID);
    glUniformMatrix3fv(depthToVertexUniforms[UNIFORM_CAL_MATRIX_INVERSE], 1, 0, _calMatInv.m);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    
    //Create Normals from the vertices.
    glUseProgram(_shaders.vertexToNormalsProgram);
    glBindFramebuffer(GL_FRAMEBUFFER, _vertexToNormalsFBO);
    glInvalidateFramebuffer(GL_FRAMEBUFFER, 1, discards);
    glViewport(0, 0, _imageWidth, _imageHeight);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glUniform1i(vertexToNormalsUniforms[UNIFORM_VERTEX_TEXTURE], _vTexID);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    
    
    if (_iteration != 0) {
        //Perform ICP.
        glBindFramebuffer(GL_FRAMEBUFFER, _ICPFBO);
        glUseProgram(_shaders.ICPMatricesProgram);
        _prevTMatInv = _TMatInv;
        
        glUniformMatrix4fv(ICPMatricesUniforms[UNIFORM_PREV_T_MATRIX_INVERSE], 1, 0, _prevTMatInv.m);
        glUniformMatrix3fv(ICPMatricesUniforms[UNIFORM_CALIBRATION_MATRIX], 1, 0, _calMat.m);
        glUniform1i(ICPMatricesUniforms[UNIFORM_VERTEX_TEXTURE], _vTexID);
        glUniform1i(ICPMatricesUniforms[UNIFORM_NORMALS_TEXTURE], _nTexID);
        glUniform1i(ICPMatricesUniforms[UNIFORM_RAY_VERTEX_TEXTURE], _rayCastVTexID);
        glUniform1i(ICPMatricesUniforms[UNIFORM_RAY_NORMALS_TEXTURE], _rayCastNTexID);

        glBindVertexArray(_imageVArr);
        glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 0, _matBuff);
        glEnable(GL_RASTERIZER_DISCARD);
        for (int i = 0; i < _ICPIters; i++) {
            glUniformMatrix4fv(ICPMatricesUniforms[UNIFORM_T_MATRIX], 1, 0, _TMat.m);
            glUniformMatrix4fv(ICPMatricesUniforms[UNIFORM_T_MATRIX_INVERSE], 1, 0, _TMatInv.m);
            
            glBeginTransformFeedback(GL_POINTS);
            glDrawArrays(GL_POINTS, 0, _ICPSize);
            glEndTransformFeedback();
            
            GLuint err = glGetError();
            if (err != 0) {
                NSLog(@"error!");
            }
            
            float* memoryBuffer = (float*)glMapBufferRange(GL_TRANSFORM_FEEDBACK_BUFFER, 0, sizeof(float) * _ICPSize * 7, GL_MAP_READ_BIT);
            _TMat = GLKMatrix4Multiply([self findMatrixWithSVD:memoryBuffer], _TMat);
//            _TMat = GLKMatrix4Multiply(_TMat, [self findMatrixWithSVD:memoryBuffer]);
            glUnmapBuffer(GL_TRANSFORM_FEEDBACK_BUFFER);
            _TMatInv = GLKMatrix4Invert(_TMat, nil);
        }
        glDisable(GL_RASTERIZER_DISCARD);
    }
    
    // Perform the depth to volume procedure.
    if (_iteration % 4 == 0) {
        
        glBindFramebuffer(GL_FRAMEBUFFER, _vertexToVolumeFBO);
        glInvalidateFramebuffer(GL_FRAMEBUFFER, 1, discards);
        glUseProgram(_shaders.vertexToVolumeProgram);
        glBindVertexArray(_quadVArr);
        glViewport(0, 0, _volumeEdge, _volumeEdge);
        
        glUniform1i(vertexToVolumeUniforms[UNIFORM_VERTEX_TEXTURE], _vTexID);
        glUniform1i(vertexToVolumeUniforms[UNIFORM_VOLUME_TEXTURE], _volumeTexID);
        glUniformMatrix3fv(vertexToVolumeUniforms[UNIFORM_CALIBRATION_MATRIX], 1, 0, _calMat.m);
        glUniformMatrix3fv(vertexToVolumeUniforms[UNIFORM_CAL_MATRIX_INVERSE], 1, 0, _calMatInv.m);
        glUniformMatrix4fv(vertexToVolumeUniforms[UNIFORM_GLOBAL_MODELVIEW_MATRIX], 1, 0, _cubeToGlobalMat.m);
        glUniformMatrix4fv(vertexToVolumeUniforms[UNIFORM_T_MATRIX], 1, 0, _TMat.m);
        glUniformMatrix4fv(vertexToVolumeUniforms[UNIFORM_T_MATRIX_INVERSE], 1, 0, _TMatInv.m);
        glUniform1f(vertexToVolumeUniforms[UNIFORM_STEP_SIZE], 1.0f / (float)_volumeEdge);
        
        GLuint vertexToVolumeAttch[4] = { GL_COLOR_ATTACHMENT0, GL_COLOR_ATTACHMENT1, GL_COLOR_ATTACHMENT2, GL_COLOR_ATTACHMENT3};
        glDrawBuffers(4,  vertexToVolumeAttch);

        for (int i = 0; i < _volumeEdge; i+=4) {
//            float layer = (float)i / ((float)_volumeEdge-1.0);
            float layer = (float)i / (float)_volumeEdge;
            glUniform1f(vertexToVolumeUniforms[UNIFORM_LAYER], layer);
            glFramebufferTextureLayer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, _volumeTex, 0, i);
            glFramebufferTextureLayer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT1, _volumeTex, 0, i+1);
            glFramebufferTextureLayer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT2, _volumeTex, 0, i+2);
            glFramebufferTextureLayer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT3, _volumeTex, 0, i+3);
            
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
            glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
        }
    }
    
    glBindFramebuffer(GL_FRAMEBUFFER, _rayCastNewFBO);
    glUseProgram(_shaders.rayCastingNewProgram);
    glBindVertexArray(_quadVArr);
    glViewport(0, 0, _imageWidth, _imageHeight);
    
    glUniform1f(rayCastingNewUniforms[UNIFORM_STEP_SIZE], 1.0f/(float)_volumeEdge);
    glUniform1i(rayCastingNewUniforms[UNIFORM_VOLUME_TEXTURE], _volumeTexID);
    glUniformMatrix4fv(rayCastingNewUniforms[UNIFORM_GLOBAL_MODELVIEW_MATRIX], 1, 0, _cubeToGlobalMat.m);
    glUniformMatrix4fv(rayCastingNewUniforms[UNIFORM_GLOBAL_MODELVIEW_MATRIX_INVERSE], 1, 0, _cubeToGlobalMatInv.m);
    glUniformMatrix4fv(rayCastingNewUniforms[UNIFORM_T_MATRIX], 1, 0, _TMat.m);
    glUniformMatrix3fv(rayCastingNewUniforms[UNIFORM_CAL_MATRIX_INVERSE], 1, 0, _calMatInv.m);
    glUniform3f(rayCastingNewUniforms[UNIFORM_VOLUME_MIN], 0.0, 0.0, 0.0);
    glUniform3f(rayCastingNewUniforms[UNIFORM_VOLUME_MAX], 1.0, 1.0, 1.0);
    glUniform2f(rayCastingNewUniforms[UNIFORM_IMAGE_SIZE], _imageWidth, _imageHeight);
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    
    
    _iteration++;
//    [_openglLock unlock];
}

- (void)glkView:(GLKView *)view drawInRect:(CGRect)rect {
//    [_openglLock lock];
    
    GLuint dispWidth = _imageWidth * 1.7;
    GLuint dispHeight = _imageHeight * 1.7;
    
    //Display the raycasted vertices.
    glViewport(0, 0, dispWidth, dispHeight);
    
    glUseProgram(_shaders.depthImageDisplayProgram);
    glBindVertexArray(_quadVArr);
    
    glUniform1i(depthDisplayUniforms[UNIFORM_VERTEX_TEXTURE], _rayCastNTexID);
//    glUniform1i(depthDisplayUniforms[UNIFORM_VERTEX_TEXTURE], _rayCastVTexID);
    glUniformMatrix4fv(depthDisplayUniforms[UNIFORM_T_MATRIX_INVERSE], 1, 0, _TMatInv.m);
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    
    glViewport(dispWidth, 0, dispWidth, dispHeight);
    glUniformMatrix4fv(depthDisplayUniforms[UNIFORM_T_MATRIX_INVERSE], 1, 0, GLKMatrix4Identity.m);
    glUniform1i(depthDisplayUniforms[UNIFORM_VERTEX_TEXTURE], _nTexID);
//    glUniform1i(depthDisplayUniforms[UNIFORM_VERTEX_TEXTURE], _vTexID);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    
//    [_openglLock unlock];
}

- (void)dealloc
{
    //TODO: Finish full tear down!!
    free(_matA);
    free(_matB);
    
    glDeleteBuffers(1, &_vBuff);
    glDeleteBuffers(1, &_quadVBuff);
    glDeleteBuffers(1, &_imageVBuff);
    glDeleteBuffers(1, &_matBuff);
    
    glDeleteRenderbuffers(1, &_rayCastRBuff);
    
    glDeleteVertexArrays(1, &_vArr);
    glDeleteVertexArrays(1, &_quadVArr);
    glDeleteVertexArrays(1, &_imageVArr);
    
    glDeleteFramebuffers(1, &_rayCastFBO);
    glDeleteFramebuffers(1, &_rayCastNewFBO);
    glDeleteFramebuffers(1, &_vertexToVolumeFBO);
    glDeleteFramebuffers(1, &_depthToVertexFBO);
    glDeleteFramebuffers(1, &_backFaceFBO);
    glDeleteFramebuffers(1, &_vertexToNormalsFBO);
}

@end
