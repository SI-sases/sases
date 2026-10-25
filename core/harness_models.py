from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class ModuleManifest(BaseModel):
    """Harness 模块清单，定义在模块目录的 manifest.json 中"""
    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    capabilities: List[str] = []
    permissions: List[str] = []
    entrypoint: str = "main.py"
    icon: Optional[str] = None
    node_type: str = "harness"
    aliases: List[str] = []
    params: Dict[str, Any] = {}
    cost: Dict[str, Any] = {}

class ToolDefinition(BaseModel):
    """工具定义，用于返回给调用方"""
    module_id: str
    name: str
    description: str
    capabilities: List[str]
    permissions: List[str]
    version: str
    node_type: str
    aliases: List[str] = []
    params: Dict[str, Any] = {}
    cost: Dict[str, Any] = {}

class ToolInvokeRequest(BaseModel):
    """调用工具请求体"""
    module_id: str
    params: Dict[str, Any] = {}

class ToolInvokeResponse(BaseModel):
    """调用工具响应体"""
    module_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    error: Optional[str] = None
