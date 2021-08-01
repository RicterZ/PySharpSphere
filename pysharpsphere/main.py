import argparse
import urllib3

from pysharpsphere.lib.sharp_sphere import SharpSphere, print_vm


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def list_wrap(args):
    ss = SharpSphere(args)
    print_vm(ss.list_vm())


def execute_wrap(args):
    ss = SharpSphere(args)
    use_ntlm = False

    if args.guest_ntlm:
        password = args.guest_ntlm
        use_ntlm = True

    elif args.guest_pass:
        password = args.guest_pass
    else:
        print('[-] No guest credentials provided')
        raise SystemExit

    ss.execute_vm(mo_id=args.mo_id, username=args.guest_user,
                  password=password, command=args.command,
                  print_output=not args.no_output,
                  use_ntlm=use_ntlm)


def upload_wrap(args):
    ss = SharpSphere(args)
    use_ntlm = False

    if args.guest_ntlm:
        password = args.guest_ntlm
        use_ntlm = True
    elif args.guest_pass:
        password = args.guest_pass
    else:
        print('[-] No guest credentials provided')
        raise SystemExit

    ss.upload_file(mo_id=args.mo_id, username=args.guest_user,
                   password=password, src=args.source_file,
                   dest=args.dest_path, use_ntlm=use_ntlm)


def dump_wrap(args):
    ss = SharpSphere(args)
    ss.dump_vm(mo_id=args.mo_id)


def main():

    parser = argparse.ArgumentParser(prog='pySharpSphere')
    parser.add_argument('-H', '--host', action='store', dest='host', help='vCenter Server host')
    parser.add_argument('-P', '--port', action='store', dest='port', type=int, default=443,
                        help='vCenter Server port')
    parser.add_argument('-u', '--username', action='store', dest='user', help='vCenter Server username')
    parser.add_argument('-p', '--password', action='store', dest='password', help='vCenter Server password')

    sub_parsers = parser.add_subparsers(help='sub-commands')

    # list command
    sub_parsers.add_parser('list', help='list virtual machines').set_defaults(func=list_wrap)

    # execute command
    sp = sub_parsers.add_parser('execute', help='execute command on target machine')
    sp.add_argument('-t', '--moID', action='store', dest='mo_id', required=True,
                    help='IP address of target machine')
    sp.add_argument('--guest-user', action='store', dest='guest_user', required=True,
                    help='guest OS username')
    sp.add_argument('--guest-pass', action='store', dest='guest_pass', required=False,
                    help='guest OS password')
    sp.add_argument('--guest-ntlm', action='store', dest='guest_ntlm', required=False,
                    help='guest OS NTLM token')
    sp.add_argument('-c', '--command', action='store', dest='command', required=True,
                    help='command to execute')
    sp.add_argument('--no-output', action='store_true', default=False,
                    help='do not show the command output')
    sp.set_defaults(func=execute_wrap)

    # upload command
    sp = sub_parsers.add_parser('upload', help='upload file to target machine')
    sp.add_argument('-t', '--moID', action='store', dest='mo_id', required=True,
                    help='IP address of target machine')
    sp.add_argument('--guest-user', action='store', dest='guest_user', required=True,
                    help='guest OS username')
    sp.add_argument('--guest-pass', action='store', dest='guest_pass', required=False,
                    help='guest OS password')
    sp.add_argument('--guest-ntlm', action='store', dest='guest_ntlm', required=False,
                    help='guest OS NTLM token')
    sp.add_argument('--source', action='store', dest='source_file', required=True,
                    help='source file path to upload')
    sp.add_argument('--dest', action='store', dest='dest_path', required=True,
                    help='dest file path on target machine')
    sp.set_defaults(func=upload_wrap)

    # dump command
    sp = sub_parsers.add_parser('dump', help='dump memory of target machine')
    sp.add_argument('-t', '--moID', action='store', dest='mo_id', required=True,
                    help='IP address of target machine')
    sp.set_defaults(func=dump_wrap)

    # default fallback
    parser.set_defaults(func=lambda s: parser.print_help())

    args = parser.parse_args()

    try:
        args.func(args)
    except Exception as e:
        if 'pyVmomi' in str(e.__class__):
            error = e.msg
        else:
            error = str(e)

        print('[-] Error: {}'.format(error))


if __name__ == '__main__':
    main()
