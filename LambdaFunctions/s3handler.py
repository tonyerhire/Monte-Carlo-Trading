import json
import boto3

def lambda_handler(event, context):
    # Get the payload from the event
    payload = event.get('key1')
    json_data = json.loads(payload)
    bucket_name = 'cloud6442385bk'
    file_name = 'data_list.json'
    s3 = boto3.resource('s3')
    s3.Object(bucket_name, file_name).put(Body=json.dumps(json_data))
