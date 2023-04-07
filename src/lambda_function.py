# ====================================================================
# To autoscale DMS instance vertically
# ======================================

# must be the first import in files with lambda function handlers
import lambdainit
import lambdalogging
import json
import boto3
import botocore
import random
import time
import os
import config
import replication_inst_class

LOG = lambdalogging.getLogger(__name__)
#events_client = boto3.client('events', 'us-east-1')
#cloudwatch = boto3.client('cloudwatch', 'us-east-1')
#lambda_client = boto3.client('lambda', 'us-east-1')
dms_client = boto3.client('dms', 'us-east-1')
#sns = boto3.client('sns', 'us-east-1')
#s3_client = boto3.resource('s3', 'us-east-1')


# To check if the DMS replication instance exists ------
# If yes send the detials of 'Replication instance' describe-----
def get_replication_instance_details(replication_instance_name):
    """Returns instance details given instance name """
    try:
        # Get all the replication instances list. We can add filters to simplify code, to improve this piece
        replication_instances_details = dms_client.describe_replication_instances(
            Filters=[
                {
                    'Name': 'replication-instance-id',
                    'Values': [replication_instance_name]
                }
            ]
        )
        #print("replication_instances_details = ", replication_instances_details)
    except Exception as e:
        LOG.error("Got Error = ", str(e))
        replication_instances_details = ''

    instance = replication_instances_details['ReplicationInstances'][0]
    #print("instance = ", type(instance))
    return instance


# To get the Replcation tasks associated with Replication instance------
def get_replication_tasks(replication_instance_arn):
    """Returns the ist of replication tasks"""
    existing_tasks = []
    #dms_client = boto3.client('dms', 'us-east-1')
    replication_tasks = dms_client.describe_replication_tasks()
    for task in replication_tasks['ReplicationTasks']:
        if task['ReplicationInstanceArn'] == replication_instance_arn:
            existing_tasks.append(task)
    return existing_tasks


# Return the next higher/lower instance type to which the instance will be modified --------
# Loads the json from S3, path is mentioned in lambda evironment variable -----------------
def get_next_instance_class(existing_instance_class, scale_type):
    """Return the next higher/lower instance type to which the instance will be modified.
    scale_type: cpu_high, cpu_low,  memory_low
    """

    LOG.debug("existing_instance_class = ", existing_instance_class)
    LOG.debug("scale_type = ", scale_type)

    instance_types = json.loads(
        replication_inst_class.instance_class_json_string)

    ## If autoscaling up or down is disabled in json resource file then quit ###
    autoscaling_up_enabled = instance_types['autoscaling_up_enabled']
    autoscaling_down_enabled = instance_types['autoscaling_down_enabled']

    if (scale_type == 'cpu_high') and autoscaling_up_enabled == 'false':
        LOG.info('Autoscaling UP is disabled in: Quitting now.. Bye!!!')
        return
    elif (scale_type == 'cpu_low' or scale_type == 'memory_low') and autoscaling_down_enabled == 'false':
        LOG.info('Autoscaling DOWN is disabled in: Quitting now.. Bye!!!')
        return
    ###### resource file autoscaling configration check complete ######

    next_instance_type = instance_types[existing_instance_class][scale_type]

    LOG.info('existing_instance_type: ', existing_instance_class,
          ', next_instance_type: ', next_instance_type)

    if next_instance_type == 'no_action':
        LOG.info('Not taking action for :',
              existing_instance_class, ' for :', scale_type)
        return 'no_action'
    return next_instance_type


# Called from below Lambda function, triggered from AWS Alarm via SNS-------------
def dms_event_handler(event, context):

    # Get our replication instance name
    # DMS replication instance name....
    replication_instance_name = event['Trigger']['Dimensions'][0]['value']

    alarm_name = event['AlarmName']   # dms_cpu_low or dms_cpu_high....

    LOG.debug("replication_instance_name = ", replication_instance_name)
    LOG.debug("alarm_name = ", alarm_name)

    # Get replication instance name is valid and if yes get the details-----
    replication_instance_details = get_replication_instance_details(
        replication_instance_name)

    if replication_instance_details == '':
        LOG.error("Not a valid replication Intance Name")
        return 0
    else:

        # Get arn and existing class of the instance that we would need for modification
        replication_instance_arn = replication_instance_details['ReplicationInstanceArn']
        replication_instance_class = replication_instance_details['ReplicationInstanceClass']
        replication_instance_status = replication_instance_details['ReplicationInstanceStatus']

    #print("replication_instance_status = ", replication_instance_status)

    # if for whatever reason instance is not in available then quit. (This will happen when already one alarm is already modifying the instane)
    if replication_instance_status != 'available':
        LOG.error('Instance status must be available to make changes to it. Current status of instance: ',
              replication_instance_details['ReplicationInstanceIdentifier'], ' is: ', replication_instance_status)
        return 0

    # get scale type cpu-high/cpu-low. e.g. dms-cpu-high --------------

    # Note: Cpu and Memory will be in sync -------------------

    if str(alarm_name) == os.environ['dms_cpu_utilisation_high']:
        event_type = "cpu_high"
    elif str(alarm_name) == os.environ['dms_cpu_utilisation_low']:
        event_type = "cpu_low"
    # If our free memory is high, we need to HIGHER instace
    elif str(alarm_name) == os.environ['dms_free_memory_low']:
        event_type = "cpu_high"
    elif str(alarm_name) == os.environ['dms_free_storage_low']:
        event_type = "free_storage_low"

    #print("replication_instance_class 1111 = ", replication_instance_class)
    LOG.debug("event_type 1111 = ", event_type)

    # CPU and Memory -----------------------------------------
    if event_type == "cpu_high" or event_type == "cpu_low":
        # Get the next higher instance class
        next_instance_type = get_next_instance_class(
            replication_instance_class, event_type)
        #print("next_instance_type = ", next_instance_type)

        if next_instance_type == 'no_action':  # next_instance_type will be no_action if up/down scaling is not possible
            LOG.info('Cannot up/down scale as per config file in S3')
            return 0

        LOG.debug("replication_instance_arn = ", replication_instance_arn)
        replication_tasks = shorten_replication_tasks(
            get_replication_tasks(replication_instance_arn))
        LOG.debug("replication_tasks = ", replication_tasks)

        # Upgrade/Downgrade the instance to next higher/lower instance class
        dms_client.modify_replication_instance(
            ReplicationInstanceArn=replication_instance_arn,
            ApplyImmediately=True,
            ReplicationInstanceClass=next_instance_type
        )

    # Free Space --------------------------------------------------
    if event_type == "free_storage_low":

        try:
            response = dms_client.describe_replication_instances(
                Filters=[
                    {
                        'Name': 'replication-instance-arn',
                        'Values': [
                            replication_instance_arn,
                        ]
                    },
                ],
            )

            nCurrentStorage = response['ReplicationInstances'][0]['AllocatedStorage']

        except:
            LOG.error("Error in getting Storage value------")
            return

        # Note: Storage high means 'Free Space is more than 80%'
        # Note: Storage low means 'Free Space is less than 80%'

        if event_type == "free_storage_low":
            nCurrentStorage += 50

        # Not to reduce store below 100 at any point of time ---------------
        if nCurrentStorage <= 100:
            return

        # Upgrade/Downgrade the instance storage to 50GB
        dms_client.modify_replication_instance(
            ReplicationInstanceArn=replication_instance_arn,
            ApplyImmediately=True,
            AllocatedStorage=nCurrentStorage
        )

    return


# To get the replication tasks associated with a DMS Replication Instance-------
def shorten_replication_tasks(replication_tasks):
    """Returns only relevent fields form replication_tasks object """
    tasks = []
    for task in replication_tasks:
        t1 = {
            "ReplicationTaskIdentifier": task['ReplicationTaskIdentifier'],
            "Status": task['Status'],
            "ReplicationTaskArn": task['ReplicationTaskArn']
        }
        tasks.append(t1)

    return tasks

# Function Called from AWS Lambda function-------------------


def lambda_handler(event, context):

    # Find the type of event scheduled or dms
    dms_alarms = [os.environ['dms_cpu_utilisation_high'], os.environ['dms_cpu_utilisation_low'],
                  os.environ['dms_free_memory_low'], os.environ['dms_free_storage_low']]

    message = ''
    LOG.debug("Inisde main function= ", type(event))
    event = json.dumps(event)
    event = json.loads(event)

    #print("pppp", type(event))
    try:

        # if event is from SNS then we need to convert the message from text to json
        #message = json.loads(event["Records"][0]["Sns"]["Message"])
        message = event["Records"][0]["Sns"]["Message"]

    except Exception as e:
        # if message is not from SNS then its from scheduled cloudwatch event and we process it directly
        #print("Got Error in Message = ", e)
        message = event

    # To execute from Alarms only---------------
    if "AlarmName" in message:
        # Json doesn't understand single quotes-----
        message = message.replace("\'", "\"")
        message = json.loads(message)

        if message["AlarmName"] in dms_alarms:
            dms_event_handler(message, context)  # Activated from AWS SNS------
    return 0