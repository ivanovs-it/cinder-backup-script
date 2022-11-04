### Backup creation script using cinder-backup API

#### Prerequisites
Change credentials for Openstack user

```bash
OS_AUTH_URL = "http://localhost:5000/v3"
OS_USERNAME = ""
OS_PASSWORD = ""
OS_PROJECT_NAME = "admin"
OS_USER_DOMAIN_ID = "Default"
OS_PROJECT_DOMAIN_ID = "Default"
```
#### Example
```bash
python3 cinder-backup.py RegionOne admin testvm01 10
```
Arguments:
1. Region name (RegionOne)
2. project name (admin)
3. VM name (testvm01)
4. Retention, number of active backups (10)
