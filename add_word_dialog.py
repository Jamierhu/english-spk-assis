# -*- coding: utf-8 -*-
"""
添加生词对话框模块
"""

from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QLabel, QToolButton, QHBoxLayout
)


class AddWordDialog(QDialog):
    """添加生词对话框类"""
    
    def __init__(self, word="", translation="", parent=None, phonetic=""):
        super().__init__(parent)
        self.setWindowTitle("添加生词")
        self.setModal(True)
        self.init_ui(word, translation, phonetic)
    
    def init_ui(self, word, translation, phonetic):
        """初始化界面"""
        layout = QFormLayout(self)
        
        # 单词行（包含单词输入、音标、播放按钮）
        word_layout = QHBoxLayout()
        
        self.word_input = QLineEdit(word)
        word_layout.addWidget(self.word_input)
        
        # 音标显示
        if phonetic:
            self.phonetic_label = QLabel(phonetic)
        else:
            self.phonetic_label = QLabel("")
        word_layout.addWidget(self.phonetic_label)
        
        # 小喇叭按钮
        self.speaker_btn = QToolButton()
        self.speaker_btn.setText("🔊")
        self.speaker_btn.setToolTip("播放发音")
        self.speaker_btn.clicked.connect(lambda: self.parent().start_tts(self.word_input.text()))
        word_layout.addWidget(self.speaker_btn)
        
        layout.addRow("单词:", word_layout)
        
        # 释义输入
        self.trans_input = QLineEdit(translation)
        layout.addRow("释义:", self.trans_input)
        
        # 例句输入
        self.example_input = QTextEdit()
        self.example_input.setMaximumHeight(80)
        self.example_input.setPlaceholderText("输入例句（可选）")
        layout.addRow("例句:", self.example_input)
        
        # 确定/取消按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_data(self):
        """获取输入数据"""
        return (
            self.word_input.text().strip(),
            self.trans_input.text().strip(),
            self.example_input.toPlainText().strip()
        )