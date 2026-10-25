import os
import sys
import base64
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import seed_utils, config

def test_image_size_limit(monkeypatch):
    monkeypatch.setattr(config, "MAX_IMAGE_SIZE", 10)
    image = base64.b64encode(b"0123456789abcdef").decode()
    with pytest.raises(ValueError):
        seed_utils.call_chat("test", image_base64=image)

def test_image_message_format(monkeypatch):
    image_base64 = base64.b64encode(b"fakeimage").decode()
    # 模拟默认客户端，避免真实 API 调用
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "mock response"
    mock_completions = MagicMock()
    mock_completions.create.return_value = mock_response
    mock_chat = MagicMock()
    mock_chat.completions = mock_completions
    mock_client = MagicMock()
    mock_client.chat = mock_chat
    # 替换模块中的 _client
    monkeypatch.setattr(seed_utils, "_client", mock_client)
    result = seed_utils.call_chat("描述图片", image_base64=image_base64)
    assert result == "mock response"
    # 检查调用参数中包含图片
    args, kwargs = mock_completions.create.call_args
    messages = kwargs.get("messages") or args[0].get("messages")
    assert messages[0]["content"][1]["type"] == "image_url"
