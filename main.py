# -*- coding: utf-8 -*-
"""
英语口语练习应用 - 程序入口

功能：文本朗读、翻译、生词本管理
"""

import sys
from PyQt5.QtWidgets import QApplication
from ui_main_window import MainWindowUI


def main():
    """程序入口"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindowUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()