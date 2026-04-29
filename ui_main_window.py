# -*- coding: utf-8 -*-
"""
主窗口界面类
"""

import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTextEdit, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QGroupBox, QLineEdit, QFileDialog, QMessageBox, QSplitter,
    QSlider, QTextBrowser, QDialog
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QTextCursor, QIcon
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

from vocabulary_db import VocabularyDB
from translation_service import TranslationService, TTSWorker, fetch_phonetic
from add_word_dialog import AddWordDialog


class MainWindowUI(QMainWindow):
    """主窗口界面类"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化服务
        self.db = VocabularyDB()
        self.media_player = QMediaPlayer()
        self.tts_thread = None
        self.translator = TranslationService()
        
        # 初始化界面
        self.init_ui()
        
        # 加载数据
        self.load_vocabulary_list()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(" ")
        self.setGeometry(100, 100, 1200, 800)
        # 隐藏系统标题栏
        #self.setWindowFlags(Qt.FramelessWindowHint)
        
        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "icon.png")
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
        
        # ===== 右侧：生词本 =====
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
        
        # 文本编辑区
        left_layout.addWidget(self._create_text_group())
        
        # 控制面板
        left_layout.addWidget(self._create_control_group())
        
        # 翻译区域
        left_layout.addWidget(self._create_translation_group())
        
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
            "- 选中文字后点击'朗读'可播放语音\n"
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
        #self.translation_display.setMaximumHeight(150)
        trans_layout.addWidget(self.translation_display)
        
        return trans_group
    
    def _create_right_panel(self):
        """创建右侧生词本面板"""
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
                left: 20px;
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
                width: 20px;
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
                padding: 20px;
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
                font-size: 20px;
                color: #2C4A6E;
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
        html = f"<h3>{word} {phonetic if phonetic else ''}🔊</h3>"
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