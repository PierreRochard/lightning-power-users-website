from datetime import datetime
from decimal import Decimal

import pytz
from sqlalchemy.orm.exc import NoResultFound

from lnd_sql import session_scope
from lnd_sql.models import InboundCapacityRequest
from website.constants import CAPACITY_FEE_RATES, EXPECTED_BYTES
from website.logger import log


class InboundCapacityRequestQueries(object):
    @staticmethod
    def insert(session_id: str):
        with session_scope() as session:
            new_request = InboundCapacityRequest()
            new_request.session_id = session_id
            new_request.status = 'registered'
            session.add(new_request)

    @staticmethod
    def update_status(session_id: str, status: str):
        with session_scope() as session:
            request: InboundCapacityRequest = (
                session.query(InboundCapacityRequest)
                    .filter(InboundCapacityRequest.session_id == session_id)
                    .order_by(InboundCapacityRequest.updated_at.desc())
                    .first()
            )
            request.status = status

    @staticmethod
    def update_connection(session_id: str, remote_pubkey: str, remote_host: str,
                          status: str):
        with session_scope() as session:
            request: InboundCapacityRequest = (
                session.query(InboundCapacityRequest)
                    .filter(InboundCapacityRequest.session_id == session_id)
                    .order_by(InboundCapacityRequest.updated_at.desc())
                    .first()
            )
            request.remote_pubkey = remote_pubkey
            request.remote_host = remote_host
            request.status = status

    @staticmethod
    def update_capacity(session_id: str, capacity: int,
                        capacity_fee_rate: Decimal, status: str):
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
            request.status = status

    @staticmethod
    def update_tx_fee_and_invoice(session_id: str, transaction_fee_rate: int,
                                  r_hash: str, status: str):
        with session_scope() as session:
            icr: InboundCapacityRequest = (
                session.query(InboundCapacityRequest)
                    .filter(InboundCapacityRequest.session_id == session_id)
                    .order_by(InboundCapacityRequest.updated_at.desc())
                    .first()
            )
            icr.transaction_fee_rate = transaction_fee_rate
            icr.expected_bytes = EXPECTED_BYTES
            icr.transaction_fee = icr.transaction_fee_rate * EXPECTED_BYTES
            icr.total_fee = icr.capacity_fee + icr.transaction_fee
            icr.invoice_r_hash = r_hash
            icr.status = status

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
