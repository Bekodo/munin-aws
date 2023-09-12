#!/usr/bin/python3.7

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

class Monitor(object):
    difhourmin = 120
    cloudwatch = []
    dimension = []
    typemon = ""
    attributes = OrderedDict([
        ('lowe',['COLOUR0','Low','AREA',0]),
        ('medi',['COLOUR6','Medium','STACK',0]),
        ('warm',['COLOUR2','Warm','STACK',0]),
        ('high',['COLOUR7','High','STACK',0]),
        ])

    def __init__(self,typemon):
        self.typemon = typemon
        self.cloudwatch = boto3.client('cloudwatch',
            aws_access_key_id = os.environ.get('aws_access_key_id'),
            aws_secret_access_key = os.environ.get('aws_secret_access_key'),
            region_name = os.environ.get('region_name')
        )

    def _getEc2InstanceID(self):
        url = 'http://169.254.169.254/latest/meta-data/instance-id'
        content = requests.get(url)
        return content.text

    def _getInstance(self):
        typemon = self.typemon
        if typemon == 'rds':
            return os.environ.get('database')
        elif typemon == 'ec2':
            return self._getEc2InstanceID()

    def _setDimensions(self):
        typemon = self.typemon
        instance = self._getInstance()
        dimension = {
            'Namespace' : '',
            'Dimensions' : [
                {
                    'Name': '',
                    'Value': ''
                },
            ],
        }
        if typemon == 'rds':
            dimension['Namespace'] = 'AWS/RDS'
            dimension['Dimensions'][0]['Name'] = 'DBInstanceIdentifier'
            dimension['Dimensions'][0]['Value'] = instance
        elif typemon == 'ec2':
            dimension['Namespace'] = 'AWS/EC2'
            dimension['Dimensions'][0]['Name'] = 'InstanceId'
            dimension['Dimensions'][0]['Value'] = instance
        else:
            dimension = []
        return dimension

    def _getStack(self,value):
        values = ""
        attributes = self.attributes
        attributes['lowe'][3] = min(value, 25)
        attributes['medi'][3] = max(min(value - 25, 25), 0)
        attributes['warm'][3] = max(min(value - 50, 25), 0)
        attributes['high'][3] = max(min(value - 75, 25), 0)
        for element in attributes:
            values += element + ".value " + str(attributes[element][3]) + "\n"
        return values[:-1]

    def printValue(self):
        dimension = self._setDimensions()
        response = self.cloudwatch.get_metric_statistics(
            Namespace = dimension['Namespace'],
            MetricName = 'CPUUtilization',
            Dimensions = [
                {
                    'Name': dimension['Dimensions'][0]['Name'],
                    'Value': dimension['Dimensions'][0]['Value']
                },
            ],
            StartTime = datetime.now() - timedelta(minutes = (self.difhourmin + 10)),
            EndTime = datetime.now() - timedelta(minutes = (self.difhourmin + 5)),
            Period = 300,
            Statistics = ['Average'],
            Unit = 'Percent'
        )
        value = round(response['Datapoints'][0]['Average'])
        return self._getStack(value)

    def printConf(self):
        typemon = self.typemon
        attributes = self.attributes
        if typemon == 'rds':
            title = 'RDS'
            category = 'mysql2'
        elif typemon == 'ec2':
            title = 'EC2'
            category = 'system'
        config = "graph_title " + title + " CPUutilization\n"\
        "graph_args --base 1000 -r --lower-limit 0 --upper-limit 100\n"\
        "graph_vlabel % of CPU utilization\n"\
        "graph_order lowe medi warm high\n"\
        "graph_category " + category + "\n"
        for item in attributes:
            config += item+".colour " + attributes[item][0] + "\n"
            config += item+".label " + attributes[item][1] + "\n"
            config += item+".draw " + attributes[item][2] + "\n"
            config += item+".type " + "GAUGE" + "\n"
            config += item+".min " + "0" + "\n"
        return config[:-1]

if __name__ == '__main__':
    script_name = sys.argv[0].split("-")
    if script_name[1] == 'rds' or script_name[1] == 'ec2':
        typemon = script_name[1]
    else:
        sys.exit()

    ClodWatch = Monitor(typemon)
    if len(sys.argv) < 2:
        print(ClodWatch.printValue())
    elif sys.argv[1] == "config":
        print(ClodWatch.printConf())
    else:
        print("Wrong Args")
