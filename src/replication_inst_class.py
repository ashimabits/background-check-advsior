
import json

instance_class_json_string = '''
{
    "version": "2.4.2",
    "autoscaling_up_enabled": "true",
    "autoscaling_down_enabled": "true",
    "timeout": 10,
    "dms.t3.micro": {
        "cpu_high": "dms.t3.small",
        "cpu_low": "no_action"
    },
    "dms.t3.small": {
        "cpu_high": "dms.t3.medium",
        "cpu_low": "dms.t3.micro"
    },
    "dms.t3.medium": {
        "cpu_high": "dms.t3.large",
        "cpu_low": "dms.t3.small"
    },
    "dms.t3.large": {
        "cpu_high": "dms.c5.large",
        "cpu_low": "dms.t3.medium"
    },
    "dms.c5.large": {
        "cpu_high": "dms.c5.xlarge",
        "cpu_low": "no_action"
    },
    "dms.c5.xlarge": {
        "cpu_high": "dms.c5.2xlarge",
        "cpu_low": "dms.c5.large"
    },
    "dms.c5.2xlarge": {
        "cpu_high": "dms.c5.4xlarge",
        "cpu_low": "dms.c5.xlarge"
    },
    "dms.c5.4xlarge": {
        "cpu_high": "dms.r5.8xlarge",
        "cpu_low": "dms.c5.2xlarge"
    },
    "dms.r5.large": {
        "cpu_high": "dms.r5.xlarge",
        "cpu_low": "no_action"
    },
    "dms.r5.xlarge": {
        "cpu_high": "dms.r5.2xlarge",
        "cpu_low": "dms.r5.large"
    },
    "dms.r5.2xlarge": {
        "cpu_high": "dms.r5.4xlarge",
        "cpu_low": "dms.r5.xlarge"
    },
    "dms.r5.4xlarge": {
        "cpu_high": "dms.r5.8xlarge",
        "cpu_low": "dms.r5.2xlarge"
    },
    "dms.r5.8xlarge": {
        "cpu_high": "no_action",
        "cpu_low": "dms.r5.4xlarge"
    }
}
'''


instance_types = json.loads(instanceClass_json_string)

#print("instance_types = ", type(instance_types))