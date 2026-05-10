from __future__ import annotations

try:
    import pynvml as _pynvml
    _PYNVML_AVAILABLE = True
except ImportError:
    _pynvml = None  # type: ignore[assignment]
    _PYNVML_AVAILABLE = False


class GpuPowerSampler:
    """NVML経由でGPU消費電力を取得する。NVIDIA環境以外では available=False になる。"""

    def __init__(self, device_index: int = 0) -> None:
        self._handle: object = None
        if not _PYNVML_AVAILABLE:
            return
        try:
            _pynvml.nvmlInit()
            self._handle = _pynvml.nvmlDeviceGetHandleByIndex(device_index)
        except Exception:
            pass

    @property
    def available(self) -> bool:
        return self._handle is not None

    def read_watts(self) -> float | None:
        """現在のGPU消費電力（W）を返す。取得失敗時はNone。"""
        if self._handle is None:
            return None
        try:
            return _pynvml.nvmlDeviceGetPowerUsage(self._handle) / 1000.0
        except Exception:
            return None
