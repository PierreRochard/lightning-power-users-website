from pprint import pformat
from typing import List

from lnd_sql import session_scope
from lnd_sql.models import LightningAddresses


class LightningAddressesQueries(object):
    @staticmethod
    def get(remote_pubkey: str) -> List[str]:
        with session_scope() as session:
            addresses = (
                session.query(LightningAddresses).filter(
                    LightningAddresses.pubkey == remote_pubkey)
                    .all()
            )
            return [a.address for a in addresses]


if __name__ == '__main__':
    data = LightningAddressesQueries.get('031678745383bd273b4c3dbefc8ffbf4847d85c2f62d3407c0c980430b3257c403')
    print(pformat(data))
