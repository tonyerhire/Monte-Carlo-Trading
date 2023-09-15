import boto3

def lambda_handler(event, context):
    ec2_client = boto3.client('ec2')
    # Get the list of all running instances
    instances = ec2_client.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    # Extract instance IDs
    instance_ids = [instance['InstanceId'] for reservation in instances['Reservations'] for instance in reservation['Instances']]
    # Terminate all running instances
    if instance_ids:
        ec2_client.terminate_instances(InstanceIds=instance_ids)
        return f"Terminating {len(instance_ids)} EC2 instances: {', '.join(instance_ids)}"
    else:
        return "No running EC2 instances found."