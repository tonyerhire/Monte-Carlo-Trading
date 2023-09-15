The system is made of up 7 lambda functions

1. CheckRunningInstances.py - Checks if any instances are currently running
2. DeleteEc2Instances.py - Deletes all ec2 instances present
3. ec2handler.py - Creates the ec2 instances
4. LambdaFunc_cloudcw.py - This function handles the risk calculations for lambda
5. LambdaFuncCheckEc2Resources.py - This functions returns the instance ip's and id's of all running instances
6. s3handler.py - This function sends the trading signal data from local to s3
7. ReadS3Data.py - This function reads the data from s3 


The system has a script called ec2_script.py which handles risk calculations for ec2

The index.py contains the main code used containing all endpoints 

Note: Currently the system is a bit fragile as some error checks have not been implemented meaning for the system to work properly endpoints calls would need to be run chronologically I.e some endpoints assume another endpoint has been called before they are called for example the resources_ready endpoint for ec2 is responsible for getting  the instances ip/id and hence this would need to be called before analysis endpoint.