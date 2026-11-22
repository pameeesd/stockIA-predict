"""Pruebas unitarias de los métodos de pronóstico y las métricas."""
import numpy as np
import pytest


def row(*values):
    return np.array([values], dtype=float)


def test_tsb_matches_hand_calculation(bt):
    # alpha = beta = 0,5. Primera venta en t=2 (y=4): p=1, z=4.
    # t=3 pronóstico 1*4=4; y=0 -> p=0,5. t=4 pronóstico 0,5*4=2; y=2 -> p=0,75, z=3. t=5 pronóstico 2,25.
    F = bt.forecast_tsb(row(0, 0, 4, 0, 2), 0.5, 0.5)
    assert F.shape == (1, 6)
    np.testing.assert_allclose(F[0], [0, 0, 0, 4, 2, 2.25])


def test_tsb_constant_demand_converges_to_level(bt):
    F = bt.forecast_tsb(row(*[10] * 30), 0.3, 0.3)
    assert F[0, -1] == pytest.approx(10.0)


def test_tsb_decays_after_prolonged_zeros(bt):
    y = row(10, 10, 10, *[0] * 20)
    F = bt.forecast_tsb(y, 0.3, 0.3)
    assert F[0, -1] < 0.05 * 10  # la probabilidad de venta cae durante la ausencia de ventas


def test_croston_constant_demand(bt):
    F = bt.forecast_croston(row(*[5] * 20), 0.2)
    assert F[0, 1:] == pytest.approx(np.full(20, 5.0))


def test_sba_applies_bias_correction(bt):
    y = row(*[5] * 20)
    croston = bt.forecast_croston(y, 0.2)
    sba = bt.forecast_croston(y, 0.2, sba=True)
    np.testing.assert_allclose(sba, croston * (1 - 0.2 / 2))


def test_moving_average_and_last_week(bt):
    y = row(1, 2, 3, 4, 5, 6)
    ma4 = bt.forecast_moving_average(y, 4)
    assert ma4[0, 5] == pytest.approx((2 + 3 + 4 + 5) / 4)
    assert ma4[0, 6] == pytest.approx((3 + 4 + 5 + 6) / 4)
    last = bt.forecast_last_week(y)
    assert last[0, 6] == 6 and last[0, 0] == 0


@pytest.mark.parametrize("name", ["tsb", "croston", "sba", "ma4", "last"])
def test_forecast_for_week_t_never_uses_week_t_or_later(bt, rng, name):
    """Sin fuga de información: F[:, t] solo depende de Y[:, :t]."""
    methods = {
        "tsb": lambda Y: bt.forecast_tsb(Y, 0.3, 0.3),
        "croston": lambda Y: bt.forecast_croston(Y, 0.3),
        "sba": lambda Y: bt.forecast_croston(Y, 0.3, sba=True),
        "ma4": lambda Y: bt.forecast_moving_average(Y, 4),
        "last": bt.forecast_last_week,
    }
    f = methods[name]
    Y = rng.poisson(2.0, size=(40, 60)).astype(float) * (rng.random((40, 60)) < 0.5)
    t = 30
    Y2 = Y.copy()
    Y2[:, t:] = rng.integers(0, 500, size=Y2[:, t:].shape)  # cambiar el "futuro"
    np.testing.assert_allclose(f(Y)[:, : t + 1], f(Y2)[:, : t + 1])


def test_forecasts_are_never_negative(bt, rng):
    Y = rng.poisson(1.5, size=(50, 80)).astype(float)
    for F in (bt.forecast_tsb(Y, 0.5, 0.5), bt.forecast_croston(Y, 0.5), bt.forecast_moving_average(Y, 13)):
        assert (F >= 0).all()


def test_wape_and_score(bt):
    actual = np.array([10.0, 0.0, 30.0])
    pred = np.array([12.0, 3.0, 20.0])
    assert bt.wape(actual, pred) == pytest.approx(100 * (2 + 3 + 10) / 40)
    s = bt.score(actual, pred)
    assert s["bias_pct"] == pytest.approx(100 * (35 - 40) / 40)
    assert s["MAE"] == pytest.approx(5.0)
    assert s["actual_units"] == 40 and s["predicted_units"] == 35


def test_score_clips_negative_predictions(bt):
    assert bt.score(np.array([10.0]), np.array([-5.0]))["predicted_units"] == 0


def test_segmentation_quadrants(bt):
    n = 52
    smooth = np.full(n, 20.0)
    intermittent = np.zeros(n)
    intermittent[::4] = 20.0
    erratic = np.tile([1.0, 100.0], n // 2)
    lumpy = np.zeros(n)
    lumpy[::4] = np.tile([1.0, 100.0], 7)[:13]
    labels = bt.segment_at(np.vstack([smooth, intermittent, erratic, lumpy]), n)
    assert list(labels) == ["smooth", "intermittent", "erratic", "lumpy"]


def test_segmentation_uses_only_history_before_origin(bt, rng):
    Y = rng.poisson(3.0, size=(30, 80)).astype(float)
    Y2 = Y.copy()
    Y2[:, 56:] = 0
    np.testing.assert_array_equal(bt.segment_at(Y, 56), bt.segment_at(Y2, 56))
