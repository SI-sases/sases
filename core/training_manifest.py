# -*- coding: utf-8 -*-
"""
SASES Training Manifest
每次训练前调用 start_run()，训练完成后调用 finalize()
自动记录所有训练元数据，保证可复现性
"""
import os
import json
import hashlib
import sys
import uuid
from datetime import datetime, timezone


class TrainingManifest:
    def __init__(self):
        self.run_id = str(uuid.uuid4())
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.manifest = {"run_id": self.run_id, "started_at": self.started_at}

    def record_environment(self):
        env = {"python_version": sys.version.split()[0]}
        try:
            import torch
            env["torch_version"] = torch.__version__
            env["cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                env["cuda_version"] = torch.version.cuda
                env["gpu_name"] = torch.cuda.get_device_name(0)
        except ImportError:
            env["torch_version"] = None
        try:
            import transformers
            env["transformers_version"] = transformers.__version__
        except ImportError:
            env["transformers_version"] = None
        try:
            import peft
            env["peft_version"] = peft.__version__
        except ImportError:
            env["peft_version"] = None
        try:
            import datasets
            env["datasets_version"] = datasets.__version__
        except ImportError:
            env["datasets_version"] = None
        self.manifest["environment"] = env

    def record_data(self, data_path):
        if not os.path.exists(data_path):
            self.manifest["data"] = {"path": data_path, "exists": False}
            return
        sha256 = hashlib.sha256()
        with open(data_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        count = 0
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                for _ in f:
                    count += 1
        except Exception:
            pass
        self.manifest["data"] = {
            "path": os.path.basename(data_path),
            "size_bytes": os.path.getsize(data_path),
            "sha256": sha256.hexdigest(),
            "num_samples": count,
        }

    def record_benchmark(self, benchmark_path):
        if not os.path.exists(benchmark_path):
            return
        sha256 = hashlib.sha256()
        with open(benchmark_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        self.manifest["benchmark"] = {
            "path": os.path.basename(benchmark_path),
            "sha256": sha256.hexdigest(),
        }

    def record_config(self, **kwargs):
        self.manifest["training_config"] = kwargs

    def record_result(self, **kwargs):
        self.manifest["result"] = kwargs

    def finalize(self, output_dir):
        self.manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "training_manifest.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, ensure_ascii=False, indent=2)
        print(f"✅ Training manifest saved to {out_path}")
        return out_path


# ========== 全局便捷接口 ==========
_current = None

def start_run():
    global _current
    _current = TrainingManifest()
    _current.record_environment()
    print(f"🚀 Training run started: {_current.run_id}")
    return _current

def current():
    if _current is None:
        raise RuntimeError("No active run. Call start_run() first.")
    return _current

def finalize(output_dir):
    if _current is None:
        raise RuntimeError("No active run. Call start_run() first.")
    return _current.finalize(output_dir)