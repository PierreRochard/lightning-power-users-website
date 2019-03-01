from collections import defaultdict
from datetime import datetime
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

    def close_channels_by_host(self, ip_address: str):
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
                        log.info(pformat(MessageToDict(txid)))
            log.info(node.pubkey, ip_addresses)
        log.info(len(self.nodes.values()))

    def close_channels(self):
        dormant_channels = []
        exclude_closed_and_pending = 0
        exclude_no_local = 0
        exclude_remote_skin_in_the_game = 0
        log.info('Closing channels')
        for node in self.nodes.values():
            for channel in node.channels:
                if channel.data.get('closing_txid') or channel.data.get('close_height') or channel.is_pending:
                    exclude_closed_and_pending += 1
                    continue
                if channel.local_balance == 0:
                    exclude_no_local += 1
                    continue
                if channel.remote_balance > 0:
                    exclude_remote_skin_in_the_game += 1
                    continue
                last_update = datetime.fromtimestamp(channel.info['last_update'])
                today = datetime.now()
                days_since_last_update = (today - last_update).days
                if days_since_last_update < 7:
                    continue
                log.info('Dormant channel', channel_data=channel.data)
                force = not channel.is_active
                channel_close_updates = self.rpc.close_channel(
                    channel_point=channel.channel_point,
                    force=force,
                    sat_per_byte=1
                )
                for channel_close_update in channel_close_updates:
                    log.info('channel_close_update',
                             channel_close_update=MessageToDict(channel_close_update)
                             )
                    break
                dormant_channels.append(channel)
        dormant_capacity = sum([c.local_balance for c in dormant_channels])

        log.info('Dormant capacity', dormant_capacity=dormant_capacity,
                 dormant_channels=len(dormant_channels))

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

    node_operator = NodeOperator(
        lnd_grpc_host=args.host,
        lnd_grpc_port=args.port,
        macaroon_path=args.macaroon,
        tls_cert_path=args.tls
    )

    if args.action == 'close' and args.ip_address:
        node_operator.close_channels_by_host(ip_address=args.ip_address)

    elif args.action == 'reconnect':
        node_operator.reconnect_all()

    elif args.action == 'sheet':
        get_google_sheet_data(node_operator)

    elif args.action == 'open':
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
        node_operator.identify_dupes()

    elif args.action == 'close' and not args.ip_address:
        node_operator.close_channels()
