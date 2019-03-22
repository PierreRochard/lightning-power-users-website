from website.constants import keyring


def set_password(service):
    new_password = input(f'New password for {service}')

    keyring.set_password(
        service=service,
        username=service,
        password=new_password
    )
    print('New password set!')


def get_password(service: str):
    password = keyring.get_password(
        service=service,
        username=service,
    )
    print(password)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='LND Node Operator Tools'
    )

    parser.add_argument(
        'action',
        type=str
    )
    parser.add_argument(
        '--service',
        '-s',
        type=str,
        help='Service name',
        required=True
    )

    args = parser.parse_args()

    if args.action == 'set':
        set_password(args.service)
    elif args.action == 'get':
        get_password(args.service)
