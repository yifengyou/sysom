# -*- coding: utf-8 -*-
import os
import sys
from datetime import datetime
import json
import traceback
import socket

nfs_ip = '127.0.0.1'
nfs_dir = '/usr/vmcore-nfs'
if len(sys.argv) == 3 :
    nfs_ip = sys.argv[1]
    nfs_dir = sys.argv[2]

def get_crash_path():
    try:
        if os.path.exists('/etc/kdump.conf'):
            with open('/etc/kdump.conf', 'r') as f1:
                lines = f1.readlines()
                part = ''
                var_path = ''
                for line in lines:
                    if line.startswith('ext4'):
                        if len(line.split()) > 1:
                            part0 = line.split()[1]
                        else:
                            continue
                        if part0.startswith('/dev/'):
                            cmd = 'lsblk %s' % (part0)
                            output = os.popen(cmd)
                            ret = output.read().strip()
                            output.close()
                            part = ret.splitlines()[-1].split()[-1]
                        elif part0.startswith('LABEL='):
                            part = part0.split('=')[-1]
                    elif line.startswith('path'):
                        var_path = line.split()[-1]
            if len(part) > 0 and len(var_path) > 0:
                return "%s%s" % (part, var_path)
            elif len(var_path) > 0:
                return var_path
        else:
            return '/var/crash/'
    except:
        pass
    return '/var/crash/'

def unmount_nfs():
    cmd = 'umount /tmp/vmcore-nfs'
    ret = os.system(cmd)
    if ret != 0:
        raise Exception('failed to unmount nfs at /tmp/vmcore-nfs')

def upload_nfs(vmcore_dir):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
    finally:
        s.close()
    timelist = vmcore_dir.split('-')[1:]
    core_time = ''.join(timelist)
    core_time = core_time.replace(':','')
    vmcore_name ='%s_%s'%(core_time,ip)

    if os.path.exists("/tmp/vmcore-nfs") == False:
        cmd = 'mkdir -p /tmp/vmcore-nfs'
        ret = os.system(cmd)
        if ret != 0:
            raise Exception('failed to make nfs mount point at /tmp/vmcore-nfs')

    cmd = 'mount -t nfs %s:%s /tmp/vmcore-nfs' % (nfs_ip,nfs_dir)
    ret = os.system(cmd)
    if ret != 0:
        raise Exception('failed to mount to nfs %s' % vmcore_dir)

    if os.path.exists("/tmp/vmcore-nfs/%s" % vmcore_name) == False:
        cmd = 'mkdir /tmp/vmcore-nfs/%s' % vmcore_name
        ret = os.system(cmd)
        if ret != 0:
            unmount_nfs()
            raise Exception('failed to make dir at mount point (/tmp/vmcore-nfs/%s)' % vmcore_name)

    cmd = 'cp %s/vmcore-dmesg.txt /tmp/vmcore-nfs/%s/vmcore-dmesg.txt' % (vmcore_dir,vmcore_name)
    ret = os.system(cmd)
    if ret != 0:
        unmount_nfs()
        raise Exception('failed to copy to nfs /tmp/vmcore-nfs/%s/vmcore-dmesg.txt' % vmcore_name)

    cmd = 'cp %s/vmcore /tmp/vmcore-nfs/%s/vmcore' % (vmcore_dir,vmcore_name)
    ret = os.system(cmd)
    if ret != 0:
        unmount_nfs()
        raise Exception('failed to copy to nfs /tmp/vmcore-nfs/%s/vmcore' % vmcore_name)

    unmount_nfs()
    with open('%s/.upload' % vmcore_dir,'w') as f:
        pass

def main():
    crash_path = get_crash_path()
    dirs_list = []
    files = os.listdir(crash_path)
    files_path = [f'{crash_path}/{file}' for file in files]
    for file in files_path:
        if os.path.isfile(file):
            continue
        if file.find('-') < 0:
            continue
        dirs_list.append(file)
    dirs_list.sort(key=lambda fp: os.path.getmtime(fp),reverse=True)
    for dir in dirs_list:
        tmp = '%s/.upload' % dir
        if os.path.exists(tmp):
            break
        upload_nfs(dir)

if __name__=="__main__":
    main()

