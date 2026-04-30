# -*- coding: utf-8 -*-
"""
主窗口界面类
"""

import sys
import os
import markdown
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTextEdit, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QGroupBox, QLineEdit, QFileDialog, QMessageBox, QSplitter,
    QSlider, QTextBrowser, QDialog, QTabWidget, QRadioButton,
    QButtonGroup, QComboBox, QApplication, QFormLayout, QScrollArea
)
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QTextCursor, QIcon, QPalette, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

from vocabulary_db import VocabularyDB
from translation_service import TranslationService, TTSWorker, fetch_phonetic
from add_word_dialog import AddWordDialog
from ai_assistant import AIAssistant, AIWorker


def resource_path(relative_path):
    """获取资源文件的绝对路径（兼容PyInstaller打包）"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except AttributeError:
        # 未打包时使用脚本所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


class MainWindowUI(QMainWindow):
    """主窗口界面类"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化服务
        self.db = VocabularyDB()
        self.media_player = QMediaPlayer()
        self.tts_thread = None
        self.translator = TranslationService()
        
        # AI助手相关初始化
        self.ai_assistant = AIAssistant()
        self.ai_thread = None
        self.ai_history = []  # 聊天历史（仅内存中）
        self.ai_configured = self._check_ai_configured()
        
        # 初始化界面
        self.init_ui()
        
        # 加载数据
        self.load_vocabulary_list()
    
    def _check_ai_configured(self):
        """检查AI是否已配置"""
        config = self.ai_assistant.get_config()
        if config.get("mode") == "local":
            return True
        return bool(config.get("api_key"))
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("英语口语练习助手")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置窗口图标
        icon_path = resource_path(os.path.join("images", "icon.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 主部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # ===== 左侧：练习区域 =====
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # ===== 右侧：生词本 + AI助手 =====
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        # 设置样式
        self._apply_style()
    
    def _create_left_panel(self):
        """创建左侧面板"""
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 文本编辑区 - 占主要空间
        left_layout.addWidget(self._create_text_group(), stretch=3)
        
        # 控制面板 - 固定高度
        left_layout.addWidget(self._create_control_group(), stretch=0)
        
        # 翻译区域 - 占较少空间但可随窗口放大
        left_layout.addWidget(self._create_translation_group(), stretch=1)
        
        return left_panel
    
    def _create_text_group(self):
        """创建文本编辑区"""
        text_group = QGroupBox("英文文本区")
        text_layout = QVBoxLayout(text_group)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        btn_open = QPushButton("📂 打开文件")
        btn_open.clicked.connect(self.open_file)
        toolbar.addWidget(btn_open)
        
        btn_clear = QPushButton("🗑️ 清空")
        btn_clear.clicked.connect(lambda: self.text_editor.clear())
        toolbar.addWidget(btn_clear)
        
        toolbar.addStretch()
        text_layout.addLayout(toolbar)
        
        # 文本编辑器
        self.text_editor = QTextEdit()
        self.text_editor.setFont(QFont("Consolas", 12))
        self.text_editor.setPlaceholderText(
            "在这里输入或粘贴英文文本...\n\n提示：\n"
            "- 选中文字后点击'朗读选中'可播放语音\n"
            "- 双击单词可添加到生词本"
        )
        self.text_editor.mouseDoubleClickEvent = self._on_double_click
        text_layout.addWidget(self.text_editor)
        
        return text_group
    
    def _create_control_group(self):
        """创建朗读控制区"""
        control_group = QGroupBox("朗读控制")
        control_layout = QHBoxLayout(control_group)
        
        btn_read = QPushButton("🔊 朗读")
        btn_read.clicked.connect(self.read_text)
        control_layout.addWidget(btn_read)
        
        btn_stop = QPushButton("⏹️ 停止")
        btn_stop.clicked.connect(self.stop_reading)
        control_layout.addWidget(btn_stop)
        
        # 语速调节
        control_layout.addWidget(QLabel("语速:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(50)
        self.speed_slider.setMaximum(300)
        self.speed_slider.setValue(150)
        control_layout.addWidget(self.speed_slider)
        
        return control_group
    
    def _create_translation_group(self):
        """创建翻译区域"""
        trans_group = QGroupBox("翻译对照")
        trans_layout = QVBoxLayout(trans_group)
        
        # 翻译按钮
        trans_toolbar = QHBoxLayout()
        
        btn_trans = QPushButton("🌐 翻译（英→中）")
        btn_trans.clicked.connect(self.translate_en_to_zh)
        trans_toolbar.addWidget(btn_trans)
        
        btn_trans_en = QPushButton("🌐 翻译（中→英）")
        btn_trans_en.clicked.connect(self.translate_zh_to_en)
        trans_toolbar.addWidget(btn_trans_en)
        
        trans_toolbar.addStretch()
        trans_layout.addLayout(trans_toolbar)
        
        # 翻译显示区
        self.translation_display = QTextBrowser()
        self.translation_display.setFont(QFont("Microsoft YaHei", 11))
        # 不设固定高度，随窗口自适应
        trans_layout.addWidget(self.translation_display)
        
        return trans_group
    
    def _create_right_panel(self):
        """创建右侧面板（生词本 + AI助手）"""
        # 使用QTabWidget替代原来的单一面板
        right_tabs = QTabWidget()
        
        # Tab1: 生词本
        vocab_panel = self._create_vocab_panel()
        right_tabs.addTab(vocab_panel, "📚 生词本")
        
        # Tab2: AI助手
        ai_panel = self._create_ai_tab()
        right_tabs.addTab(ai_panel, "💬 AI助手")
        
        return right_tabs
    
    def _create_vocab_panel(self):
        """创建生词本面板"""
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        vocab_group = QGroupBox("📚 生词本")
        vocab_layout = QVBoxLayout(vocab_group)
        
        # 搜索栏
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索单词...")
        self.search_input.textChanged.connect(self.search_vocabulary)
        search_layout.addWidget(self.search_input)
        
        btn_export = QPushButton("📤 导出")
        btn_export.clicked.connect(self.export_vocabulary)
        search_layout.addWidget(btn_export)
        vocab_layout.addLayout(search_layout)
        
        # 生词列表
        self.vocab_list = QListWidget()
        self.vocab_list.setFont(QFont("Microsoft YaHei", 10))
        self.vocab_list.itemDoubleClicked.connect(self.show_word_detail)
        vocab_layout.addWidget(self.vocab_list)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_delete = QPushButton("🗑️ 删除选中")
        btn_delete.clicked.connect(self.delete_selected_word)
        btn_layout.addWidget(btn_delete)
        
        btn_add_manual = QPushButton("➕ 手动添加")
        btn_add_manual.clicked.connect(self.add_word_manual)
        btn_layout.addWidget(btn_add_manual)
        vocab_layout.addLayout(btn_layout)
        
        # 统计信息
        self.stats_label = QLabel("共 0 个生词")
        vocab_layout.addWidget(self.stats_label)
        
        right_layout.addWidget(vocab_group)
        
        return right_panel
    
    def _create_ai_tab(self):
        """创建AI助手聊天界面"""
        ai_panel = QWidget()
        ai_layout = QVBoxLayout(ai_panel)
        ai_layout.setContentsMargins(5, 5, 5, 5)
        
        # ===== 顶部：模式指示 + 设置按钮 =====
        header_layout = QHBoxLayout()
        
        # 模式指示标签
        self.ai_mode_label = QLabel()
        self._update_ai_mode_label()
        self.ai_mode_label.setStyleSheet("""
            QLabel {
                font-family: "等线";
                font-size: 22px;
                padding: 4px 10px;
                border-radius: 12px;
                background-color: rgba(74, 154, 232, 30);
                color: #2C5A8E;
            }
        """)
        header_layout.addWidget(self.ai_mode_label)
        
        header_layout.addStretch()
        
        # 清空记录按钮
        btn_clear_history = QPushButton("🗑️ 清空记录")
        #btn_clear_history.setFixedSize(100, 32)
        btn_clear_history.clicked.connect(self._clear_ai_history)
        header_layout.addWidget(btn_clear_history)
        
        # 设置按钮
        btn_settings = QPushButton("⚙️ 设置")
        #btn_settings.setFixedSize(70, 32)
        btn_settings.clicked.connect(self._open_ai_settings)
        header_layout.addWidget(btn_settings)
        
        ai_layout.addLayout(header_layout)
        
        # ===== 中间：聊天记录区域 =====
        self.ai_chat_browser = QTextBrowser()
        self.ai_chat_browser.setFont(QFont("Microsoft YaHei", 13))
        self.ai_chat_browser.setOpenExternalLinks(False)
        self._show_ai_welcome()
        ai_layout.addWidget(self.ai_chat_browser)
        
        # ===== 底部：输入区域 =====
        input_layout = QHBoxLayout()
        
        self.ai_input = QLineEdit()
        self.ai_input.setFont(QFont("Microsoft YaHei", 13))
        self.ai_input.setPlaceholderText("输入问题，Shift+Enter换行，Enter发送...")
        self.ai_input.returnPressed.connect(self._on_ai_input_return)
        input_layout.addWidget(self.ai_input)
        
        self.ai_send_btn = QPushButton("发送")
        #self.ai_send_btn.setFixedSize(70, 36)
        self.ai_send_btn.clicked.connect(self._send_ai_message)
        input_layout.addWidget(self.ai_send_btn)
        
        ai_layout.addLayout(input_layout)
        
        return ai_panel
    
    def _update_ai_mode_label(self):
        """更新AI模式标签"""
        config = self.ai_assistant.get_config()
        mode = config.get("mode", "online")
        if mode == "local":
            mode_text = "🔗 本地模式 (Ollama)"
        else:
            mode_text = "🌐 在线模式"
        
        model = config.get("model", "")
        self.ai_mode_label.setText(f"{mode_text} | {model}")
    
    def _show_ai_welcome(self):
        """显示AI助手欢迎信息"""
        if self.ai_configured:
            welcome_html = """
            <div style="text-align: center; padding: 30px 20px; color: #666;">
                <h2 style="color: #4A9AE8; margin-bottom: 15px;">🤖 欢迎使用AI英语学习助手</h2>
                <p style="line-height: 1.8; font-size: 22px;">
                    我可以帮你：<br>
                    📝 解答英语语法问题<br>
                    📖 讲解词汇用法<br>
                    ✍️ 纠正写作错误<br>
                    🗣️ 提供发音指导<br>
                    💡 制定学习计划<br><br>
                    <span style="color: #999;">请在下方输入你的问题，开始学习吧！</span>
                </p>
            </div>
            """
        else:
            welcome_html = """
            <div style="text-align: center; padding: 30px 20px; color: #666;">
                <h2 style="color: #4A9AE8; margin-bottom: 15px;">⚠️ AI助手未配置</h2>
                <p style="line-height: 1.8; font-size: 20px;">
                    请先点击右上角<strong>⚙️ 设置</strong>按钮<br>
                    配置AI服务（支持DeepSeek、Kimi、OpenAI、Ollama等）<br><br>
                    <span style="color: #999;">配置完成后即可开始AI辅助学习</span>
                </p>
            </div>
            """
        self.ai_chat_browser.setHtml(welcome_html)
    
    def _create_ai_settings_dialog(self):
        """创建AI设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("AI助手设置")
        #dialog.setFixedSize(480, 420)
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        
        # ===== 模式选择 =====
        mode_group = QGroupBox("连接模式")
        mode_layout = QHBoxLayout(mode_group)
        
        self.online_radio = QRadioButton("🌐 在线模式")
        self.local_radio = QRadioButton("🔗 本地模式 (Ollama)")
        mode_layout.addWidget(self.online_radio)
        mode_layout.addWidget(self.local_radio)
        mode_layout.addStretch()
        
        # 默认选中
        config = self.ai_assistant.get_config()
        if config.get("mode") == "local":
            self.local_radio.setChecked(True)
        else:
            self.online_radio.setChecked(True)
        
        layout.addWidget(mode_group)
        
        # ===== 预设配置选择 =====
        preset_group = QGroupBox("快速配置")
        preset_layout = QHBoxLayout(preset_group)
        
        preset_layout.addWidget(QLabel("预设:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.ai_assistant.get_preset_configs().keys()))
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        
        layout.addWidget(preset_group)
        
        # ===== API配置表单 =====
        form_group = QGroupBox("API配置")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)
        
        # API Key
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("输入API Key（在线模式必填）")
        form_layout.addRow("API Key:", self.api_key_input)
        
        # Base URL
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("例如: https://api.deepseek.com/v1")
        form_layout.addRow("Base URL:", self.base_url_input)
        
        # Model
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("例如: deepseek-chat, gpt-4o-mini, llama3")
        form_layout.addRow("Model:", self.model_input)
        
        layout.addWidget(form_group)
        
        # 连接测试按钮
        btn_test = QPushButton("🔌 测试连接")
        btn_test.clicked.connect(lambda: self._test_ai_connection(dialog))
        layout.addWidget(btn_test)
        
        # ===== 按钮区域 =====
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_save = QPushButton("💾 保存")
        btn_save.clicked.connect(lambda: self._save_ai_settings(dialog))
        btn_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
        
        # 加载当前配置
        self._load_current_ai_settings()
        
        # 连接模式切换事件
        self.online_radio.toggled.connect(self._on_mode_changed)
        self.local_radio.toggled.connect(self._on_mode_changed)
        self._on_mode_changed()  # 初始化状态
        
        return dialog
    
    def _load_current_ai_settings(self):
        """加载当前AI配置到表单"""
        config = self.ai_assistant.get_config()
        
        self.api_key_input.setText(config.get("api_key", ""))
        self.base_url_input.setText(config.get("base_url", ""))
        self.model_input.setText(config.get("model", ""))
        
        # 匹配预设
        base_url = config.get("base_url", "")
        presets = self.ai_assistant.get_preset_configs()
        for name, preset in presets.items():
            if preset.get("base_url") == base_url:
                self.preset_combo.setCurrentText(name)
                break
    
    def _on_preset_changed(self, preset_name):
        """预设配置变更"""
        presets = self.ai_assistant.get_preset_configs()
        if preset_name in presets:
            preset = presets[preset_name]
            self.base_url_input.setText(preset.get("base_url", ""))
            self.model_input.setText(preset.get("model", ""))
            
            # 如果是Ollama本地模式，设置默认API Key
            if preset_name == "Ollama（本地）":
                self.api_key_input.setText("ollama")
            else:
                self.api_key_input.clear()
    
    def _on_mode_changed(self):
        """模式切换事件"""
        is_online = self.online_radio.isChecked()
        
        # 在线模式显示API Key输入，本地模式隐藏
        self.api_key_input.setVisible(is_online)
        self.api_key_input.setEnabled(is_online)
        
        # 更新预设下拉框
        self.preset_combo.model().item(3).setEnabled(True)  # Ollama始终可选
        
        if is_online:
            self.preset_combo.setCurrentText("DeepSeek")
        else:
            self.preset_combo.setCurrentText("Ollama（本地）")
    
    def _open_ai_settings(self):
        """打开AI设置对话框"""
        dialog = self._create_ai_settings_dialog()
        dialog.exec_()
    
    def _test_ai_connection(self, dialog=None):
        """测试AI连接"""
        # 先临时保存当前配置
        original_config = self.ai_assistant.get_config().copy()
        
        # 应用测试配置
        mode = "local" if self.local_radio.isChecked() else "online"
        base_url = self.base_url_input.text().strip()
        model = self.model_input.text().strip()
        api_key = self.api_key_input.text().strip() if mode == "online" else "ollama"
        
        # 临时更新配置并测试
        self.ai_assistant.update_config(mode, base_url, model, api_key)
        success, message = self.ai_assistant.test_connection()
        
        # 恢复原配置（用户还需要点保存）
        self.ai_assistant.update_config(
            original_config.get("mode"),
            original_config.get("base_url"),
            original_config.get("model"),
            original_config.get("api_key")
        )
        
        if success:
            QMessageBox.information(dialog or self, "连接测试", f"✅ {message}")
        else:
            QMessageBox.warning(dialog or self, "连接测试", f"❌ {message}")
    
    def _save_ai_settings(self, dialog):
        """保存AI设置"""
        mode = "local" if self.local_radio.isChecked() else "online"
        base_url = self.base_url_input.text().strip()
        model = self.model_input.text().strip()
        api_key = self.api_key_input.text().strip()
        
        # 验证
        if not base_url:
            QMessageBox.warning(dialog, "配置错误", "Base URL不能为空")
            return
        
        if not model:
            QMessageBox.warning(dialog, "配置错误", "Model不能为空")
            return
        
        if mode == "online" and not api_key:
            QMessageBox.warning(dialog, "配置错误", "在线模式需要填写API Key")
            return
        
        # 保存配置
        self.ai_assistant.update_config(mode, base_url, model, api_key)
        
        # 更新状态
        self.ai_configured = True
        self._update_ai_mode_label()
        self._show_ai_welcome()
        
        QMessageBox.information(dialog, "保存成功", "AI设置已保存！")
        dialog.accept()
    
    def _on_ai_input_return(self):
        """AI输入框回车事件"""
        # 如果Shift被按下，不发送
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.ShiftModifier:
            return
        self._send_ai_message()
    
    def _send_ai_message(self):
        """发送AI消息"""
        message = self.ai_input.text().strip()
        
        if not message:
            return
        
        if not self.ai_configured:
            QMessageBox.information(self, "提示", "请先在设置中配置AI服务")
            return
        
        # 显示用户消息
        self._add_user_message(message)
        
        # 清空输入框
        self.ai_input.clear()
        
        # 禁用发送按钮
        self.ai_send_btn.setEnabled(False)
        self.ai_input.setEnabled(False)
        
        # 创建并启动AI工作线程
        self.ai_thread = AIWorker(self.ai_assistant, message, self.ai_history.copy())
        self.ai_thread.finished.connect(self._on_ai_reply)
        self.ai_thread.error.connect(self._on_ai_error)
        self.ai_thread.start()
    
    def _add_user_message(self, message):
        """添加用户消息到聊天区域"""
        html = f"""
        <div style="text-align: right; margin: 10px 5px;">
            <span style="display: inline-block; background-color: #4A9AE8; 
                         color: white; padding: 10px 15px; border-radius: 15px 15px 3px 15px;
                         max-width: 80%; word-wrap: break-word; font-size: 22px;">
                {message}
            </span>
        </div>
        """
        self.ai_chat_browser.append(html)
        self.ai_chat_browser.verticalScrollBar().setValue(
            self.ai_chat_browser.verticalScrollBar().maximum()
        )
    
    def _add_ai_message(self, message):
        """添加AI消息到聊天区域"""
        # Markdown转HTML
        try:
            html_content = markdown.markdown(
                message,
                extensions=['fenced_code', 'codehilite', 'tables', 'nl2br']
            )
        except Exception:
            html_content = message.replace('\n', '<br>')
        
        html = f"""
        <div style="text-align: left; margin: 10px 5px;">
            <span style="display: inline-block; background-color: #FFFFFF; 
                         color: #1E3A5F; padding: 10px 15px; border-radius: 15px 15px 15px 3px;
                         max-width: 80%; word-wrap: break-word; font-size: 22px;
                         border: 1px solid #E0E0E0;">
                🤖 {html_content}
            </span>
        </div>
        """
        self.ai_chat_browser.append(html)
        self.ai_chat_browser.verticalScrollBar().setValue(
            self.ai_chat_browser.verticalScrollBar().maximum()
        )
    
    def _on_ai_reply(self, reply):
        """AI回复接收"""
        # 更新历史
        self.ai_history = self.ai_thread.history if self.ai_thread else self.ai_history
        
        # 显示AI回复
        self._add_ai_message(reply)
        
        # 恢复UI
        self.ai_send_btn.setEnabled(True)
        self.ai_input.setEnabled(True)
        self.ai_input.setFocus()
        
        # 清理线程
        if self.ai_thread:
            self.ai_thread.deleteLater()
            self.ai_thread = None
    
    def _on_ai_error(self, error_msg):
        """AI错误处理"""
        self._add_ai_message(f"❌ 发生错误: {error_msg}")
        
        # 恢复UI
        self.ai_send_btn.setEnabled(True)
        self.ai_input.setEnabled(True)
        self.ai_input.setFocus()
        
        # 清理线程
        if self.ai_thread:
            self.ai_thread.deleteLater()
            self.ai_thread = None
    
    def _clear_ai_history(self):
        """清空聊天记录"""
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有聊天记录吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.ai_history.clear()
            self._show_ai_welcome()
    
    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #E3F2FD, stop:0.4 #E8F0FE,
                    stop:0.7 #E0ECFA, stop:1 #EBF2FA
                );
            }
            QGroupBox {
                font-weight: bold;
                font-family: "等线";
                font-size: 23px;
                border: 1px solid rgba(120, 160, 200, 0.3);
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 12px;
                background-color: rgba(255, 255, 255, 230);
                color: #2C4A6E;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 23px;
                padding: 0 6px;
                color: #3D7EC7;
            }
            QPushButton {
                font-family: "等线";
                font-size: 20px;
                padding: 9px 20px;
                border-radius: 6px;
                background-color: #4A9AE8;
                color: #FFFFFF;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3A8AD8;
            }
            QPushButton:pressed {
                background-color: #2A7AC8;
            }
            QPushButton:disabled {
                background-color: #A0C0E0;
            }
            QTextEdit, QTextBrowser {
                font-family: "等线";
                font-size: 22px;
                border: 1px solid rgba(120, 160, 200, 0.3);
                border-radius: 8px;
                padding: 8px;
                background-color: rgba(255, 255, 255, 240);
                color: #1E3A5F;
                selection-background-color: #4A9AE8;
                selection-color: white;
            }
            QLineEdit {
                font-family: "等线";
                font-size: 22px;
                border: 1px solid rgba(120, 160, 200, 0.3);
                border-radius: 6px;
                padding: 6px 10px;
                background-color: rgba(255, 255, 255, 240);
                color: #1E3A5F;
            }
            QLineEdit:focus {
                border: 1px solid #4A9AE8;
            }
            QSlider::groove:horizontal {
                height: 6px;
                border-radius: 3px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B8D8F0, stop:1 #90C0E0
                );
            }
            QSlider::handle:horizontal {
                background-color: #4A9AE8;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #3A8AD8;
            }
            QListWidget {
                font-family: "等线";
                font-size: 20px;
                border: 1px solid rgba(120, 160, 200, 0.3);
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 240);
                color: #1E3A5F;
            }
            QListWidget::item {
                padding: 7px;
                border-bottom: 1px solid rgba(120, 160, 200, 0.15);
            }
            QListWidget::item:selected {
                background-color: rgba(74, 154, 232, 40);
                color: #2C5A8E;
            }
            QListWidget::item:hover {
                background-color: rgba(74, 154, 232, 20);
            }
            QLabel {
                font-family: "等线";
                font-size: 22px;
                color: #2C4A6E;
            }
            /* QTabWidget 样式 */
            QTabWidget::pane {
                border: 1px solid rgba(120, 160, 200, 0.3);
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 230);
            }
            QTabBar::tab {
                font-family: "等线";
                font-size: 20px;
                padding: 10px 28px;
                margin-right: 2px;
                background-color: rgba(200, 220, 240, 150);
                color: #2C4A6E;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background-color: rgba(255, 255, 255, 240);
                color: #4A9AE8;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: rgba(74, 154, 232, 40);
            }
            /* QRadioButton 样式 */
            QRadioButton {
                font-family: "等线";
                font-size: 20px;
                color: #2C4A6E;
                padding: 4px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid #4A9AE8;
            }
            QRadioButton::indicator:checked {
                background-color: #4A9AE8;
            }
            /* QComboBox 样式 */
            QComboBox {
                font-family: "等线";
                font-size: 20px;
                padding: 6px 12px;
                border: 1px solid rgba(120, 160, 200, 0.3);
                border-radius: 6px;
                background-color: rgba(255, 255, 255, 240);
                color: #1E3A5F;
            }
            QComboBox:hover {
                border: 1px solid #4A9AE8;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #4A9AE8;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                font-family: "等线";
                font-size: 22px;
                border: 1px solid rgba(120, 160, 200, 0.3);
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 250);
                selection-background-color: #4A9AE8;
            }
            /* 对话框样式 */
            QDialog {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #E3F2FD, stop:1 #E8F0FE
                );
            }
            QFormLayout {
                spacing: 10px;
            }
            QFormLayout Label {
                font-family: "等线";
                font-size: 22px;
                color: #2C4A6E;
                min-width: 80px;
            }
        """)
    
    # ==================== 事件处理方法 ====================
    
    def open_file(self):
        """打开文件"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "打开文件", "", 
            "文本文件 (*.txt);;所有文件 (*)"
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.text_editor.setText(content)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法打开文件: {e}")
    
    def read_text(self):
        """朗读文本（有选中朗读选中，无选中朗读全部）"""
        cursor = self.text_editor.textCursor()
        selected_text = cursor.selectedText()
        if selected_text:
            self.start_tts(selected_text)
        else:
            text = self.text_editor.toPlainText()
            if text:
                self.start_tts(text)
            else:
                QMessageBox.information(self, "提示", "文本为空，请先输入或导入文本")
    
    def start_tts(self, text):
        """启动TTS线程"""
        if self.tts_thread and self.tts_thread.isRunning():
            self.tts_thread.quit()
        rate_value = self.speed_slider.value() - 150
        rate_str = f"{rate_value:+d}%"
        self.tts_thread = TTSWorker(text, rate=rate_str)
        self.tts_thread.finished.connect(self.play_audio)
        self.tts_thread.start()
    
    def play_audio(self, file_path):
        """播放音频文件"""
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
        self.media_player.play()
        self.media_player.mediaStatusChanged.connect(lambda status: self.cleanup_audio(file_path, status))
    
    def cleanup_audio(self, file_path, status):
        """清理音频文件"""
        if status == QMediaPlayer.EndOfMedia:
            try:
                os.remove(file_path)
            except:
                pass
    
    def stop_reading(self):
        """停止朗读"""
        self.media_player.stop()
        if self.tts_thread and self.tts_thread.isRunning():
            self.tts_thread.quit()
    
    def translate_en_to_zh(self):
        """翻译文本（英译中，有选中翻译选中，无选中翻译全部）"""
        cursor = self.text_editor.textCursor()
        selected_text = cursor.selectedText().strip()
        if selected_text:
            text = selected_text
        else:
            text = self.text_editor.toPlainText().strip()
        
        if text:
            result = self.translator.translate(text)
            self.translation_display.setHtml(
                f"<p><b>原文：</b>{text}</p>"
                f"<p><b>译文：</b>{result}</p>"
            )
        else:
            QMessageBox.information(self, "提示", "文本为空，请先输入或导入文本")
    
    def translate_zh_to_en(self):
        """翻译文本（中译英，有选中翻译选中，无选中翻译全部）"""
        cursor = self.text_editor.textCursor()
        selected_text = cursor.selectedText().strip()
        if selected_text:
            text = selected_text
        else:
            text = self.text_editor.toPlainText().strip()
        
        if text:
            result = self.translator.translate_to_en(text)
            self.translation_display.setHtml(
                f"<p><b>原文：</b>{text}</p>"
                f"<p><b>译文：</b>{result}</p>"
            )
        else:
            QMessageBox.information(self, "提示", "文本为空，请先输入或导入文本")
    
    def _on_double_click(self, event):
        """双击事件 - 添加生词"""
        cursor = self.text_editor.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText().strip()
        
        if word and word.isalpha():
            translation = self.translator.translate(word)
            phonetic = fetch_phonetic(word)
            dialog = AddWordDialog(word, translation, self, phonetic=phonetic)
            if dialog.exec_() == QDialog.Accepted:
                word, trans, example = dialog.get_data()
                if self.db.add_word(word, trans, example):
                    self.load_vocabulary_list()
                    QMessageBox.information(self, "成功", f"'{word}' 已添加到生词本")
                else:
                    QMessageBox.warning(self, "提示", f"'{word}' 已存在于生词本中")
    
    def add_word_manual(self):
        """手动添加生词"""
        dialog = AddWordDialog("", "", self)
        if dialog.exec_() == QDialog.Accepted:
            word, trans, example = dialog.get_data()
            if word:
                if self.db.add_word(word, trans, example):
                    self.load_vocabulary_list()
                    QMessageBox.information(self, "成功", f"'{word}' 已添加到生词本")
                else:
                    QMessageBox.warning(self, "提示", f"'{word}' 已存在于生词本中")
    
    def load_vocabulary_list(self):
        """加载生词列表"""
        self.vocab_list.clear()
        words = self.db.get_all_words()
        for word, trans, example, add_time, _ in words:
            item = QListWidgetItem(f"{word} - {trans}")
            item.setData(Qt.UserRole, (word, trans, example, add_time))
            self.vocab_list.addItem(item)
        self.stats_label.setText(f"共 {len(words)} 个生词")
    
    def search_vocabulary(self, keyword):
        """搜索单词"""
        self.vocab_list.clear()
        if keyword:
            words = self.db.search_words(keyword)
        else:
            words = self.db.get_all_words()
        
        for word, trans, example, add_time, _ in words:
            item = QListWidgetItem(f"{word} - {trans}")
            item.setData(Qt.UserRole, (word, trans, example, add_time))
            self.vocab_list.addItem(item)
        self.stats_label.setText(f"共 {len(words)} 个生词")
    
    def show_word_detail(self, item):
        """显示单词详情"""
        data = item.data(Qt.UserRole)
        word, trans, example, add_time = data
        phonetic = fetch_phonetic(word)
        
        # 显示详情
        html = f"<h3>{word} {phonetic if phonetic else ''} 🔊</h3>"
        html += f"<p><b>释义：</b>{trans}</p>"
        html += f"<p><b>例句：</b>{example if example else '无'}</p>"
        html += f"<p><b>添加时间：</b>{add_time}</p>"
        self.translation_display.setHtml(html)
        
        # 事件过滤器实现点击喇叭播放
        self.translation_display.viewport().installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """事件过滤器"""
        if obj == self.translation_display.viewport() and event.type() == event.MouseButtonRelease:
            cursor = self.translation_display.cursorForPosition(event.pos())
            anchor = cursor.block().text()
            if '🔊' in anchor:
                word = self.translation_display.toPlainText().split('\n')[0].split()[0]
                self.start_tts(word)
                return True
        return super().eventFilter(obj, event)
    
    def delete_selected_word(self):
        """删除选中的单词"""
        current_item = self.vocab_list.currentItem()
        if current_item:
            data = current_item.data(Qt.UserRole)
            word = data[0]
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除 '{word}' 吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.db.delete_word(word)
                self.load_vocabulary_list()
    
    def export_vocabulary(self):
        """导出生词本"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出生词本", "vocabulary_export.txt",
            "文本文件 (*.txt)"
        )
        if filepath:
            self.db.export_to_txt(filepath)
            QMessageBox.information(self, "成功", f"生词本已导出到:\n{filepath}")
    
    def closeEvent(self, event):
        """关闭事件"""
        # 清理AI线程
        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.quit()
            self.ai_thread.wait()
        
        # 清理TTS线程
        if self.tts_thread and self.tts_thread.isRunning():
            self.tts_thread.quit()
            self.tts_thread.wait()
        
        event.accept()
