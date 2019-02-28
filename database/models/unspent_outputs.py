from sqlalchemy import (
    BIGINT,
    Column,
    DateTime,
    func,
    String
)
from sqlalchemy.orm import Session

from database import session_scope
from database.base import Base


class UnspentOutputs(Base):
    __tablename__ = 'unspent_outputs'

    created_at = Column(DateTime(timezone=True),
                        nullable=False,
                        server_default=func.now())

    updated_at = Column(DateTime(timezone=True),
                        nullable=False,
                        onupdate=func.now(),
                        server_default=func.now())

    deleted_at = Column(DateTime(timezone=True),
                        nullable=True)

    id = Column(BIGINT, primary_key=True)

    type = Column(String)
    address = Column(String)
    amount_sat = Column(BIGINT)
    script_pubkey = Column(String)
    outpoint = Column(String)
    confirmations = Column(BIGINT)


if __name__ == '__main__':
    session: Session = None
    with session_scope() as session:
        Base.metadata.create_all(session.get_bind())
