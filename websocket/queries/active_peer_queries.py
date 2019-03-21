from sqlalchemy.orm.exc import NoResultFound

from lnd_sql import session_scope
from lnd_sql.models import ActivePeers


class ActivePeerQueries(object):
    @staticmethod
    def is_connected(remote_pubkey: str) -> bool:
        with session_scope() as session:
            try:
                peer = (
                    session.query(ActivePeers.id).filter(
                        ActivePeers.remote_pubkey == remote_pubkey)
                        .one()
                )
                return bool(peer)
            except NoResultFound:
                return False
