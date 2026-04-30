# -*- coding: utf-8 -*-
"""
AI助手服务模块
支持在线API（DeepSeek/Kimi/OpenAI等）和本地Ollama
"""

import json
import os
from openai import OpenAI
from PyQt5.QtCore import QThread, pyqtSignal


# 英语学习系统提示词
ENGLISH_LEARNING_SYSTEM_PROMPT = """你是一位专业的英语学习助手，名叫"English AI Tutor"。你的专长包括：

1. **语法解答**：解释英语语法规则，分析句式结构
2. **词汇讲解**：讲解单词用法、短语搭配、近义词辨析
3. **发音指导**：提供单词和句子的发音技巧（IPA音标）
4. **写作纠正**：批改英语作文，指出错误并给出修改建议
5. **翻译协助**：中英互译，提供多种翻译版本及适用场景
6. **学习建议**：根据用户水平提供个性化的英语学习建议
7. **练习生成**：生成英语练习题，如填空、改错、翻译等
8. **例句提供**：提供地道的英语例句，帮助理解词汇和语法

请用友好、专业的方式回复。如果用户的问题涉及中文，你可以用中文解释，但示例和重点内容用英文呈现。
始终鼓励用户学习，指出他们的进步。"""


# 预设API配置列表
PRESET_CONFIGS = {
    "DeepSeek": {
        "mode": "online",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key": ""
    },
    "Kimi（月之暗面）": {
        "mode": "online",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "api_key": ""
    },
    "OpenAI": {
        "mode": "online",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "api_key": ""
    },
    "Ollama（本地）": {
        "mode": "local",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3",
        "api_key": "ollama"
    },
    "硅基流动": {
        "mode": "online",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "api_key": ""
    }
}


class AIAssistant:
    """AI助手服务类"""
    
    def __init__(self):
        self.config_file = self._get_config_path()
        self.config = self._load_config()
        self.client = None
        self._init_client()
    
    def _get_config_path(self):
        """获取配置文件路径"""
        # 优先使用用户目录
        if os.name == 'nt':  # Windows
            config_dir = os.path.join(os.environ.get('APPDATA', ''), 'EnglishPracticeApp')
        else:  # macOS/Linux
            config_dir = os.path.expanduser('~/.config/EnglishPracticeApp')
        
        # 确保目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        return os.path.join(config_dir, 'ai_config.json')
    
    def _load_config(self):
        """加载配置"""
        default_config = {
            "mode": "online",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "api_key": "",
            "system_prompt": ENGLISH_LEARNING_SYSTEM_PROMPT
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并配置，确保有默认值
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception:
                return default_config
        return default_config
    
    def _save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存AI配置失败: {e}")
    
    def _init_client(self):
        """初始化OpenAI客户端"""
        try:
            # 如果是本地模式（Ollama），api_key设为空或任意值
            api_key = self.config.get("api_key", "")
            if not api_key and self.config.get("mode") == "local":
                api_key = "ollama"
            
            self.client = OpenAI(
                base_url=self.config.get("base_url", ""),
                api_key=api_key if api_key else "ollama"
            )
        except Exception as e:
            print(f"初始化AI客户端失败: {e}")
            self.client = None
    
    def update_config(self, mode, base_url, model, api_key):
        """更新配置"""
        self.config["mode"] = mode
        self.config["base_url"] = base_url
        self.config["model"] = model
        self.config["api_key"] = api_key
        self._save_config()
        self._init_client()
    
    def update_system_prompt(self, prompt):
        """更新系统提示词"""
        self.config["system_prompt"] = prompt
        self._save_config()
    
    def get_config(self):
        """获取当前配置"""
        return self.config.copy()
    
    def chat(self, message, history=None):
        """
        发送聊天请求
        
        Args:
            message: 用户消息
            history: 聊天历史 [(role, content), ...]
        
        Returns:
            AI回复内容
        """
        if not self.client:
            return "AI客户端未初始化，请检查配置。"
        
        # 构建消息列表
        messages = []
        
        # 添加系统提示词
        system_prompt = self.config.get("system_prompt", ENGLISH_LEARNING_SYSTEM_PROMPT)
        messages.append({"role": "system", "content": system_prompt})
        
        # 添加聊天历史
        if history:
            for role, content in history:
                messages.append({"role": role, "content": content})
        
        # 添加当前消息
        messages.append({"role": "user", "content": message})
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.get("model", "gpt-4o-mini"),
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            if "api_key" in error_msg.lower() or "auth" in error_msg.lower():
                return "API密钥错误或未设置，请检查AI设置。"
            elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                return "无法连接到AI服务，请检查网络连接和API地址。"
            elif "model" in error_msg.lower():
                return "模型不存在或不支持，请检查模型名称是否正确。"
            else:
                return f"AI请求失败: {error_msg}"
    
    def test_connection(self):
        """测试AI连接"""
        if not self.client:
            return False, "AI客户端未初始化"
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.get("model", "gpt-4o-mini"),
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10
            )
            return True, "连接成功！"
        except Exception as e:
            return False, f"连接失败: {str(e)}"
    
    def get_preset_configs(self):
        """获取预设配置列表"""
        return PRESET_CONFIGS.copy()


class AIWorker(QThread):
    """AI工作线程 - 异步处理AI请求"""
    
    finished = pyqtSignal(str)  # 完成信号，返回AI回复
    error = pyqtSignal(str)  # 错误信号
    
    def __init__(self, ai_assistant, message, history=None):
        super().__init__()
        self.ai_assistant = ai_assistant
        self.message = message
        self.history = history or []
    
    def run(self):
        """执行AI请求"""
        try:
            # 添加用户消息到历史
            self.history.append(("user", self.message))
            
            # 调用AI
            reply = self.ai_assistant.chat(self.message, self.history)
            
            # 添加AI回复到历史
            self.history.append(("assistant", reply))
            
            self.finished.emit(reply)
        except Exception as e:
            self.error.emit(str(e))
