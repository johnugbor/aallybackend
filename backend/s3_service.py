import boto3
import os
from dotenv import load_dotenv

load_dotenv()

class S3Service:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION")
        )
        self.bucket = os.getenv("S3_BUCKET_NAME")

    def upload_manual(self, file_obj, filename):
        self.s3.upload_fileobj(file_obj, self.bucket, f"manuals/{filename}")
        return f"https://{self.bucket}.s3.amazonaws.com/manuals/{filename}"

s3_handler = S3Service()