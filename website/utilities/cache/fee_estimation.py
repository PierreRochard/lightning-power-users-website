from datetime import datetime

from website.logger import log
from website.extensions import bitcoind
from website.utilities.dump_json import dump_json


def cache_fee_estimate():

    fee_estimates = [
        dict(conf_target=1, label='Ten minutes'),
        dict(conf_target=6, label='One_hour'),
        dict(conf_target=36, label='Six hours'),
        dict(conf_target=72, label='Twelve hours'),
        dict(conf_target=144, label='One day'),
        dict(conf_target=288, label='Two days'),
        dict(conf_target=432, label='Three days'),
        dict(conf_target=1008, label='One week')
    ]

    for fee_estimate in fee_estimates:
        # noinspection PyProtectedMember
        fee_estimate['conservative'] = bitcoind.estimate_smart_fee(
            fee_estimate['conf_target'],
            'CONSERVATIVE'
        )

        # noinspection PyProtectedMember
        fee_estimate['economical'] = bitcoind.estimate_smart_fee(
            fee_estimate['conf_target'],
            'ECONOMICAL'
        )

        log.info(
            'estimate_smart_fee',
            fee_estimate=fee_estimate,
        )

    today = datetime.now()
    dump_json(data=fee_estimates, name='fee_estimate', date=today)


if __name__ == '__main__':
    cache_fee_estimate()
