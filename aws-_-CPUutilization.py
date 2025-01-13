#!/usr/bin/python

import boto3
import sys
import os
import requests
from collections import OrderedDict
from datetime import datetime, timedelta

'''
In your /etc/munin/plugin-conf/munin-node
[aws-*]
env.aws_access_key_id [KEY_ID]
env.aws_secret_access_key [ACCESS_KEY]
env.region_name [REGION]
env.database [RDSINSTANCE]

For munin EC2:
ln -s /usr/share/munin/plugins/aws-_-CPUutilization.py aws-ec2-CPUutilization
For munin RDS:
ln -s /usr/share/munin/plugins/aws-_-CPUutilization.py aws-rds-CPUutilization
'''

class Monitor:
    def __init__(self, typemon):
        self.typemon = typemon
        self.cloudwatch = boto3.client('cloudwatch',
            aws_access_key_id=os.environ.get('aws_access_key_id'),
            aws_secret_access_key=os.environ.get('aws_secret_access_key'),
            region_name=os.environ.get('region_name')
        )
        self.attributes = OrderedDict([
            ('lowe', ['COLOUR0', 'Low', 'AREA', 0]),
            ('medi', ['COLOUR6', 'Medium', 'STACK', 0]),
            ('warm', ['COLOUR2', 'Warm', 'STACK', 0]),
            ('high', ['COLOUR7', 'High', 'STACK', 0]),
        ])

    def _get_ec2_instance_id(self):
        url = 'http://169.254.169.254/latest/meta-data/instance-id'
        response = requests.get(url)
        response.raise_for_status()
        return response.text

    def _get_instance(self):
        if self.typemon == 'rds':
            return os.environ.get('database')
        elif self.typemon == 'ec2':
            return self._get_ec2_instance_id()
        else:
            raise ValueError("Invalid typemon value")

    def _set_dimensions(self):
        instance = self._get_instance()
        if self.typemon == 'rds':
            return {
                'Namespace': 'AWS/RDS',
                'Dimensions': [{'Name': 'DBInstanceIdentifier', 'Value': instance}]
            }
        elif self.typemon == 'ec2':
            return {
                'Namespace': 'AWS/EC2',
                'Dimensions': [{'Name': 'InstanceId', 'Value': instance}]
            }
        else:
            raise ValueError("Invalid typemon value")

    def _get_stack(self, value):
        self.attributes['lowe'][3] = min(value, 25)
        self.attributes['medi'][3] = max(min(value - 25, 25), 0)
        self.attributes['warm'][3] = max(min(value - 50, 25), 0)
        self.attributes['high'][3] = max(min(value - 75, 25), 0)
        return "\n".join("{key}.value {value}".format(key=key, value=attr[3]) for key, attr in self.attributes.items())

    def print_value(self):
        dimensions = self._set_dimensions()
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=5)
        response = self.cloudwatch.get_metric_statistics(
            Namespace=dimensions['Namespace'],
            MetricName='CPUUtilization',
            Dimensions=dimensions['Dimensions'],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=['Average'],
            Unit='Percent'
        )
        if not response['Datapoints']:
            raise ValueError("No data points found")
        value = round(response['Datapoints'][0]['Average'])
        return self._get_stack(value)

    def print_conf(self):
        if self.typemon == 'rds':
            title = 'RDS'
            category = 'mysql2'
        elif self.typemon == 'ec2':
            title = 'EC2'
            category = 'system'
        else:
            raise ValueError("Invalid typemon value")

        config = (
            "graph_title {title} CPUutilization\n"
            "graph_args --base 1000 -r --lower-limit 0 --upper-limit 100\n"
            "graph_vlabel % of CPU utilization\n"
            "graph_order lowe medi warm high\n"
            "graph_category {category}\n"
        ).format(title=title, category=category)
        for key, attr in self.attributes.items():
            config += (
                "{key}.colour {colour}\n"
                "{key}.label {label}\n"
                "{key}.draw {draw}\n"
                "{key}.type GAUGE\n"
                "{key}.min 0\n"
            ).format(key=key, colour=attr[0], label=attr[1], draw=attr[2])
        return config

def main():
    script_name = sys.argv[0].split("-")
    if len(script_name) < 2 or script_name[1] not in ['rds', 'ec2']:
        sys.exit("Invalid script name format")

    typemon = script_name[1]
    monitor = Monitor(typemon)

    if len(sys.argv) < 2:
        print(monitor.print_value())
    elif sys.argv[1] == "config":
        print(monitor.print_conf())
    else:
        print("Wrong Args")

if __name__ == '__main__':
    main()