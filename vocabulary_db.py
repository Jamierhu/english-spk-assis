# -*- coding: utf-8 -*-
"""
生词本数据库管理模块
"""

import sqlite3
from datetime import datetime


class VocabularyDB:
    """生词本数据库管理类"""
    
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