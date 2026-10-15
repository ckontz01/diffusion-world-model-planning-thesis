"""Conservative full-future arithmetic; excludes no files merely because reused."""


def reconcile(original_live, original_runtime, unused_export, container, environment,
              abandoned_pc_runtime, prior_preparation_reservation,
              live_cap=12_000_000_000, archive_cap=14_000_000_000,
              inclusive_cap=42_000_000_000):
    values = (original_live, original_runtime, unused_export, container, environment,
              abandoned_pc_runtime, prior_preparation_reservation, live_cap,
              archive_cap, inclusive_cap)
    if any(type(x) is not int or x < 0 for x in values):
        raise ValueError('Nonnegative integer byte accounting required')
    if original_runtime > min(original_live, prior_preparation_reservation):
        raise ValueError('Original runtime is not covered by both prior reservations')
    if original_runtime + unused_export > original_live:
        raise ValueError('Double subtraction')
    cluster_runtime = container + environment
    # PC files are outside cluster live storage but remain in inclusive topology.
    # Replace (not add to) the obsolete 4GB PC growth reservation: no more boot work.
    prep = prior_preparation_reservation - original_runtime + abandoned_pc_runtime
    live = original_live - original_runtime - unused_export + cluster_runtime
    lower_topology = live + 2 * archive_cap + prep
    proposed_live_cap = 13_000_000_000
    proposed_inclusive_cap = 44_000_000_000
    proposed_topology = proposed_live_cap + 2 * archive_cap + prep
    return dict(cluster_runtime_bytes=cluster_runtime,
                retained_preparation_full_future_bytes=prep,
                candidate_live_reservation_bytes=live,
                candidate_live_over_current_cap_bytes=max(0, live-live_cap),
                topology_using_candidate_live_reservation_bytes=lower_topology,
                topology_over_current_inclusive_cap_bytes=max(0, lower_topology-inclusive_cap),
                current_caps_fit=live <= live_cap and lower_topology <= inclusive_cap,
                unused_safe_export_reservation_released_for_this_comparison=unused_export,
                proposed_not_authorized_caps=dict(live=proposed_live_cap, archive=archive_cap,
                                                 inclusive=proposed_inclusive_cap),
                proposed_full_topology_bytes=proposed_topology,
                proposed_inclusive_slack_bytes=proposed_inclusive_cap-proposed_topology)
