import atexit
import ssl

try:
    from pyvim.connect import SmartConnect, Disconnect, VimSessionOrientedStub
except ImportError:
    from pyVim.connect import SmartConnect, Disconnect, VimSessionOrientedStub


def connect(args):
    ssl._create_default_https_context = ssl._create_unverified_context

    try:
        if args.user and args.password:
            service_instance = SmartConnect(host=args.host,
                                            user=args.user,
                                            pwd=args.password,
                                            port=args.port,
                                            disableSslCertValidation=True)
        else:
            raise Exception('invalid arguments')

        atexit.register(Disconnect, service_instance)
    except Exception as e:
        print('[-] Error: {}'.format(e))
        raise e

    if not service_instance:
        raise SystemExit("[-] Unable to connect to host with supplied credentials.")

    return service_instance
