from pprint import pformat

from sqlalchemy import and_, func
from sqlalchemy.orm.exc import NoResultFound

from lnd_sql import session_scope
from lnd_sql.models import OpenChannels


class ChannelQueries(object):
    @staticmethod
    def get_peer_channel_totals(remote_pubkey: str) -> dict:
        with session_scope() as session:
            try:
                record = (
                    session
                        .query(
                            OpenChannels.remote_pubkey,
                            func.count(OpenChannels.id).label('count'),
                            func.sum(OpenChannels.capacity).label('capacity')
                        )
                        .filter(
                            and_(
                                OpenChannels.remote_pubkey == remote_pubkey
                            )
                        )
                        .group_by(OpenChannels.remote_pubkey)
                        .one()
                )
                # noinspection PyProtectedMember
                data = record._asdict()
                data['capacity'] = str(data['capacity'])
            except NoResultFound:
                data = None
            return data


if __name__ == '__main__':
    results_data = ChannelQueries.get_peer_channel_totals(
        remote_pubkey='0263824afadb0f50603d7fda6325f285a889b60371416cd37ebddb48aacf2b37bf'
    )
    print(pformat(results_data))
