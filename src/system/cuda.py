"""Preload CUDA libs from pip packages to avoid lazy import issues."""

from pathlib import Path
import ctypes


def preload_cuda_libs():
    try:
        import nvidia.cublas

        for base_path in nvidia.cublas.__path__:
            cublas_lib_path = Path(base_path) / "lib"
            if cublas_lib_path.exists():
                for lib in sorted(cublas_lib_path.glob("libcublas*.so*")):
                    try:
                        ctypes.CDLL(str(lib), mode=ctypes.RTLD_GLOBAL)
                    except OSError:
                        pass
                break
    except (ImportError, TypeError, AttributeError):
        pass

    try:
        import nvidia.cudnn

        for base_path in nvidia.cudnn.__path__:
            cudnn_lib_path = Path(base_path) / "lib"
            if cudnn_lib_path.exists():
                for lib in sorted(cudnn_lib_path.glob("libcudnn*.so*")):
                    try:
                        ctypes.CDLL(str(lib), mode=ctypes.RTLD_GLOBAL)
                    except OSError:
                        pass
                break
    except (ImportError, TypeError, AttributeError):
        pass
