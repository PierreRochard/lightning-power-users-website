from statistics import median

from google.protobuf.json_format import MessageToDict
from sqlalchemy import and_

from lnd_sql import session_scope
from lnd_sql.logger import log
from lnd_sql.models import OpenChannels, RoutingPolicies


class SetPolicy(object):

    def calculate_fee(self, volume):
        slope = (self.router_fee_range[1] - self.router_fee_range[0]) / (
                self.median_volume - self.lowest_volume)
        intercept = -self.lowest_volume * slope
        return min(int(intercept + slope * volume + self.router_fee_range[0]),
                   500)

    def set_policy(self, rpc):
        with session_scope() as session:
            routers = session.execute("""
SELECT open_channels.remote_pubkey,
       their_node.alias,
       open_channels.chan_id,
       open_channels.channel_point,
       open_channels.capacity,
       open_channels.local_balance,
       open_channels.remote_balance,
       round(open_channels.local_balance::FLOAT/open_channels.capacity*100) as channel_percent_ours,
       open_peers.percent_ours as total_percent_ours,
       our_routing_policies.fee_base_msat AS our_base_fee,
       our_routing_policies.fee_rate_milli_msat AS our_fee_rate,
       their_routing_policies.fee_base_msat AS their_base_fee,
       their_routing_policies.fee_rate_milli_msat AS their_fee_rate,
       array_agg(DISTINCT associated_channels.channel_point) AS associated_channels,
       count(out_forwarding_events.id)       out_10_day_count_pmts,
       sum(out_forwarding_events.amount_out) out_10_day_total_pmts,
       count(in_forwarding_events.id)        in_10_day_count_pmts,
       sum(in_forwarding_events.amount_in)   in_10_day_total_pmts,
       sum(in_forwarding_events.fee)         fee_10_day_total
from open_channels
       JOIN forwarding_events out_forwarding_events
            ON out_forwarding_events.channel_id_out = open_channels.chan_id
              and out_forwarding_events.timestamp >
                  current_date - interval '30' day
       JOIN forwarding_events in_forwarding_events
            ON in_forwarding_events.channel_id_in = open_channels.chan_id
              and
               in_forwarding_events.timestamp > current_date - interval '30' day
       JOIN routing_policies our_routing_policies
            ON our_routing_policies.channel_id = open_channels.chan_id
              AND our_routing_policies.pubkey = open_channels.local_pubkey
       JOIN routing_policies their_routing_policies
            ON their_routing_policies.channel_id = open_channels.chan_id
              AND their_routing_policies.pubkey = open_channels.remote_pubkey
       JOIN lightning_nodes their_node
              ON their_node.pubkey = open_channels.remote_pubkey
       JOIN open_channels associated_channels
       ON open_channels.remote_pubkey = associated_channels.remote_pubkey
       JOIN open_peers ON open_peers.remote_pubkey = open_channels.remote_pubkey
GROUP BY open_channels.remote_pubkey, open_channels.chan_id, open_channels.channel_point,
         open_channels.capacity, our_routing_policies.fee_base_msat,
         our_routing_policies.fee_base_msat, our_routing_policies.fee_rate_milli_msat,
         their_node.alias, open_channels.local_balance, open_channels.remote_balance,
         open_peers.percent_ours, their_routing_policies.fee_base_msat, their_routing_policies.fee_rate_milli_msat
HAVING count(in_forwarding_events.id) > 10
AND sum(in_forwarding_events.amount_in) > 100000
ORDER BY sum(in_forwarding_events.amount_in) DESC, capacity DESC, remote_pubkey;
            """)
            self.router_fee_range = (100, 500)
            routers = list(routers)
            volumes = [r.in_10_day_total_pmts for r in routers]
            routing_channel_points = [r.associated_channels for r in routers]
            routing_channel_points = [item for sublist in routing_channel_points
                                      for item in sublist]
            self.lowest_volume = min(volumes)
            self.median_volume = median(volumes)
            self.highest_volume = max(volumes)

            highest_fee = self.calculate_fee(self.highest_volume)
            lowest_fee = self.calculate_fee(self.lowest_volume)
            assert lowest_fee == self.router_fee_range[0]
            assert highest_fee == self.router_fee_range[1]

            for index, routing_channel in enumerate(routers):
                fee = self.calculate_fee(routing_channel.in_10_day_total_pmts)
                if fee == routing_channel.our_fee_rate:
                    continue
                for channel_point in routing_channel.associated_channels:
                    response = rpc.update_channel_policy(
                        base_fee_msat=1000,
                        fee_rate=0.000001 * fee,
                        time_lock_delta=77,
                        chan_point=channel_point,
                    )
                    response_dict = MessageToDict(response)
                    log.info(
                        'update_channel_policy',
                        fee=fee,
                        response=response_dict
                    )

            default_fee = 10
            for channel in (
                    session.query(OpenChannels)
                            .join(RoutingPolicies, and_(
                        RoutingPolicies.pubkey == OpenChannels.local_pubkey,
                        RoutingPolicies.channel_id == OpenChannels.chan_id
                    )).filter(
                        RoutingPolicies.fee_rate_milli_msat != default_fee).all()
            ):
                if channel.channel_point in routing_channel_points:
                    continue

                response = rpc.update_channel_policy(
                    base_fee_msat=1000,
                    fee_rate=0.000001 * default_fee,
                    time_lock_delta=77,
                    chan_point=channel.channel_point,
                )
                response_dict = MessageToDict(response)
                log.info(
                    'update_channel_policy',
                    response=response_dict,
                    default_fee=default_fee
                )
