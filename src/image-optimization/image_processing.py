# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import time
import io
import base64
import boto3
from PIL import Image, ImageOps

# Initialize the S3 client
s3Client = boto3.client('s3')

S3_ORIGINAL_IMAGE_BUCKET = os.environ.get('originalImageBucketName')
S3_TRANSFORMED_IMAGE_BUCKET = os.environ.get('transformedImageBucketName')
TRANSFORMED_IMAGE_CACHE_TTL = os.environ.get('transformedImageCacheTTL')
MAX_IMAGE_SIZE = int(os.environ.get('maxImageSize'))

def handler(event, context=None):
    # Validate if this is a GET request
    if not event.get("requestContext") or not event["requestContext"].get("http") or not (event["requestContext"]["http"].get("method") == 'GET'):
        return sendError(400, 'Only GET method is supported', event)
    
    # Example expected path:
    # /images/rio/1.jpeg/format=jpeg,width=100 or /images/rio/1.png/format=jpeg,width=100
    # where /images/rio/1.jpeg is the key of the original image in S3.
    imagePathArray = event["requestContext"]["http"]["path"].split('/')
    # The last element is the operations (e.g., format, width, etc.)
    operationsPrefix = imagePathArray.pop()
    # Remove the leading empty element (if the path starts with a slash)
    if imagePathArray[0] == "":
        imagePathArray.pop(0)
    # The remaining elements form the original image path
    originalImagePath = '/'.join(imagePathArray)
    
    startTime = time.perf_counter() * 1000
    # Download the original image from S3
    try:
        getOriginalImageCommandOutput = s3Client.get_object(Bucket=S3_ORIGINAL_IMAGE_BUCKET, Key=originalImagePath)
        print(f"Got response from S3 for {originalImagePath}")
        originalImageBody = getOriginalImageCommandOutput["Body"].read()
        contentType = getOriginalImageCommandOutput.get("ContentType")
    except Exception as error:
        return sendError(500, 'Error downloading original image', error)
    
    # Open the image using Pillow
    try:
        transformedImage = Image.open(io.BytesIO(originalImageBody))
    except Exception as error:
        return sendError(500, 'Error opening original image', error)
    
    # Get image orientation from EXIF to auto-rotate if needed
    imageMetadata = transformedImage._getexif() if hasattr(transformedImage, "_getexif") else None
    
    # Process the requested operations
    operationsParts = operationsPrefix.split(',')
    operationsJSON = dict(op.split('=') for op in operationsParts if '=' in op)
    
    # Track timing for diagnostics
    timingLog = 'img-download;dur=' + str(int(time.perf_counter() * 1000 - startTime))
    startTime = time.perf_counter() * 1000
    
    try:
        # Resize image if width or height is provided
        resizingOptions = {}
        if 'width' in operationsJSON:
            resizingOptions['width'] = int(operationsJSON['width'])
        if 'height' in operationsJSON:
            resizingOptions['height'] = int(operationsJSON['height'])
        if resizingOptions:
            orig_width, orig_height = transformedImage.size
            new_width = resizingOptions.get('width')
            new_height = resizingOptions.get('height')
            # Calculate the missing dimension to maintain aspect ratio if only one is provided
            if new_width and not new_height:
                new_height = int((orig_height * new_width) / orig_width)
            elif new_height and not new_width:
                new_width = int((orig_width * new_height) / orig_height)
            transformedImage = transformedImage.resize((new_width, new_height))
        
        # Auto-rotate the image based on EXIF data if available
        if imageMetadata and 274 in imageMetadata:
            transformedImage = ImageOps.exif_transpose(transformedImage)
        
        # Check if formatting is requested
        if 'format' in operationsJSON:
            fmt = operationsJSON['format']
            isLossy = False
            if fmt == 'jpeg':
                contentType = 'image/jpeg'
                isLossy = True
                # Convert image to RGB if it has transparency (alpha channel)
                if transformedImage.mode in ('RGBA', 'LA') or (transformedImage.mode == 'P' and 'transparency' in transformedImage.info):
                    transformedImage = transformedImage.convert('RGB')
            elif fmt == 'gif':
                contentType = 'image/gif'
            elif fmt == 'webp':
                contentType = 'image/webp'
                isLossy = True
            elif fmt == 'png':
                contentType = 'image/png'
            elif fmt == 'avif':
                contentType = 'image/avif'
                isLossy = True
            else:
                # Default to JPEG if an unsupported format is specified
                contentType = 'image/jpeg'
                isLossy = True
                if transformedImage.mode in ('RGBA', 'LA') or (transformedImage.mode == 'P' and 'transparency' in transformedImage.info):
                    transformedImage = transformedImage.convert('RGB')
            
            # Set the output format accordingly
            output_format = fmt.upper() if fmt != 'jpeg' else 'JPEG'
            # Prepare any save parameters (such as quality for lossy formats)
            save_kwargs = {}
            if 'quality' in operationsJSON and isLossy:
                save_kwargs['quality'] = int(operationsJSON['quality'])
            
            # Save the transformed image to a buffer in the requested format
            buffer = io.BytesIO()
            transformedImage.save(buffer, format=output_format, **save_kwargs)
            transformedImageBytes = buffer.getvalue()
        else:
            # If no explicit format is requested, maintain the original format.
            # For example, if the image is an SVG, convert it to PNG.
            if contentType == 'image/svg+xml':
                contentType = 'image/png'
            buffer = io.BytesIO()
            # Save using the original image format if available, otherwise default to PNG.
            transformedImage.save(buffer, format=transformedImage.format if transformedImage.format else 'PNG')
            transformedImageBytes = buffer.getvalue()
    except Exception as error:
        return sendError(500, 'Error transforming image', error)
    
    timingLog = timingLog + ',img-transform;dur=' + str(int(time.perf_counter() * 1000 - startTime))
    
    # Determine if the generated image is too large (e.g., exceeding Lambda's payload limits)
    imageTooBig = len(transformedImageBytes) > MAX_IMAGE_SIZE
    
    # Upload the transformed image back to S3 if a bucket is specified
    if S3_TRANSFORMED_IMAGE_BUCKET:
        startTime = time.perf_counter() * 1000
        try:
            s3Client.put_object(
                Body=transformedImageBytes,
                Bucket=S3_TRANSFORMED_IMAGE_BUCKET,
                Key=originalImagePath + '/' + operationsPrefix,
                ContentType=contentType,
                CacheControl=TRANSFORMED_IMAGE_CACHE_TTL
            )
            timingLog = timingLog + ',img-upload;dur=' + str(int(time.perf_counter() * 1000 - startTime))
            # If the image is too big, redirect to the S3 object rather than returning it directly.
            if imageTooBig:
                return {
                    "statusCode": 302,
                    "headers": {
                        "Location": "/" + originalImagePath + "?" + operationsPrefix.replace(",", "&"),
                        "Cache-Control": "private,no-store",
                        "Server-Timing": timingLog
                    }
                }
        except Exception as error:
            logError('Could not upload transformed image to S3', error)
    
    # Return an error if the image is too big and a redirection wasn't possible, otherwise return the transformed image
    if imageTooBig:
        return sendError(403, 'Requested transformed image is too big', '')
    else:
        return {
            "statusCode": 200,
            "body": base64.b64encode(transformedImageBytes).decode('utf-8'),
            "isBase64Encoded": True,
            "headers": {
                "Content-Type": contentType,
                "Cache-Control": TRANSFORMED_IMAGE_CACHE_TTL,
                "Server-Timing": timingLog
            }
        }

def sendError(statusCode, body, error):
    logError(body, error)
    return { "statusCode": statusCode, "body": body }

def logError(body, error):
    print('APPLICATION ERROR:', body)
    print(error)

if __name__ == "__main__":
    # Example event for local testing purposes.
    test_event = {
        "requestContext": {
            "http": {
                "method": "GET",
                # Example: convert a PNG image to JPEG with a width of 100 pixels.
                "path": "/images/rio/1.png/format=jpeg,width=100"
            }
        }
    }
    response = handler(test_event)
    print(response)