import time

from google.protobuf.json_format import MessageToDict
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.elements import and_

from database import session_scope
from database.models.event_log import EventLog
from database.models.unspent_outputs import UnspentOutputs
from lnd_grpc.lnd_grpc import Client
from lnd_grpc.protos.rpc_pb2 import GetInfoResponse


class UpsertUnspentOutputs(object):
    rpc: Client

    def __init__(self,
                 lnd_network: str = 'mainnet',
                 lnd_grpc_host: str = '127.0.0.1',
                 lnd_grpc_port: str = '10009'):
        self.rpc = Client(
            network=lnd_network,
            grpc_host=lnd_grpc_host,
            grpc_port=lnd_grpc_port,
        )
        unspent_outputs = self.rpc.list_unspent()
        info: GetInfoResponse = self.rpc.get_info()
        channel_dicts = [MessageToDict(c) for c in channels]
        for channel_dict in channel_dicts:
            self.upsert(info.identity_pubkey, channel_dict)

    @staticmethod
    def upsert(local_pubkey, data: dict):
        with session_scope() as session:
            try:
                record = (
                    session
                        .query(UnspentOutputs)
                        .filter(and_(UnspentOutputs.local_pubkey == local_pubkey,
                                     UnspentOutputs.chan_id == data['chan_id'])
                                )
                        .one()
                )
            except NoResultFound:
                record = UnspentOutputs()
                record.local_pubkey = local_pubkey
                record.chan_id = data['chan_id']
                session.add(record)

            for key, value in data.items():
                old_value = getattr(record, key)
                setattr(record, key, value)
                session.commit()
                new_value = getattr(record, key)
                if old_value != new_value:
                    new_event = EventLog()
                    new_event.pubkey = local_pubkey
                    new_event.table = 'open_channels'
                    new_event.column = key
                    new_event.old_value = old_value
                    new_event.new_value = new_value
                    session.add(new_event)


if __name__ == '__main__':
    while True:
        UpsertChannels()
        time.sleep(60)
