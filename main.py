# -*- coding: utf-8 -*-
"""
英语口语练习应用
功能：文本朗读、翻译、生词本管理
"""

import sys
import sqlite3
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QTabWidget, QLineEdit, QFileDialog, QMessageBox, QSplitter,
    QComboBox, QSlider, QGroupBox, QFormLayout, QDialog,
    QDialogButtonBox, QTextBrowser
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QUrl
from PyQt5.QtGui import QFont, QTextCursor, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
import requests
from PyQt5.QtWidgets import QToolButton

import edge_tts
import asyncio
import tempfile
import os
from translate import Translator


# ==================== 数据库管理 ====================
class VocabularyDB:
    """生词本数据库管理"""
    
    def __init__(self, db_path="vocabulary.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE NOT NULL,
                translation TEXT,
                example TEXT,
                add_time TEXT,
                review_count INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_word(self, word, translation="", example=""):
        """添加生词"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO vocabulary (word, translation, example, add_time)
                VALUES (?, ?, ?, ?)
            ''', (word, translation, example, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # 单词已存在
        finally:
            conn.close()
    
    def get_all_words(self):
        """获取所有生词"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT word, translation, example, add_time, review_count FROM vocabulary ORDER BY add_time DESC')
        words = cursor.fetchall()
        conn.close()
        return words
    
    def search_words(self, keyword):
        """搜索单词"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT word, translation, example, add_time, review_count 
            FROM vocabulary 
            WHERE word LIKE ? OR translation LIKE ?
            ORDER BY add_time DESC
        ''', (f'%{keyword}%', f'%{keyword}%'))
        words = cursor.fetchall()
        conn.close()
        return words
    
    def delete_word(self, word):
        """删除单词"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM vocabulary WHERE word = ?', (word,))
        conn.commit()
        conn.close()
    
    def export_to_txt(self, filepath):
        """导出生词到文本文件"""
        words = self.get_all_words()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 50 + "\n")
            f.write("生词本导出\n")
            f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            for word, trans, example, add_time, _ in words:
                f.write(f"单词: {word}\n")
                f.write(f"释义: {trans}\n")
                if example:
                    f.write(f"例句: {example}\n")
                f.write(f"添加时间: {add_time}\n")
                f.write("-" * 30 + "\n\n")


# ==================== 翻译服务 ====================
class TTSWorker(QThread):
    """Edge-TTS工作线程"""
    
    finished = pyqtSignal(str)  # 传递生成的音频文件路径
    
    def __init__(self, text, voice="en-US-AriaNeural", rate="+0%", volume="+0%"):
        super().__init__()
        self.text = text
        self.voice = voice
        self.rate = rate
        self.volume = volume
    
    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            communicate = edge_tts.Communicate(self.text, self.voice, rate=self.rate, volume=self.volume)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                loop.run_until_complete(communicate.save(f.name))
                self.finished.emit(f.name)
        except Exception as e:
            print(f"TTS error: {e}")
        finally:
            loop.close()


class TranslationService:
    """翻译服务"""
    
    def __init__(self):
        self.translator = Translator(to_lang="zh")
    
    def translate(self, text):
        """翻译文本（英译中）"""
        try:
            result = self.translator.translate(text)
            return result
        except Exception as e:
            return f"翻译失败: {str(e)}"
    
    def translate_to_en(self, text):
        """翻译文本（中译英）"""
        try:
            translator = Translator(from_lang="zh", to_lang="en")
            result = translator.translate(text)
            return result
        except Exception as e:
            return f"翻译失败: {str(e)}"


# ==================== 主窗口 ====================
class EnglishPracticeApp(QMainWindow):
    """英语口语练习应用主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db = VocabularyDB()
        self.media_player = QMediaPlayer()
        self.tts_thread = None
        self.translator = TranslationService()
        self.init_ui()
        self.load_vocabulary_list()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("英语口语练习助手")
        self.setGeometry(100, 100, 1200, 800)
        
        # 主部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # ===== 左侧：练习区域 =====
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 文本编辑区
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
        self.text_editor.setPlaceholderText("在这里输入或粘贴英文文本...\n\n提示：\n- 选中文字后点击'朗读选中'可播放语音\n- 双击单词可添加到生词本")
        self.text_editor.textChanged.connect(self.on_text_changed)
        text_layout.addWidget(self.text_editor)
        
        left_layout.addWidget(text_group)
        
        # 控制面板
        control_group = QGroupBox("朗读控制")
        control_layout = QHBoxLayout(control_group)
        
        btn_read_all = QPushButton("🔊 朗读全部")
        btn_read_all.clicked.connect(self.read_all_text)
        control_layout.addWidget(btn_read_all)
        
        btn_read_selected = QPushButton("🔊 朗读选中")
        btn_read_selected.clicked.connect(self.read_selected_text)
        control_layout.addWidget(btn_read_selected)
        
        btn_stop = QPushButton("⏹️ 停止")
        btn_stop.clicked.connect(self.stop_reading)
        control_layout.addWidget(btn_stop)
        
        # 语速调节
        control_layout.addWidget(QLabel("语速:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(50)
        self.speed_slider.setMaximum(300)
        self.speed_slider.setValue(150)
        self.speed_slider.valueChanged.connect(self.change_speed)
        control_layout.addWidget(self.speed_slider)
        
        left_layout.addWidget(control_group)
        
        # 翻译区域
        trans_group = QGroupBox("翻译对照")
        trans_layout = QVBoxLayout(trans_group)
        
        trans_toolbar = QHBoxLayout()
        btn_trans = QPushButton("🌐 翻译选中（英→中）")
        btn_trans.clicked.connect(self.translate_selected)
        trans_toolbar.addWidget(btn_trans)
        
        btn_trans_en = QPushButton("🌐 翻译选中（中→英）")
        btn_trans_en.clicked.connect(self.translate_to_en)
        trans_toolbar.addWidget(btn_trans_en)
        trans_toolbar.addStretch()
        trans_layout.addLayout(trans_toolbar)
        
        self.translation_display = QTextBrowser()
        self.translation_display.setFont(QFont("Microsoft YaHei", 11))
        self.translation_display.setMaximumHeight(150)
        trans_layout.addWidget(self.translation_display)
        
        left_layout.addWidget(trans_group)
        
        # ===== 右侧：生词本 =====
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
        
        # ===== 组装界面 =====
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)  # 左侧占3份
        splitter.setStretchFactor(1, 1)  # 右侧占1份
        
        main_layout.addWidget(splitter)
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 5px;
                background-color: #4CAF50;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QTextEdit, QTextBrowser, QLineEdit {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
        """)
        
        # 双击事件绑定
        self.text_editor.mouseDoubleClickEvent = self.on_double_click
    
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
    
    def on_text_changed(self):
        """文本改变时的处理"""
        pass  # 可以添加实时翻译等功能
    
    def read_all_text(self):
        """朗读全部文本"""
        text = self.text_editor.toPlainText()
        if text:
            self.start_tts(text)
    
    def read_selected_text(self):
        """朗读选中文本"""
        cursor = self.text_editor.textCursor()
        text = cursor.selectedText()
        if text:
            self.start_tts(text)
        else:
            QMessageBox.information(self, "提示", "请先选中要朗读的文本")
    
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
    
    def change_speed(self, value):
        """改变语速"""
        # 语速在下次播放时应用
        pass
    
    def translate_selected(self):
        """翻译选中文本（英译中）"""
        cursor = self.text_editor.textCursor()
        text = cursor.selectedText().strip()
        if text:
            result = self.translator.translate(text)
            self.translation_display.setHtml(
                f"<p><b>原文：</b>{text}</p>"
                f"<p><b>译文：</b>{result}</p>"
            )
        else:
            QMessageBox.information(self, "提示", "请先选中要翻译的文本")
    
    def translate_to_en(self):
        """翻译选中文本（中译英）"""
        cursor = self.text_editor.textCursor()
        text = cursor.selectedText().strip()
        if text:
            result = self.translator.translate_to_en(text)
            self.translation_display.setHtml(
                f"<p><b>原文：</b>{text}</p>"
                f"<p><b>译文：</b>{result}</p>"
            )
        else:
            QMessageBox.information(self, "提示", "请先选中要翻译的文本")
    
    def on_double_click(self, event):
        """双击事件 - 添加生词"""
        cursor = self.text_editor.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText().strip()
        
        if word and word.isalpha():
            # 自动翻译
            translation = self.translator.translate(word)
            phonetic = fetch_phonetic(word)
            # 弹出确认对话框
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
        # 朗读单词
        # self.start_tts(word)  # 改为点击喇叭播放
        # 显示详情
        html = f"<h3>{word} <span style='font-size:16px;color:#888;'>{phonetic if phonetic else ''}</span> "
        html += f"<a href='#' id='play_word' style='text-decoration:none;'>🔊</a></h3>"
        html += f"<p><b>释义：</b>{trans}</p>"
        html += f"<p><b>例句：</b>{example if example else '无'}</p>"
        html += f"<p><b>添加时间：</b>{add_time}</p>"
        self.translation_display.setHtml(html)
        # 事件过滤器实现点击喇叭播放
        self.translation_display.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
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


# ==================== 添加生词对话框 ====================
class AddWordDialog(QDialog):
    """添加生词对话框"""
    
    def __init__(self, word="", translation="", parent=None, phonetic=""):
        super().__init__(parent)
        self.setWindowTitle("添加生词")
        self.setModal(True)
        self.init_ui(word, translation, phonetic)
    
    def init_ui(self, word, translation, phonetic):
        layout = QFormLayout(self)

        word_layout = QHBoxLayout()
        self.word_input = QLineEdit(word)
        word_layout.addWidget(self.word_input)
        if phonetic:
            self.phonetic_label = QLabel(phonetic)
            word_layout.addWidget(self.phonetic_label)
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

        self.trans_input = QLineEdit(translation)
        layout.addRow("释义:", self.trans_input)

        self.example_input = QTextEdit()
        self.example_input.setMaximumHeight(80)
        self.example_input.setPlaceholderText("输入例句（可选）")
        layout.addRow("例句:", self.example_input)

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


# ==================== 获取音标函数 ====================
def fetch_phonetic(word):
    """从有道词典API获取音标"""
    try:
        url = f"https://dict.youdao.com/jsonapi?q={word}&dicts=ec"  # 有道开放API
        resp = requests.get(url, timeout=5)
        data = resp.json()
        # 英式音标优先
        phonetic = data.get('ec', {}).get('word', [{}])[0].get('ukphone')
        if not phonetic:
            phonetic = data.get('ec', {}).get('word', [{}])[0].get('usphone')
        if phonetic:
            return f'[{phonetic}]'
    except Exception as e:
        print(f"音标获取失败: {e}")
    return ''


# ==================== 主程序入口 ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    window = EnglishPracticeApp()
    window.show()
    
    sys.exit(app.exec_())
