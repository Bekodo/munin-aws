# munin-aws
## Munin AWS CPUutulization plugin
In your /etc/munin/plugin-conf/munin-node
```
[aws-*]
env.aws_access_key_id [KEY_ID]
env.aws_secret_access_key [ACCESS_KEY]
env.region_name [REGION]
env.database [RDSINSTANCE]
```
For munin EC2:
```
ln -s /usr/share/munin/plugins/aws-_-CPUutilization.py aws-ec2-CPUutilization
```
For munin RDS:
```
ln -s /usr/share/munin/plugins/aws-_-CPUutilization.py aws-ec2-CPUutilization
```
