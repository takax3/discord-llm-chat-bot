from unittest.mock import MagicMock, patch

from discordbot.services.gpu_power_sampler import GpuPowerSampler


def _make_sampler_with_mock_handle(power_mw: int) -> GpuPowerSampler:
    sampler = GpuPowerSampler.__new__(GpuPowerSampler)
    handle = MagicMock()
    sampler._handle = handle
    with patch("discordbot.services.gpu_power_sampler._pynvml") as mock_nvml:
        mock_nvml.nvmlDeviceGetPowerUsage.return_value = power_mw
        sampler._mock_nvml = mock_nvml
    return sampler, mock_nvml


def test_available_is_false_when_handle_is_none() -> None:
    sampler = GpuPowerSampler.__new__(GpuPowerSampler)
    sampler._handle = None
    assert sampler.available is False


def test_available_is_true_when_handle_is_set() -> None:
    sampler = GpuPowerSampler.__new__(GpuPowerSampler)
    sampler._handle = MagicMock()
    assert sampler.available is True


def test_read_watts_returns_none_when_unavailable() -> None:
    sampler = GpuPowerSampler.__new__(GpuPowerSampler)
    sampler._handle = None
    assert sampler.read_watts() is None


def test_read_watts_converts_mw_to_watts() -> None:
    sampler = GpuPowerSampler.__new__(GpuPowerSampler)
    sampler._handle = MagicMock()
    with patch("discordbot.services.gpu_power_sampler._pynvml") as mock_nvml:
        mock_nvml.nvmlDeviceGetPowerUsage.return_value = 250_000  # 250 W in mW
        result = sampler.read_watts()
    assert result == 250.0


def test_read_watts_returns_none_on_nvml_error() -> None:
    sampler = GpuPowerSampler.__new__(GpuPowerSampler)
    sampler._handle = MagicMock()
    with patch("discordbot.services.gpu_power_sampler._pynvml") as mock_nvml:
        mock_nvml.nvmlDeviceGetPowerUsage.side_effect = Exception("NVML error")
        result = sampler.read_watts()
    assert result is None


def test_init_sets_handle_to_none_when_pynvml_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("discordbot.services.gpu_power_sampler._PYNVML_AVAILABLE", False)
    sampler = GpuPowerSampler()
    assert sampler._handle is None
    assert sampler.available is False
