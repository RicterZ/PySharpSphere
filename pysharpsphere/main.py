import argparse

from pysharpsphere.lib.sharp_sphere import SharpSphere, print_vm


def list_wrap(args):
    ss = SharpSphere(args)
    print_vm(ss.list_vm())


def execute_wrap(args):
    ss = SharpSphere(args)

    ss.execute_vm(ip_address=args.ip_address, username=args.guest_user,
                  password=args.guest_pass, command=args.command)


def upload_wrap(args):
    ss = SharpSphere(args)
    ss.upload_file(ip_address=args.ip_address, username=args.guest_user,
                   password=args.password, src=args.source_file,
                   dest=args.dest_path)


def dump_wrap(args):
    ss = SharpSphere(args)
    ss.dump_vm(ip_address=args.ip_address)


def main():

    parser = argparse.ArgumentParser(prog='pySharpSphere')
    parser.add_argument('-H', '--host', action='store', dest='host', help='vCenter Server host')
    parser.add_argument('-P', '--port', action='store', dest='port', type=int, default=443,
                        help='vCenter Server port')
    parser.add_argument('-u', '--username', action='store', dest='user', help='vCenter Server username')
    parser.add_argument('-p', '--password', action='store', dest='password', help='vCenter Server password')

    sub_parsers = parser.add_subparsers(help='sub-command')

    # list command
    sub_parsers.add_parser('list', help='list virtual machines').set_defaults(func=list_wrap)

    # execute command
    sp = sub_parsers.add_parser('execute', help='execute command on target machine')
    sp.add_argument('-t', '--ip-address', action='store', dest='ip_address', required=True,
                    help='IP address of target machine')
    sp.add_argument('--guest-user', action='store', dest='guest_user', required=True,
                    help='guest OS username')
    sp.add_argument('--guest-pass', action='store', dest='guest_pass', required=True,
                    help='guest OS password')
    sp.add_argument('-c', '--command', action='store', dest='command', required=True,
                    help='command to execute')
    sp.set_defaults(func=execute_wrap)

    # upload command
    sp = sub_parsers.add_parser('upload', help='upload file to target machine')
    sp.add_argument('-t', '--ip-address', action='store', dest='ip_address', required=True,
                    help='IP address of target machine')
    sp.add_argument('--guest-user', action='store', dest='guest_user', required=True,
                    help='guest OS username')
    sp.add_argument('--guest-pass', action='store', dest='guest_pass', required=True,
                    help='guest OS password')
    sp.add_argument('--source', action='store', dest='source_file', required=True,
                    help='source file path to upload')
    sp.add_argument('--dest', action='store', dest='dest_path', required=True,
                    help='dest file path on target machine')
    sp.set_defaults(func=upload_wrap)

    # dump command
    sp = sub_parsers.add_parser('dump', help='dump memory of target machine')
    sp.add_argument('-t', '--ip-address', action='store', dest='ip_address', required=True,
                    help='IP address of target machine')
    sp.set_defaults(func=dump_wrap)

    # default fallback
    parser.set_defaults(func=lambda s: parser.print_help())

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()