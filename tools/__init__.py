"""
工具管理模块 - 统一管理所有Agent工具
所有工具在此注册，所有Agent共享同一个Toolkit实例
"""
from typing import Dict, List, Optional, Callable, Any, Literal
import logging
import os
import json
from agentscope.tool import Toolkit

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
TOOLS_CONFIG_FILE = os.path.join(CONFIG_DIR, "tools_config.json")


class ToolRegistry:
    """
    全局工具注册中心（单例模式）
    """

    _instance = None
    _toolkit: Optional[Toolkit] = None
    _tools_config: Dict[str, bool] = {}  # 工具启用状态配置
    _tools_meta: Dict[str, Any] = {}  # 工具元数据

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._toolkit = Toolkit()
        self._load_config()  # 先加载配置
        self._load_builtin_tools()

    def _load_config(self):
        """从配置文件加载工具配置"""
        try:
            if os.path.exists(TOOLS_CONFIG_FILE):
                with open(TOOLS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._tools_config = config.get('tools', {})
                    logger.info(f"✅ 从配置文件加载了 {len(self._tools_config)} 个工具配置")
            else:
                logger.info("📝 工具配置文件不存在，将使用默认配置")
                self._tools_config = {}
        except Exception as e:
            logger.warning(f"⚠️ 加载工具配置失败: {e}")
            self._tools_config = {}

    def save_config(self):
        """保存工具配置到文件"""
        try:
            # 确保配置目录存在
            os.makedirs(CONFIG_DIR, exist_ok=True)

            config = {
                'tools': self._tools_config
            }

            with open(TOOLS_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ 工具配置已保存到 {TOOLS_CONFIG_FILE}")
            return True
        except Exception as e:
            logger.error(f"❌ 保存工具配置失败: {e}")
            return False

    def _load_builtin_tools(self):
        """加载内置工具"""
        from .builtin import file_io, browser_control

        # 注册文件操作工具（使用配置中的启用状态，默认为True）
        self.register_tool("read_file", file_io.read_file,
                          enabled=self._tools_config.get('read_file', True))
        self.register_tool("write_file", file_io.write_file,
                          enabled=self._tools_config.get('write_file', True))
        self.register_tool("edit_file", file_io.edit_file,
                          enabled=self._tools_config.get('edit_file', True))
        self.register_tool("append_file", file_io.append_file,
                          enabled=self._tools_config.get('append_file', True))

        # 注册浏览器工具
        self.register_tool("browser_use", browser_control.browser_use,
                          enabled=self._tools_config.get('browser_use', True))

        logger.info(f"✅ 已注册 {len(self._toolkit.tools)} 个工具")

    def register_tool(
        self,
        name: str,
        tool_func: Callable,
        enabled: bool = True,
        namesake_strategy: str = "skip"
    ) -> bool:
        """
        注册工具到Toolkit

        Args:
            name: 工具名称
            tool_func: 工具函数
            enabled: 是否启用
            namesake_strategy: 同名处理策略 (override/skip/raise/rename)

        Returns:
            是否注册成功
        """
        if not enabled:
            self._tools_config[name] = False
            logger.debug(f"工具 {name} 已禁用，跳过注册")
            return False

        try:
            self._toolkit.register_tool_function(
                tool_func,
                namesake_strategy=namesake_strategy
            )
            self._tools_config[name] = True
            logger.debug(f"✅ 注册工具: {name}")
            return True
        except Exception as e:
            logger.error(f"❌ 注册工具 {name} 失败: {e}")
            return False

    def get_toolkit(self) -> Toolkit:
        """获取全局Toolkit实例"""
        return self._toolkit

    def list_tools(self) -> List[str]:
        """获取所有可用工具列表（包括已禁用的）"""
        # 返回所有已知工具，包括已注册的和配置中有的
        all_tools = set(self._toolkit.tools.keys())
        all_tools.update(self._tools_config.keys())

        # 如果配置为空，返回默认工具列表
        if not all_tools:
            return ["read_file", "write_file", "edit_file", "append_file", "browser_use"]

        return sorted(list(all_tools))

    def is_tool_enabled(self, name: str) -> bool:
        """检查工具是否启用"""
        return self._tools_config.get(name, True)

    def enable_tool(self, name: str):
        """启用工具 - 动态注册到 Toolkit"""
        self._tools_config[name] = True

        # 如果工具未在 Toolkit 中，则重新注册
        if name not in self._toolkit.tools:
            self._re_register_tool(name)
            logger.info(f"✅ 工具 {name} 已启用并注册到 Toolkit")

    def disable_tool(self, name: str):
        """禁用工具 - 从 Toolkit 移除"""
        self._tools_config[name] = False

        # 从 Toolkit 中移除工具
        if name in self._toolkit.tools:
            del self._toolkit.tools[name]
            logger.info(f"🚫 工具 {name} 已从 Toolkit 移除")

    def _re_register_tool(self, name: str):
        """重新注册工具到 Toolkit"""
        from .builtin import file_io, browser_control

        tool_map = {
            "read_file": file_io.read_file,
            "write_file": file_io.write_file,
            "edit_file": file_io.edit_file,
            "append_file": file_io.append_file,
            "browser_use": browser_control.browser_use,
        }

        if name in tool_map:
            try:
                self._toolkit.register_tool_function(
                    tool_map[name],
                    namesake_strategy="override"
                )
                logger.debug(f"✅ 重新注册工具: {name}")
            except Exception as e:
                logger.error(f"❌ 重新注册工具 {name} 失败: {e}")


# 全局实例
tool_registry = ToolRegistry()

# 便捷导出
get_toolkit = tool_registry.get_toolkit
list_tools = tool_registry.list_tools
