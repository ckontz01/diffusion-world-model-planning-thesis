"""Coordinate verification only; does not set bodies or change observations."""
import numpy as np

def verify_pusht_initialization(actual,expected,center_of_gravity):
    actual=np.asarray(actual,dtype=np.float64);source=np.asarray(expected)
    cog=np.asarray(center_of_gravity,dtype=np.float64)
    if actual.shape!=(7,) or source.shape!=(7,) or source.dtype not in (np.dtype('float32'),np.dtype('float64')) or not np.isfinite(actual).all() or not np.isfinite(source).all():
        raise RuntimeError('PushT initialization shape/precision/nonfinite mismatch')
    if cog.shape!=(2,) or not np.array_equal(cog,[0.,45.]):raise RuntimeError('PushT native geometry changed')
    fixed=[0,1,4,5,6]
    if not np.array_equal(actual[fixed],source[fixed]):raise RuntimeError('PushT non-position initialization changed')
    delta=np.abs(actual[2:4]-source[2:4].astype(np.float64))
    # Pymunk stores the body CoG position and reconstructs its local origin.
    # Bound only that two-coordinate round trip, below the original independent
    # 1e-12 reset acceptance bound and with exact stored-source-precision equality.
    bound=np.minimum(1e-12,8*np.finfo(np.float64).eps*np.maximum.reduce([np.ones(2),np.abs(source[2:4].astype(np.float64)),np.full(2,45.)]))
    if np.any(delta>bound) or not np.array_equal(actual.astype(source.dtype),source):raise RuntimeError('PushT block position initialization changed beyond round-trip bound')
    return dict(contract='pusht-body-position-roundtrip-v1',block_position_errors=delta.tolist(),bounds=bound.tolist(),
                max_absolute_error=float(delta.max()),source_dtype=str(source.dtype),source_precision_roundtrip=True,other_fields_exact=True,center_of_gravity=cog.tolist())
