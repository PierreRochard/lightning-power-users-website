import csv
import time
from typing import List

from google.protobuf.json_format import MessageToDict
import networkx as nx
# noinspection PyProtectedMember
from grpc._channel import _Rendezvous

from lnd_grpc.protos.rpc_pb2 import ChannelGraph, OpenStatusUpdate
from website.logger import log


def convert_to_dict(data):
    data = [MessageToDict(d) for d in data]
    return data


def save_to_csv(name: str, data: List[dict]):
    timestamp = time.time()
    with open(f'{name}-{timestamp}.csv', 'w') as f:
        w = csv.DictWriter(f, data[0].keys())
        w.writeheader()
        for d in data:
            w.writerow(d)


class LightningGraph(object):
    def __init__(self, local_pubkey: str, node_operator):
        self.node_operator = node_operator
        self.local_pubkey = local_pubkey
        self.rpc = self.node_operator.rpc
        self.graph: ChannelGraph = self.rpc.describe_graph()
        self.nodes = convert_to_dict(self.graph.nodes)
        self.edges = convert_to_dict(self.graph.edges)

    def to_csv(self):
        save_to_csv(name='nodes', data=self.nodes)
        save_to_csv(name='edges', data=self.edges)

    def open_channels(self, name: str, data, top: int = 10):
        list_data = [dict(pub_key=pub_key, score=score) for pub_key, score in
                     data.items()]
        list_data.sort(key=lambda x: x['score'], reverse=True)
        log.info(name, lpu_rank=[i for i, p in enumerate(list_data) if
                                 p['pub_key'] == self.local_pubkey][0])

        for page in list_data[0:top]:
            log.debug(f'Processing {name} result', **page)
            node = self.node_operator.nodes[page['pub_key']]
            if not node.peer_info:
                connected = node.reconnect()
                if not connected:
                    log.error(f'Aborting {name} processing, unable to connect')
                    continue
            if len(node.channels) > 1:
                log.error(
                    f'Aborting {name} processing, already have channels',
                    local_balance=node.local_balance,
                    remote_balance=node.remote_balance,
                    channels=[c.channel_point for c in node.channels]
                )
                continue
            if node.local_balance and not node.remote_balance:
                log.error(
                    f'Aborting {name} processing, possible capital waste',
                    local_balance=node.local_balance,
                    remote_balance=node.remote_balance,
                    channels=[c.channel_point for c in node.channels]
                )
                continue

            response = self.rpc.open_channel(
                node_pubkey_string=node.pubkey,
                local_funding_amount=max(1000000, node.remote_balance),
                push_sat=0,
                sat_per_byte=1,
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
                    details=e.details()
                )

    def pagerank(self):
        G = nx.DiGraph()
        for index, node in enumerate(self.nodes):
            G.add_node(node['pub_key'], **node)
        for index, edge in enumerate(self.edges):
            G.add_edge(
                edge['node1_pub'],
                edge['node2_pub'],
                weight=int(edge['capacity']),
                **edge
            )
        data = nx.pagerank(G)
        return data

        # path_graph = nx.path_graph(G)
        # data = nx.eigenvector_centrality(path_graph)
        # self.print_summary('eigen', data)
