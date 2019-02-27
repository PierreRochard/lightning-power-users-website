from contextlib import contextmanager
import os
import uuid

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import sessionmaker

from website.constants import keyring
from website.logger import log

is_test = False


def keyring_get_or_create(label: str):
    log.debug('getting label', label=label)
    password = keyring.get_password(
        service=label,
        username=label,
    )
    if password is None:
        log.debug('creating label', label=label)
        password = uuid.uuid4().hex
        keyring.set_password(
            service=label,
            username=label,
            password=password
        )
    return password


def get_url():
    pg_url = URL(drivername='postgresql+psycopg2',
                 host=os.environ['LPU_PGHOST'],
                 port=os.environ['LPU_PGPORT'],
                 database=keyring_get_or_create('LPU_PGDATABASE'),
                 username=keyring_get_or_create('LPU_PGUSER'),
                 password=keyring_get_or_create('LPU_PGPASSWORD'))
    return pg_url


@contextmanager
def session_scope(echo=False,
                  raise_integrity_error=True,
                  raise_programming_error=True):

    pg_url = get_url()
    engine = create_engine(pg_url, echo=echo,
                           connect_args={'sslmode': 'prefer'})
    session_maker = sessionmaker(bind=engine)
    session = session_maker()

    try:
        yield session
        session.commit()
    except IntegrityError:
        log.debug('IntegrityError', exc_info=True)
        session.rollback()
        if raise_integrity_error:
            raise
    except ProgrammingError:
        log.debug('ProgrammingError', exc_info=True)
        session.rollback()
        if raise_programming_error:
            raise
    except Exception as e:
        log.debug('Exception', exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()
