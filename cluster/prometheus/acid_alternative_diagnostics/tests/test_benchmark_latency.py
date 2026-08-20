import pytest
from acid_alternative_diagnostics.benchmark_latency import latency_summary


def test_latency_summary_reports_declared_quantiles_and_iqr():
    result = latency_summary([1.0, 2.0, 3.0, 4.0])
    assert result["calls"] == 4
    assert result["median_ms"] == pytest.approx(2.5)
    assert result["q25_ms"] == pytest.approx(1.75)
    assert result["q75_ms"] == pytest.approx(3.25)
    assert result["iqr_ms"] == pytest.approx(1.5)
    assert result["p95_ms"] == pytest.approx(3.85)


def test_latency_summary_rejects_empty_or_negative_values():
    with pytest.raises(ValueError, match="nonempty"):
        latency_summary([])
    with pytest.raises(ValueError, match="nonnegative"):
        latency_summary([1.0, -1.0])
