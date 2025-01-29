import boto3
import base64
import os
from dotenv import load_dotenv

# Load AWS credentials from .env
load_dotenv()

class KMSManager:
    def __init__(self):
        self.kms_client = boto3.client(
            'kms',
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        self.key_id = os.getenv("KMS_KEY_ID")

    def encrypt(self, plaintext):
        response = self.kms_client.encrypt(
            KeyId=self.key_id,
            Plaintext=plaintext
        )
        ciphertext = base64.b64encode(response['CiphertextBlob']).decode()
        return ciphertext

    def decrypt(self, ciphertext):
        decoded_blob = base64.b64decode(ciphertext)
        response = self.kms_client.decrypt(
            CiphertextBlob=decoded_blob
        )
        return response['Plaintext'].decode()