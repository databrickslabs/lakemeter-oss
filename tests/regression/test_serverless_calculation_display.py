from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CALCULATOR = ROOT / "frontend" / "src" / "pages" / "Calculator.tsx"


def test_serverless_compute_display_shows_full_dbu_formula():
    source = CALCULATOR.read_text()

    assert source.count("<ServerlessComputeDbuBreakdown\n") == 2
    assert "Driver" in source
    assert "DBU/hr each" in source
    assert "Photon {photonMultiplier.toFixed(2)}×" in source
    assert "Performance Optimized" in source
    assert "Standard" in source


def test_all_purpose_display_always_uses_performance_optimized_mode():
    source = CALCULATOR.read_text()

    assert "workloadType === 'ALL_PURPOSE'" in source
    assert "const modeMultiplier = performanceOptimized ? 2 : 1" in source


def test_serverless_display_no_longer_hides_dbu_hour_inputs():
    source = CALCULATOR.read_text()

    assert "(Serverless{photonEnabled ? ' + Photon' : ''})" not in source
    assert "dbuPerHour / (baseDBUPerHour * modeMultiplier)" in source
