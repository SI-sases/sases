# core/services/local_embedding.py
import os
import numpy as np
try:
    import onnxruntime as ort
    from transformers import AutoTokenizer
except ImportError:
    ort = None
    AutoTokenizer = None
    print("[LocalEmbedding] Missing deps, fallback to API mode")



class LocalEmbedding:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_dir="./bge-small-zh-onnx"):
        if LocalEmbedding._initialized:
            return
        self.model_dir = model_dir
        self.tokenizer = None
        self.session = None
        self._input_names = None
        self._load()
        LocalEmbedding._initialized = True

    def _load(self):
        if not os.path.exists(self.model_dir):
            raise FileNotFoundError(f"模型目录不存在: {self.model_dir}")

        onnx_path = os.path.join(self.model_dir, "onnx", "model_int8.onnx")
        if not os.path.exists(onnx_path):
            # 兼容非量化文件名
            alt_path = os.path.join(self.model_dir, "onnx", "model.onnx")
            if os.path.exists(alt_path):
                onnx_path = alt_path
            else:
                raise FileNotFoundError(f"ONNX 模型文件不存在: {onnx_path}")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
        _opts = ort.SessionOptions()
        _opts.intra_op_num_threads = 1
        _opts.inter_op_num_threads = 1
        _opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(
            onnx_path,
            sess_options=_opts,
            providers=['CPUExecutionProvider']
        )
        # 记录模型期望的输入名
        self._input_names = [i.name for i in self.session.get_inputs()]
        print(f"[本地Embedding] 模型输入: {self._input_names}")

    def get_embedding(self, text: str) -> np.ndarray:
        """获取文本的向量表示，返回 shape (1, dim) 的 numpy 数组"""
        inputs = self.tokenizer(
            text,
            return_tensors="np",
            padding=True,
            truncation=True,
            max_length=512
        )

        # 根据模型期望的输入名动态构建 feed
        feed = {}
        for name in self._input_names:
            if name in inputs:
                feed[name] = inputs[name].astype(np.int64)
            elif name == "token_type_ids":
                # 有些模型需要 token_type_ids，但 tokenizer 可能没返回，手动补全
                feed[name] = np.zeros_like(inputs["input_ids"], dtype=np.int64)
            else:
                raise ValueError(f"模型需要输入 {name}，但 tokenizer 未提供")

        outputs = self.session.run(None, feed)

        # 取 [CLS] token 的输出作为句向量，并做 L2 归一化
        embedding = outputs[0][:, 0, :]
        embedding = embedding / np.linalg.norm(embedding, axis=1, keepdims=True)
        return embedding

    def compute_similarity(self, text1: str, text2: str) -> float:
        vec1 = self.get_embedding(text1)
        vec2 = self.get_embedding(text2)
        return float(np.dot(vec1, vec2.T)[0][0])
