from sqlalchemy import (
    Column,
    DateTime,
    func,
    Integer,
    String)

from database.base import Base


class EventLog(Base):
    __tablename__ = 'event_log'

    created_at = Column(DateTime(timezone=True),
                        nullable=False,
                        server_default=func.now())

    id = Column(Integer, primary_key=True)

    pubkey = Column(String)
    table = Column(String)
    column = Column(String)
    old_value = Column(String)
    new_value = Column(String)
