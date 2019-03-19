from pprint import pformat

from sqlalchemy import and_, func, Float, cast
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
                            func.sum(OpenChannels.capacity).label('capacity'),
                            cast(
                                func.sum(OpenChannels.local_balance)
                                / func.sum(OpenChannels.capacity), Float).label('balance')
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

    @staticmethod
    def get_channel_totals() -> dict:
        with session_scope() as session:
            peers = (
                session
                    .query(
                    OpenChannels.remote_pubkey,
                    func.count(OpenChannels.id).label('count'),
                    func.sum(OpenChannels.capacity).label('capacity'),
                    cast(func.sum(OpenChannels.local_balance) / func.sum(OpenChannels.capacity), Float).label('balance')
                )
                    .order_by(func.count(OpenChannels.id))
                    .order_by(func.sum(OpenChannels.capacity).desc())
                    .group_by(OpenChannels.remote_pubkey)
                    .limit(10)
            )
            return list(peers)


if __name__ == '__main__':
    # results_data = ChannelQueries.get_peer_channel_totals(
    #     remote_pubkey='0263824afadb0f50603d7fda6325f285a889b60371416cd37ebddb48aacf2b37bf'
    # )
    results_data = ChannelQueries.get_channel_totals()
    print(pformat(results_data))
