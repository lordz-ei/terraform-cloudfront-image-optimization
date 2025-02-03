import os
import json
import boto3
import io
from urllib.parse import unquote
from PIL import Image
import PIL.Image

# AWS S3 Client
s3_client = boto3.client("s3")

# Load Environment Variables
S3_ORIGINAL_IMAGE_BUCKET = os.getenv("originalImageBucketName")
S3_TRANSFORMED_IMAGE_BUCKET = os.getenv("transformedImageBucketName")
TRANSFORMED_IMAGE_CACHE_TTL = int(os.getenv("transformedImageCacheTTL", 86400))  # Default: 1 day
MAX_IMAGE_SIZE = int(os.getenv("maxImageSize", 5000))  # Max allowed width/height

def lambda_handler(event, context):
    """ Main Lambda function for processing image requests """

    # Ensure it's a GET request
    if event.get("requestContext", {}).get("http", {}).get("method") != "GET":
        return send_error(400, "Only GET method is supported")

    # Extract image path from request
    path = event["rawPath"]  # Example: /images/rio/1.jpeg/format=webp,width=100
    query_params = event.get("queryStringParameters", {})

    # Parse image path and transformation options
    image_key, transformations = parse_image_path(path, query_params)

    if not image_key:
        return send_error(400, "Invalid image request path")

    # Check if the transformed image already exists
    transformed_key = generate_transformed_key(image_key, transformations)
    if check_s3_object_exists(S3_TRANSFORMED_IMAGE_BUCKET, transformed_key):
        return redirect_to_s3(S3_TRANSFORMED_IMAGE_BUCKET, transformed_key)

    # Fetch original image from S3
    image = fetch_image_from_s3(S3_ORIGINAL_IMAGE_BUCKET, image_key)
    if image is None:
        return send_error(404, "Original image not found")

    # Process image
    processed_image = process_image(image, transformations)

    # Save transformed image to S3
    upload_image_to_s3(S3_TRANSFORMED_IMAGE_BUCKET, transformed_key, processed_image)

    # Redirect to the cached image
    return redirect_to_s3(S3_TRANSFORMED_IMAGE_BUCKET, transformed_key)

def parse_image_path(path, query_params):
    """ Extract image key and transformation parameters from the request """
    parts = path.strip("/").split("/")
    if len(parts) < 2:
        return None, {}

    image_key = "/".join(parts[:-1])  # Extract image path
    transformations = query_params  # Extract transformations from query params

    return image_key, transformations

def generate_transformed_key(image_key, transformations):
    """ Generate a unique S3 key for the transformed image """
    transformation_string = "_".join([f"{k}-{v}" for k, v in transformations.items()])
    return f"transformed/{transformation_string}/{image_key}"

def check_s3_object_exists(bucket, key):
    """ Check if an object exists in S3 """
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except s3_client.exceptions.ClientError:
        return False

def fetch_image_from_s3(bucket, key):
    """ Fetch an image from S3 """
    try:
        s3_object = s3_client.get_object(Bucket=bucket, Key=key)
        return Image.open(io.BytesIO(s3_object["Body"].read()))
    except Exception as e:
        print(f"Error fetching image: {e}")
        return None

def process_image(image, transformations):
    """ Apply transformations (resize, format change) """
    width = int(transformations.get("width", image.width))
    height = int(transformations.get("height", image.height))
    format_ = transformations.get("format", "JPEG").upper()

    if width > MAX_IMAGE_SIZE or height > MAX_IMAGE_SIZE:
        width, height = min(width, MAX_IMAGE_SIZE), min(height, MAX_IMAGE_SIZE)

    image = image.resize((width, height))

    output_stream = io.BytesIO()
    image.save(output_stream, format=format_)
    output_stream.seek(0)

    return output_stream

def upload_image_to_s3(bucket, key, image_stream):
    """ Upload the transformed image to S3 """
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=image_stream,
        ContentType="image/jpeg",
        CacheControl=f"public, max-age={TRANSFORMED_IMAGE_CACHE_TTL}"
    )

def redirect_to_s3(bucket, key):
    """ Redirect to the transformed image stored in S3 """
    s3_url = f"https://{bucket}.s3.amazonaws.com/{key}"
    return {
        "statusCode": 302,
        "headers": {
            "Location": s3_url
        }
    }

def send_error(status_code, message):
    """ Return an error response """
    return {
        "statusCode": status_code,
        "body": json.dumps({"error": message}),
        "headers": {"Content-Type": "application/json"}
    }
