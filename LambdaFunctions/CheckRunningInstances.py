import boto3

def lambda_handler(event, context):
    # Create EC2 client
    ec2 = boto3.client('ec2')
    
    # Describe EC2 instances
    response = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    
    # Check if there are running instances
    running_instances = len(response['Reservations']) > 0
    
    return not running_instances