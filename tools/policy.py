from google.protobuf.json_format import MessageToDict

from lnd_sql import session_scope
from lnd_sql.logger import log


class SetPolicy(object):

    @staticmethod
    def set_policy(rpc):
        with session_scope() as session:
            routers = session.execute("""
SELECT open_channels.remote_pubkey,
       their_node.alias,
       open_channels.chan_id,
       open_channels.capacity,
       open_channels.local_balance,
       open_channels.remote_balance,
       round(open_channels.local_balance::FLOAT/open_channels.capacity*100) as local_balance_pct,
       our_routing_policies.fee_base_msat AS our_base_fee,
       our_routing_policies.fee_rate_milli_msat AS our_fee_rate,
       array_agg(DISTINCT associated_channels.chan_id) AS associated_channels,
       count(out_forwarding_events.id)       out_10_day_count_pmts,
       sum(out_forwarding_events.amount_out) out_10_day_total_pmts,
       count(in_forwarding_events.id)        in_10_day_count_pmts,
       to_char(sum(in_forwarding_events.amount_in)::NUMERIC, '999,999,999')   in_10_day_total_pmts,
       sum(in_forwarding_events.fee)         fee_10_day_total
from open_channels
       JOIN forwarding_events out_forwarding_events
            ON out_forwarding_events.channel_id_out = open_channels.chan_id
              and out_forwarding_events.timestamp >
                  current_date - interval '10' day
       JOIN forwarding_events in_forwarding_events
            ON in_forwarding_events.channel_id_in = open_channels.chan_id
              and
               in_forwarding_events.timestamp > current_date - interval '10' day
       JOIN routing_policies our_routing_policies
            ON our_routing_policies.channel_id = open_channels.chan_id
              AND our_routing_policies.pubkey = open_channels.local_pubkey
       JOIN lightning_nodes their_node
              ON their_node.pubkey = open_channels.remote_pubkey
       JOIN open_channels associated_channels
       ON open_channels.remote_pubkey = associated_channels.remote_pubkey
GROUP BY open_channels.remote_pubkey, open_channels.chan_id,
         open_channels.capacity, our_routing_policies.fee_base_msat,
         our_routing_policies.fee_base_msat, fee_rate_milli_msat,
         their_node.alias, open_channels.local_balance, open_channels.remote_balance
HAVING count(in_forwarding_events.id) > 10
AND sum(in_forwarding_events.amount_in) > 100000
ORDER BY in_10_day_total_pmts DESC, capacity DESC, remote_pubkey;
            """)
            router_fee_range = (100, 500)



        response = rpc.update_channel_policy(
            base_fee_msat=1000,
            fee_rate=0.000001,
            time_lock_delta=144
        )
        response_dict = MessageToDict(response)
        log.info('update_channel_policy', response=response_dict)