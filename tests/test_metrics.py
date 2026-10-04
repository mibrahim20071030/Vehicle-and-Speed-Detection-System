import pytest

from metrics import percent_error, speed_errors


def test_percent_error():
    assert percent_error(105, 100) == pytest.approx(5.0)
    assert percent_error(95, 100) == pytest.approx(5.0)


def test_percent_error_zero_truth():
    assert percent_error(3, 0) is None


def test_speed_errors():
    e = speed_errors([52, 48], [50, 50])
    assert e["mae_kmh"] == pytest.approx(2.0)
    assert e["bias_kmh"] == pytest.approx(0.0)
    assert e["mape_pct"] == pytest.approx(4.0)
