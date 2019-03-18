from sqlalchemy.orm.exc import NoResultFound

from lnd_sql import session_scope
from lnd_sql.models import InboundCapacityRequest
from website.logger import log


class InboundCapacityRequestQueries(object):
    @staticmethod
    def get_by_invoice(r_hash: str) -> dict:

        with session_scope() as session:
            try:
                record = (
                    session.query(
                        InboundCapacityRequest.session_id,
                        InboundCapacityRequest.remote_pubkey,
                        InboundCapacityRequest.total_fee,
                        InboundCapacityRequest.transaction_fee_rate,
                        InboundCapacityRequest.capacity
                    )
                        .filter(InboundCapacityRequest.invoice_r_hash == r_hash)
                        .one()
                )
                # noinspection PyProtectedMember
                data = record._asdict()
            except NoResultFound:
                log.debug(
                    'r_hash not found in inbound_capacity_request table',
                    r_hash=r_hash
                )
                data = None
            return data
