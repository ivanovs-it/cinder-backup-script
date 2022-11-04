#!/usr/bin/python3

import os
from os import environ as env
import sys
import time
from datetime import datetime
from keystoneauth1.identity import v3
from keystoneauth1 import session
from cinderclient import client as cinderclient
from novaclient import client as novaclient
from keystoneclient import client as keystoneclient
import logging

# Set variables
project_name = sys.argv[2]
vm_name = sys.argv[3]
retention = int (sys.argv[4])
sleep_timer = 60
project_id = ""

# Openstack variables
OS_AUTH_URL = "http://localhost:5000/v3"
OS_USERNAME = "admin"
OS_PASSWORD = "password"
OS_PROJECT_NAME = "admin"
OS_USER_DOMAIN_ID = "Default"
OS_PROJECT_DOMAIN_ID = "Default"
OS_REGION_NAME = sys.argv[1]

logging.basicConfig(stream=sys.stdout, level=logging.INFO,format="%(asctime)s [%(process)d] %(message)s")
logging.log(level=20,msg="Starting backup creation for Openstack PROD "+OS_REGION_NAME+", project \'"+project_name+"\', vm \'"+vm_name+"\'.")

# Openstack authorization
auth = v3.Password(auth_url=OS_AUTH_URL, username=OS_USERNAME,
                     password=OS_PASSWORD, project_name=OS_PROJECT_NAME,
                     user_domain_id=OS_USER_DOMAIN_ID, project_domain_id=OS_PROJECT_DOMAIN_ID)
sess = session.Session(auth=auth)
keystone = keystoneclient.Client(3, session=sess)
nova = novaclient.Client(2, session=sess, region_name=OS_REGION_NAME)
cinder = cinderclient.Client(3, session=sess, region_name=OS_REGION_NAME)

# Get project id
try:
  projects = keystone.projects.list()
  for project in projects:
    if project.name == project_name:
      project_id = project.id
  # Check that project id is not null
  if project_id == "":
    logging.log(level=20,msg="Failed to get project id for project called \'"+project_name+"\'. Please check project name")
    sys.exit(2)
  else:
    logging.log(level=20,msg="ID for project \'"+project_name+"\' is "+project_id)
except Exception as err:
  logging.log(level=20,msg="Error occured while getting project list from keystone. Error: \""+str(err)+"\"")
  raise

# Get VM id
search_opts={ 'all_tenants': 'True', 'project_id': project_id, 'name': vm_name}
try:
  vm = nova.servers.list(search_opts=search_opts)[0]
except Exception as err:
  logging.log(level=20,msg="Error occured while getting server from nova. Error: \""+str(err)+"\"")
  raise

# Get volume id
try:
  volume_id = nova.volumes.get_server_volumes(vm.id)[0].id
except Exception as err:
  logging.log(level=20,msg="Error occured while getting attached volume from nova. Error: \""+str(err)+"\"")
  raise

# Get backup list
search_opts = { 'volume_id': volume_id }
try:
  backup_list = cinder.backups.list(search_opts=search_opts)
  backup_list_ids = []
  for backup in backup_list:
     backup_list_ids.append(backup.id)
  logging.log(level=20,msg="The following backups were found for volume "+volume_id+": "+" ".join(backup_list_ids))
except Exception as err:
  logging.log(level=20,msg="Error occured while getting backup list from cinder. Error: \""+str(err)+"\"")
  raise

# Create new backup
try:
  logging.log(level=20,msg="Creating new backup for volume "+volume_id)
  cinder.backups.create (volume_id, force=True)
except Exception as err:
  logging.log(level=20,msg="Failed to create backup. Error: \""+str(err)+"\"")
  raise

# Check cinder backup creation progress
search_opts = { 'volume_id': volume_id, 'status': "creating"}
backup_id = cinder.backups.list(search_opts=search_opts)[0].id
backup_object = cinder.backups.get(backup_id)
while backup_object.status == 'creating':
  logging.log(level=20,msg="Backup "+backup_id+" is currently in \'"+backup_object.status+"\' status. Sleeping for "+str(sleep_timer)+" seconds.")
  time.sleep(sleep_timer)
  backup_object = cinder.backups.get(backup_id)
logging.log(level=20,msg="Backup "+backup_id+" switched from \'creating\' status to \'"+backup_object.status+" status")

#Check that backup is available after creation
if cinder.backups.get(backup_id).status != "available":
  logging.log(level=20,msg="Something went wrong. Backup "+backup_id+" status is not \'available\'")
  sys.exit(2)

# Find obsolete backups and delete
# This will delete all obsolete backups, if retention policy is changed
count_backups = 0
for backup in backup_list:
  count_backups += 1
  if (count_backups >= retention):
    try:
      logging.log(level=20,msg="Deleting backup id "+backup.id+" due to retention rules: "+str(retention)+" backup(s)")
      cinder.backups.delete (backup.id)
      logging.log(level=20,msg="Backup id "+backup.id+" has been successfully deleted")
    except Exception as err:
      logging.log(level=20,msg=" Failed to detele backup."+str(err))
      raise

logging.log(level=20,msg="Backup creation script finished successfully.")
