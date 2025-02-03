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
    # An example of expected path is /images/rio/1.jpeg/format=auto,width=100 or /images/rio/1.jpeg/original where /images/rio/1.jpeg is the path of the original image
    imagePathArray = event["requestContext"]["http"]["path"].split('/')
    # get the requested image operations
    operationsPrefix = imagePathArray.pop()
    # get the original image path images/rio/1.jpg
    imagePathArray.pop(0)
    originalImagePath = '/'.join(imagePathArray)

    startTime = time.perf_counter() * 1000
    # Downloading original image
    try:
        getOriginalImageCommandOutput = s3Client.get_object(Bucket=S3_ORIGINAL_IMAGE_BUCKET, Key=originalImagePath)
        print(f"Got response from S3 for {originalImagePath}")
        originalImageBody = getOriginalImageCommandOutput["Body"].read()
        contentType = getOriginalImageCommandOutput.get("ContentType")
    except Exception as error:
        return sendError(500, 'Error downloading original image', error)

    try:
        # Open the image using Pillow
        transformedImage = Image.open(io.BytesIO(originalImageBody))
    except Exception as error:
        return sendError(500, 'Error opening original image', error)

    # Get image orientation to rotate if needed
    imageMetadata = transformedImage._getexif() if hasattr(transformedImage, "_getexif") else None

    # execute the requested operations 
    operationsParts = operationsPrefix.split(',')
    operationsJSON = dict(op.split('=') for op in operationsParts if '=' in op)
    # variable holding the server timing header value
    timingLog = 'img-download;dur=' + str(int(time.perf_counter() * 1000 - startTime))
    startTime = time.perf_counter() * 1000
    try:
        # check if resizing is requested
        resizingOptions = {}
        if 'width' in operationsJSON:
            resizingOptions['width'] = int(operationsJSON['width'])
        if 'height' in operationsJSON:
            resizingOptions['height'] = int(operationsJSON['height'])
        if resizingOptions:
            # Get current image size
            orig_width, orig_height = transformedImage.size
            new_width = resizingOptions.get('width')
            new_height = resizingOptions.get('height')
            # Calculate the missing dimension to maintain aspect ratio if needed
            if new_width and not new_height:
                new_height = int((orig_height * new_width) / orig_width)
            elif new_height and not new_width:
                new_width = int((orig_width * new_height) / orig_height)
            transformedImage = transformedImage.resize((new_width, new_height))
        # check if rotation is needed
        if imageMetadata and 274 in imageMetadata:
            # Use Pillow's auto rotation based on EXIF data
            transformedImage = ImageOps.exif_transpose(transformedImage)
        # check if formatting is requested
        if 'format' in operationsJSON:
            isLossy = False
            fmt = operationsJSON['format']
            if fmt == 'jpeg':
                contentType = 'image/jpeg'
                isLossy = True
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
                contentType = 'image/jpeg'
                isLossy = True
            output_format = fmt.upper() if fmt != 'jpeg' else 'JPEG'
            # Prepare parameters for saving
            save_kwargs = {}
            if 'quality' in operationsJSON and isLossy:
                save_kwargs['quality'] = int(operationsJSON['quality'])
            # Convert the image to the specified format by saving to a buffer
            buffer = io.BytesIO()
            transformedImage.save(buffer, format=output_format, **save_kwargs)
            transformedImageBytes = buffer.getvalue()
        else:
            # If not format is precised, Sharp converts svg to png by default https://github.com/aws-samples/image-optimization/issues/48
            if contentType == 'image/svg+xml':
                contentType = 'image/png'
            buffer = io.BytesIO()
            # Preserve original format if not specified; Pillow may not support SVG so we default to PNG conversion
            transformedImage.save(buffer, format=transformedImage.format if transformedImage.format else 'PNG')
            transformedImageBytes = buffer.getvalue()
    except Exception as error:
        return sendError(500, 'error transforming image', error)
    timingLog = timingLog + ',img-transform;dur=' + str(int(time.perf_counter() * 1000 - startTime))

    # handle gracefully generated images bigger than a specified limit (e.g. Lambda output object limit)
    imageTooBig = len(transformedImageBytes) > MAX_IMAGE_SIZE

    # upload transformed image back to S3 if required in the architecture
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
            # If the generated image file is too big, send a redirection to the generated image on S3, instead of serving it synchronously from Lambda. 
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

    # Return error if the image is too big and a redirection to the generated image was not possible, else return transformed image
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
    print('APPLICATION ERROR', body)
    print(error)
    
if __name__ == "__main__":
    # Example event for testing purposes
    test_event = {
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/images/rio/1.jpeg/format=jpeg,width=100"
            }
        }
    }
    # Call handler for testing
    response = handler(test_event)
    print(response)