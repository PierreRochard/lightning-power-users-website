from datetime import datetime
from decimal import Decimal

import pytz
from sqlalchemy.orm.exc import NoResultFound

from lnd_sql import session_scope
from lnd_sql.models import InboundCapacityRequest
from website.constants import CAPACITY_FEE_RATES
from website.logger import log


class InboundCapacityRequestQueries(object):
    @staticmethod
    def insert(session_id: str, remote_pubkey: str, remote_host: str):
        with session_scope() as session:
            new_request = InboundCapacityRequest()
            new_request.session_id = session_id
            new_request.remote_pubkey = remote_pubkey
            new_request.remote_host = remote_host
            session.add(new_request)

    @staticmethod
    def update_capacity(session_id: str, capacity: int,
                        capacity_fee_rate: Decimal):
        with session_scope() as session:
            request: InboundCapacityRequest = (
                session.query(InboundCapacityRequest)
                    .filter(InboundCapacityRequest.session_id == session_id)
                    .order_by(InboundCapacityRequest.updated_at.desc())
                    .first()
            )
            request.capacity = capacity
            request.capacity_fee_rate = capacity_fee_rate
            request.capacity_fee = request.capacity * request.capacity_fee_rate
            delta = [c[2] for c in CAPACITY_FEE_RATES if c[0] == capacity_fee_rate][0]
            today = datetime.utcnow().replace(tzinfo=pytz.utc)
            request.keep_open_until = today + delta

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
