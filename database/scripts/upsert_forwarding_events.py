# noinspection PyPackageRequirements
from datetime import datetime

from google.protobuf.json_format import MessageToDict
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.elements import and_

from database import session_scope
from database.models.forwarding_events import ForwardingEvents
from lnd_grpc.lnd_grpc import Client
from lnd_grpc.protos.rpc_pb2 import GetInfoResponse
from website.logger import log


class UpsertForwardingEvents(object):
    rpc: Client

    def __init__(self,
                 tls_cert_path: str = None,
                 macaroon_path: str = None,
                 lnd_network: str = 'mainnet',
                 lnd_grpc_host: str = '127.0.0.1',
                 lnd_grpc_port: str = '10009'):
        self.rpc = Client(
            tls_cert_path=tls_cert_path,
            macaroon_path=macaroon_path,
            network=lnd_network,
            grpc_host=lnd_grpc_host,
            grpc_port=lnd_grpc_port,
        )
        forwarding_events = self.rpc.forwarding_history(
            start_time=1,
            end_time=int(datetime.now().timestamp()),
            num_max_events=10000
        )
        log.debug('forwarding_events',
                  last_offset_index=forwarding_events.last_offset_index)
        info: GetInfoResponse = self.rpc.get_info()
        forwarding_event_dicts = [MessageToDict(c) for c in forwarding_events.forwarding_events]
        for forwarding_event_dict in forwarding_event_dicts:
            self.upsert(info.identity_pubkey, forwarding_event_dict)

    @staticmethod
    def upsert(local_pubkey, data: dict):
        with session_scope() as session:
            try:
                record = (
                    session
                        .query(ForwardingEvents)
                        .filter(and_(ForwardingEvents.local_pubkey == local_pubkey,
                                     ForwardingEvents.timestamp == data['timestamp'])
                                )
                        .one()
                )
            except NoResultFound:
                record = ForwardingEvents()
                record.local_pubkey = local_pubkey
                record.timestamp = data['timestamp']
                session.add(record)

            for key, value in data.items():
                setattr(record, key, value)


if __name__ == '__main__':
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

    # while True:
    UpsertForwardingEvents(tls_cert_path=args.tls,
                           macaroon_path=args.macaroon)
        # time.sleep(60)
