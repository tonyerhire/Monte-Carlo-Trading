import boto3
import json
 

def lambda_handler(event, context):
    s3_client = boto3.client('s3')
    bucket_name = 'cloud6442385bk'
    object_key = 'data_list.json'
    response = s3_client.get_object(Bucket=bucket_name, Key=object_key) 
    data_list = json.load(response['Body'])
    
    return data_list
 



