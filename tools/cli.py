import time

from google.protobuf.json_format import MessageToDict
# noinspection PyProtectedMember
from grpc._channel import _Rendezvous

from lnd_grpc import lnd_grpc
from lnd_grpc.protos.rpc_pb2 import OpenStatusUpdate
from tools.node_operator import NodeOperator
from tools.policy import SetPolicy
from website.logger import log

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='LND Node Operator Tools'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Display additional information for debugging'
    )

    parser.add_argument(
        'action',
        type=str
    )

    parser.add_argument(
        '--ip_address',
        '-i',
        type=str,
        help='The IP address of the peer that you want to force close channels on',
        default=None
    )

    parser.add_argument(
        '--pubkey',
        '-p',
        type=str
    )

    parser.add_argument(
        '--size',
        '-s',
        type=int
    )

    parser.add_argument(
        '--fee',
        '-f',
        type=int
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

    parser.add_argument(
        '--port',
        type=str,
        help='Port for gRPC',
        default='10009'
    )

    parser.add_argument(
        '--host',
        type=str,
        help='Host IP address for gRPC',
        default='127.0.0.1'
    )

    args = parser.parse_args()

    if args.action == 'close' and args.ip_address:
        node_operator = NodeOperator(
            lnd_grpc_host=args.host,
            lnd_grpc_port=args.port,
            macaroon_path=args.macaroon,
            tls_cert_path=args.tls
        )
        node_operator.close_channels_by_host(ip_address=args.ip_address)

    elif args.action == 'reconnect':
        node_operator = NodeOperator(
            lnd_grpc_host=args.host,
            lnd_grpc_port=args.port,
            macaroon_path=args.macaroon,
            tls_cert_path=args.tls
        )
        node_operator.reconnect_all()

    elif args.action == 'open':
        node_operator = NodeOperator(
            lnd_grpc_host=args.host,
            lnd_grpc_port=args.port,
            macaroon_path=args.macaroon,
            tls_cert_path=args.tls
        )
        response = node_operator.rpc.open_channel(
            node_pubkey_string=args.pubkey,
            local_funding_amount=args.size,
            push_sat=0,
            sat_per_byte=args.fee,
            spend_unconfirmed=True
        )
        try:
            for update in response:
                log.info(str(type(update)), **MessageToDict(update))
                if isinstance(update, OpenStatusUpdate):
                    break
        except _Rendezvous as e:
            log.error(
                'open_channel',
                exc_info=True
            )

    elif args.action == 'dupes':
        node_operator = NodeOperator(
            lnd_grpc_host=args.host,
            lnd_grpc_port=args.port,
            macaroon_path=args.macaroon,
            tls_cert_path=args.tls
        )
        node_operator.identify_dupes()

    elif args.action == 'close' and not args.ip_address:
        node_operator = NodeOperator(
            lnd_grpc_host=args.host,
            lnd_grpc_port=args.port,
            macaroon_path=args.macaroon,
            tls_cert_path=args.tls
        )
        node_operator.close_channels()

    elif args.action == 'policy':
        rpc = lnd_grpc.Client(
            grpc_host=args.host,
            grpc_port=args.port,
            macaroon_path=args.macaroon,
            tls_cert_path=args.tls
        )
        while True:
            SetPolicy().set_policy(rpc)
            time.sleep(1*60*60)
