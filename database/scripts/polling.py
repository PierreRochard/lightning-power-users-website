
if __name__ == '__main__':
    import time

    from database.scripts.upsert_forwarding_events import UpsertForwardingEvents
    from database.scripts.upsert_open_channels import UpsertOpenChannels

    import argparse

    parser = argparse.ArgumentParser(
        description='LND Node Operator Tools'
    )

    parser.add_argument(
        '--macaroon',
        '-m',
        type=str
    )

    parser.add_argument(
        '--tls',
        '-t',
        type=str
    )

    args = parser.parse_args()

    while True:
        UpsertOpenChannels(tls_cert_path=args.tls,
                           macaroon_path=args.macaroon)

        UpsertForwardingEvents(tls_cert_path=args.tls,
                               macaroon_path=args.macaroon)

        time.sleep(60)
