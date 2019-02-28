# noinspection PyPackageRequirements

from lnd_grpc.lnd_grpc import Client


class RpcClient(object):
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
