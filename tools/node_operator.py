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
    def __missing__(self, key):
        self[key] = new = self.default_factory(key)
        return new


class NodeOperator(object):
    nodes: Dict[str, Node]

    def __init__(self):
        self.nodes = MyDefaultDict(Node)
        self.get_channels()
        self.get_peers()
        self.lnd_client = lnd_grpc.Client()

    def get_channels(self):
        channels = self.lnd_client.list_channels()
        [self.nodes[m.remote_pubkey].add_channel(Channel(**MessageToDict(m)))
         for m in channels]

        pending_channels = [c for c in self.lnd_client.pending_channels()]
        [self.nodes[m.remote_node_pub].add_channel(Channel(**m))
         for m in pending_channels]

        closed_channels = [c for c in self.lnd_client.closed_channels()]
        [self.nodes[m.remote_pubkey].add_channel(Channel(**MessageToDict((m))))
         for m in closed_channels]

        log.debug(
            'Got channels',
            open_channels=len(channels),
            pending_channels=len(pending_channels),
            closed_channels=len(closed_channels)
        )

    def get_peers(self):
        peers = self.lnd_client.list_peers()
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
                        txid = self.lnd_client.close_channel(
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
        type=str
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

    args = parser.parse_args()

    node_operator = NodeOperator()

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

