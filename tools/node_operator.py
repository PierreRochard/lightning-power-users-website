from collections import defaultdict
from pprint import pformat
from typing import Dict

from google.protobuf.json_format import MessageToDict
# noinspection PyProtectedMember
from grpc._channel import _Rendezvous

from lnd_grpc import lnd_grpc
from lnd_grpc.protos.rpc_pb2 import OpenStatusUpdate
from website.logger import log
from tools.channel import Channel
from tools.google_sheet import get_google_sheet_data
from tools.node import Node


class MyDefaultDict(defaultdict):

    def __init__(self, rpc, node, **kwargs):
        super().__init__(node, **kwargs)
        self.rpc = rpc

    def __missing__(self, key):
        self[key] = new = self.default_factory(self.rpc, key)
        return new


class NodeOperator(object):
    nodes: Dict[str, Node]

    def __init__(self,
                 lnd_dir: str = None,
                 lnd_network: str = 'mainnet',
                 lnd_grpc_host: str = '127.0.0.1',
                 lnd_grpc_port: str = '10009',
                 macaroon_path: str = None,
                 tls_cert_path: str = None):

        self.rpc = lnd_grpc.Client(
            lnd_dir=lnd_dir,
            network=lnd_network,
            grpc_host=lnd_grpc_host,
            grpc_port=lnd_grpc_port,
            macaroon_path=macaroon_path,
            tls_cert_path=tls_cert_path
        )
        self.nodes = MyDefaultDict(self.rpc, Node)
        self.get_channels()
        self.get_peers()

    def get_channels(self):
        log.info('Getting channels')
        channels = self.rpc.list_channels()
        [self.nodes[m.remote_pubkey].add_channel(Channel(self.rpc,
                                                         **MessageToDict(m)))
         for m in channels]

        pending_channels = [c for c in self.rpc.list_pending_channels()]
        [self.nodes[m.remote_node_pub].add_channel(Channel(self.rpc,
                                                           **m))
         for m in pending_channels]

        closed_channels = [c for c in self.rpc.closed_channels()]
        [self.nodes[m.remote_pubkey].add_channel(Channel(self.rpc,
                                                         **MessageToDict(m)))
         for m in closed_channels]

        log.debug(
            'Got channels',
            open_channels=len(channels),
            pending_channels=len(pending_channels),
            closed_channels=len(closed_channels)
        )

    def get_peers(self):
        peers = self.rpc.list_peers()
        log.debug(
            'Got peers',
            peers=len(peers)
        )
        for peer in peers:
            data = MessageToDict(peer)
            node = self.nodes[data['pub_key']]
            node.peer_info = data

    def reconnect_all(self):
        for node in self.nodes.values():
            node.reconnect()

    def close_channels(self, ip_address: str):
        for node in self.nodes.values():
            ip_addresses = []
            if node.info is None:
                continue
            for address in node.info['node'].get('addresses', []):
                ip_addresses.append(address['addr'])
                if ip_address in address['addr']:
                    for channel in node.channels:
                        force = not channel.is_active
                        txid = self.rpc.close_channel(
                            channel_point=channel.channel_point,
                            force=force,
                            sat_per_byte=1
                            )
                        print(pformat(MessageToDict(txid)))
            print(node.pubkey, ip_addresses)
        print(len(self.nodes.values()))

    def identify_dupes(self):
        for pubkey in self.nodes:
            node = self.nodes[pubkey]
            if len(node.channels) < 3:
                continue
            print(node)


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
        help='The IP address of the peer that you want to force close channels on'
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

    node_operator = NodeOperator(
        lnd_grpc_host=args.host,
        lnd_grpc_port=args.port,
        macaroon_path=args.macaroon,
        tls_cert_path=args.tls
    )

    if args.action == 'close' and args.ip_address:
        node_operator.close_channels(ip_address=args.ip_address)

    elif args.action == 'reconnect':
        node_operator.reconnect_all()

    elif args.action == 'sheet':
        get_google_sheet_data(node_operator)

    elif args.action == 'open':
        response = lnd_remote_client.open_channel(
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
        node_operator.identify_dupes()

