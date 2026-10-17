"""Prospective finite byte reservations, never a claim of actual free storage.

Metadata encodings preserve every member/copy. Archives stay uncompressed; no
hardlink/deduplication/deletion saving is used. Actual full-future root, source,
control-copy, preparation and designated-volume measurements remain mandatory.
"""
from .archive_v2 import canonical,checked_plan,OVERHEAD,MAX_MANIFEST

PORTABLE_LIMIT=12000000
SIDECAR_LIMIT=1000000
SOURCE_DOC_BUNDLE_LIMIT=4500000
SMALL_SOURCE_PACKAGES_ALL_COPIES_LIMIT=2200000
AUX_RESERVATIONS={'source_docs_four_full_logical_copies':SOURCE_DOC_BUNDLE_LIMIT*4,
                  'monitor_240_checks_all_copies':240*65536,
                  'portable_inventory_remote_and_designated_SSD':PORTABLE_LIMIT*2,
                  'two_sidecars_two_full_copies_each':SIDECAR_LIMIT*4,
                  'new_small_source_packages_all_logical_copies':SMALL_SOURCE_PACKAGES_ALL_COPIES_LIMIT}


def prove(planned,root_paths,final_contract_sha256,preparation_full_future_bytes):
    members=checked_plan(planned)
    if type(preparation_full_future_bytes) is not int or not 0<preparation_full_future_bytes<=5368709120:
        raise ValueError('separately authenticated actual full-future preparation bytes, no full-cap assumption')
    total_aux=sum(AUX_RESERVATIONS.values())
    if total_aux!=63928640 or total_aux>64000000:raise ValueError('all new auxiliary logical copies within unchanged64MB')
    portable={k:v for k,v in planned.items() if k!='members'}
    rows={};manifest_rows={};regular=0
    for name,row in sorted(members.items()):
        if row['type']=='file':
            rows[name]={'type':'file','bytes':row['bytes'],'sha256':'0'*64}
            manifest_rows[name]=dict(rows[name],payload='payload/'+str(regular).zfill(6));regular+=1
        else:rows[name]={'type':'symlink','target':row['target']};manifest_rows[name]=rows[name]
    portable['members']=rows
    # Hashes always have64 hex characters: these exact byte-size forecasts do
    # not assume compression or omit names. Actual identities are bound later.
    portable_bytes=len(canonical(portable))
    manifest={'schema':'WM-DIAG0-RC1-ARCHIVE-v2','binding':{'root_paths':root_paths,'final_contract_sha256':final_contract_sha256},
              'root_labels':planned['root_labels'],'members':manifest_rows,
              'logical_payload_bytes_no_discounts':planned['logical_payload_bytes_no_discounts'],
              'alias_policy':'metadata-only; never followed/extracted/executed','compression_or_hardlink_savings_assumed':False}
    manifest_bytes=len(canonical(manifest))
    if portable_bytes>PORTABLE_LIMIT or manifest_bytes>MAX_MANIFEST:raise ValueError('full future portable/manifest writer bounds BEFORE archive creation')
    # Deliberately conservative additions, even if some presently measured
    # source/control/artificial bytes are already in the whole-root inventory.
    live=planned['logical_payload_bytes_no_discounts']+64000000+4000000
    archive=live+OVERHEAD;inclusive=live+2*14000000000+preparation_full_future_bytes
    if live>13500000000 or archive>14000000000 or inclusive>44000000000:raise ValueError('unchanged live/archive/inclusive full-future limits; no deletion or copy discounts')
    return {'status':'FINITE_FULL_FUTURE_BYTE_ARITHMETIC_NOT_MEASUREMENT_OR_VOLUME_GATE',
            'full_future_live_bytes':live,'full_future_archive_bytes':archive,'full_future_inclusive_bytes':inclusive,
            'preparation_full_future_bytes_supplied_not_authenticated_here':preparation_full_future_bytes,
            'two_full_archive_copies_reserved_bytes':28000000000,'archive_overhead_reserved_bytes':OVERHEAD,
            'final_artificial_whole_root_reservation_bytes':4000000,'all_new_auxiliary_logical_copy_reservation_bytes':64000000,
            'auxiliary_subreservations':AUX_RESERVATIONS,'auxiliary_subreservation_total':total_aux,'locked_auxiliary_margin_bytes':71360,
            'forecast_portable_bytes':portable_bytes,'forecast_manifest_bytes':manifest_bytes,
            'portable_writer_cap':PORTABLE_LIMIT,'sidecar_writer_cap':SIDECAR_LIMIT,
            'actual_preparation_roots_copies_free_space_or_SSD_authenticated':False,'final_gate_ready':False}
