import boto3
import time
ec2 = boto3.resource('ec2')
def lambda_handler(event, context):
    num_instances = int(event['key1'])
    response = ec2.create_instances(
            ImageId='ami-04ffc7fb456ecd7c2',
            MinCount=num_instances,
            MaxCount=num_instances,
            InstanceType='t2.micro',
            KeyName='us-east-1kp',
            SecurityGroups=['SSH']
        )

            
    return 