from google.protobuf.json_format import MessageToDict

from database import session_scope
from database.models import Balances
from lnd_grpc import lnd_grpc


class Reconciliation(object):
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

    def reconciliation(self):
        info = MessageToDict(self.rpc.get_info())
        wallet_balance = MessageToDict(self.rpc.wallet_balance())
        channel_balance = MessageToDict(self.rpc.channel_balance())
        with session_scope() as session:
            new_balance = Balances()
            new_balance.channel_balance = channel_balance['balance']
            new_balance.channel_pending_open_balance = channel_balance[
                'pending_open_balance']
            new_balance.wallet_total_balance = wallet_balance['total_balance']
            new_balance.wallet_confirmed_balance = wallet_balance[
                'confirmed_balance']
            session.add(new_balance)

        print('here')
