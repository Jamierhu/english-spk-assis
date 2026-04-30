英语口语练习助手


一个简单实用的英语口语练习桌面应用，支持文本朗读、翻译和生词本管理。
功能特性
🔊 语音朗读


支持朗读全部文本或选中文本
可调节语速（50-300）
🌐 翻译功能


英译中：选中英文文本一键翻译
中译英：支持中文翻译成英文
实时显示翻译结果
📚 生词本


双击英文单词自动添加到生词本
自动获取单词释义
支持手动添加生词和例句
生词搜索功能
导出生词到文本文件
SQLite 数据库存储
🤖 AI学习助手


支持在线模型（DeepSeek / Kimi / OpenAI / 硅基流动）
支持本地模型（Ollama）
英语语法解答、词汇讲解、发音指导、写作纠正
预设快速配置，一键切换模型
项目结构


plaintext
english-spk-assis/
├── app/                        # 所有Python源码
│   ├── main.py                 # 程序入口
│   ├── ui_main_window.py       # 主窗口界面类
│   ├── vocabulary_db.py        # 生词本数据库管理
│   ├── translation_service.py  # 翻译服务 + TTS线程 + 音标获取
│   ├── add_word_dialog.py      # 添加生词对话框
│   └── ai_assistant.py         # AI助手服务模块
├── static/                     # 静态资源
│   └── icon.png                # 应用图标
├── data/                       # 数据文件（运行时生成）
├── dist/                       # 构建产物
├── requirements.txt
├── .gitignore
└── README.md

安装步骤
1. 环境要求


Python 3.8 或更高版本
Windows / macOS / Linux
2. 安装依赖


bash
pip install -r requirements.txt

3. 运行程序


bash
python app/main.py

打包成 Windows 应用


bash
pyinstaller --onefile --windowed --name "英语口语练习助手" --add-data "static;static" app/main.py



输出文件：dist/英语口语练习助手.exe
使用指南


语音朗读 — 输入或导入英文文本，点击「🔊 朗读」，有选中朗读选中，无选中朗读全部
翻译 — 点击「翻译（英→中）」或「翻译（中→英）」，同理有选中翻译选中，无选中翻译全部
生词本 — 双击文本中的英文单词自动添加，也可手动添加
AI助手 — 切换到「💬 AI助手」标签页，点击 ⚙️ 设置配置模型后即可使用
技术栈


GUI：PyQt5
语音合成：Edge-TTS
翻译：translate 库
音标：有道词典开放API
AI助手：OpenAI SDK（兼容 DeepSeek / Kimi / Ollama 等）
数据库：SQLite


本项目仅供学习和个人使用。