from typing import List

from lnd_sql import session_scope
from lnd_sql.models import LightningAddresses


class LightningAddressesQueries(object):
    @staticmethod
    def get(remote_pubkey: str) -> List[dict]:
        with session_scope() as session:
            addresses = (
                session.query(LightningAddresses).filter(
                    LightningAddresses.pubkey == remote_pubkey)
                    .all()
            )
            return [a.__dict__ for a in addresses]
