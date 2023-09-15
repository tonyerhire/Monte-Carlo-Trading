import boto3

def lambda_handler(event, context):
    # Create an EC2 client
    ec2 = boto3.client('ec2')

    # Get a list of all EC2 instances
    response = ec2.describe_instances()

    # Initialize lists for IPs and IDs
    instance_ips = []
    instance_ids = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if instance['State']['Name'] == 'running': 
                instance_ips.append(instance.get('PublicIpAddress', 'N/A'))
                instance_ids.append(instance['InstanceId'])



    num_running_instances = len(instance_ips)  # Count the number of running instances

    return instance_ips, instance_ids, num_running_instances

