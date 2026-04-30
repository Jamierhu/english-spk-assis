# -*- coding: utf-8 -*-
"""
翻译和TTS服务模块
"""

import asyncio
import tempfile
import requests
import edge_tts
from PyQt5.QtCore import QThread, pyqtSignal
from translate import Translator


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
    """翻译服务类"""
    
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


def fetch_phonetic(word):
    """从有道词典API获取音标"""
    try:
        url = f"https://dict.youdao.com/jsonapi?q={word}&dicts=ec"
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