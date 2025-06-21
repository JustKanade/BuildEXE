#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roblox资源提取器 - 从Roblox缓存中提取音频、图片、纹理和模型文件
Roblox Asset Extractor - Extract audio, images, textures and models from Roblox cache
作者/Author: JustKanade
修改/Modified by: User (Enhanced Version)
版本/Version: 0.15.0 (Multiple Asset Types Support)
许可/License: GNU Affero General Public License v3.0 (AGPLv3)
"""

import os
import sys
import time
import json
import logging
import threading
import concurrent.futures
import platform
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import Dict, List, Any, Tuple, Set, Optional
from enum import Enum, auto
import datetime
import queue
import traceback
import hashlib
import multiprocessing
from functools import lru_cache


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# 延迟导入库列表
_LIBS_IMPORTED = False
gzip = shutil = random = string = getpass = subprocess = ThreadPoolExecutor = Fore = Style = init = None


# 分类方法枚举
class ClassificationMethod(Enum):
    """资源分类方法枚举"""
    DURATION = auto()  # 按时长分类（仅音频）
    SIZE = auto()  # 按大小分类
    TYPE = auto()  # 按文件类型分类
    FORMAT = auto()  # 按具体格式分类


# 文件类型枚举
class FileType(Enum):
    """文件类型枚举"""
    AUDIO_OGG = auto()  # OGG音频文件
    IMAGE_PNG = auto()  # PNG图片
    IMAGE_WEBP = auto()  # WEBP图片
    TEXTURE_KTX = auto()  # KTX纹理
    MODEL_RBXM = auto()  # RBXM模型


def import_libs():
    """按需导入库，减少启动时间和内存占用"""
    global gzip, shutil, random, string, hashlib, getpass, multiprocessing
    global subprocess, ThreadPoolExecutor, Fore, Style, init, _LIBS_IMPORTED

    if _LIBS_IMPORTED:
        return

    # 导入标准库
    import gzip
    import shutil
    import random
    import string
    import hashlib
    import getpass
    import multiprocessing
    import subprocess
    import webbrowser
    from concurrent.futures import ThreadPoolExecutor

    # 导入第三方库
    try:
        from colorama import Fore, Style, init
        init()
    except ImportError:
        # 创建假的colorama对象
        class DummyColorama:
            def __getattr__(self, name):
                return ""

        Fore = DummyColorama()
        Style = DummyColorama()

        def dummy_init():
            pass

        init = dummy_init
        logger.warning("未找到colorama库，将不显示彩色输出。请使用 pip install colorama 安装。")
        logger.warning(
            "Colorama library not found, colored output won't be displayed. Install with: pip install colorama.")

    _LIBS_IMPORTED = True


def get_roblox_default_dir():
    try:
        username = os.getenv('USERNAME') or os.getenv('USER')

        if os.name == 'nt':  # Windows
            return os.path.join("C:", os.sep, "Users", username, "AppData", "Local", "Roblox", "rbx-storage")
        elif sys.platform == 'darwin':  # macOS
            return os.path.join("/Users", username, "Library", "Caches", "Roblox", "rbx-storage")
        else:  # Linux
            return os.path.join(os.path.expanduser("~"), ".local", "share", "Roblox", "rbx-storage")
    except:
        return os.path.join(os.getcwd(), "Roblox")


class Language(Enum):
    """支持的语言枚举类"""
    ENGLISH = auto()
    CHINESE = auto()


class LanguageManager:
    """语言管理器，处理翻译和语言切换"""

    def __init__(self):
        """初始化语言管理器，设置支持的语言和翻译"""
        self.ENGLISH = Language.ENGLISH
        self.CHINESE = Language.CHINESE

        # 翻译字典 - 使用嵌套字典结构更高效
        self._load_translations()

        # 设置当前语言
        self.current_language = self._detect_system_language()
        self._cache = {}  # 添加缓存以提高性能

    def _load_translations(self):
        """加载翻译，分离为单独方法以提高可维护性"""
        self.TRANSLATIONS = {
            "title": {
                self.ENGLISH: "    Roblox-Asset-Extractor Version-0.15.0 ",
                self.CHINESE: "    Roblox-Asset-Extractor Version-0.15.0 "
            },

            "welcome_message": {
                self.ENGLISH: "Welcome to Roblox Asset Extractor!",
                self.CHINESE: "欢迎使用 Roblox-Asset-Extractor "
            },
            "extract_assets": {
                self.ENGLISH: "Extract Assets",
                self.CHINESE: "提取资源"
            },
            "view_history": {
                self.ENGLISH: "View History",
                self.CHINESE: "查看历史"
            },
            "clear_history": {
                self.ENGLISH: "Clear Extracted History",
                self.CHINESE: "清除提取历史"
            },
            "language_settings": {
                self.ENGLISH: "Languages",
                self.CHINESE: "语言"
            },
            "about": {
                self.ENGLISH: "About",
                self.CHINESE: "关于"
            },

            'clear_cache': {
                Language.ENGLISH: "Clear Asset Cache",
                Language.CHINESE: "清除资源缓存"
            },
            'cache_description': {
                Language.ENGLISH: "Clear all asset cache files (audio, images, textures, models) from the default cache directory.\n\nNote: The extracted_assets, extracted_mp3, and extracted_oggs folders will be automatically excluded from clearing.\n\nUse this when you want to extract assets from a specific game: clear the cache first, then run the game until it's fully loaded before extracting.",
                Language.CHINESE: "清除默认缓存目录中的所有资源缓存文件（音频、图片、纹理、模型）。\n\n注意：extracted_assets、extracted_mp3和extracted_oggs文件夹将自动排除，不会被清除。\n\n当你想要提取某一特定游戏的资源时使用:先清除缓存,然后运行游戏直至完全加载后再进行提取。"
            },
            'confirm_clear_cache': {
                Language.ENGLISH: "Are you sure you want to clear all asset cache files? This cannot be undone.",
                Language.CHINESE: "确定要清除所有资源缓存文件吗？此操作无法撤销。"
            },
            'cache_cleared': {
                Language.ENGLISH: "Successfully cleared {0} of {1} asset cache files.",
                Language.CHINESE: "成功清除了{1}个缓存文件中的{0}个。"
            },
            'no_cache_found': {
                Language.ENGLISH: "No asset cache files found.",
                Language.CHINESE: "未找到资源缓存文件。"
            },
            'clear_cache_failed': {
                Language.ENGLISH: "Failed to clear cache: {0}",
                Language.CHINESE: "清除缓存失败: {0}"
            },
            'cache_location': {
                Language.ENGLISH: "Cache Directory Location",
                Language.CHINESE: "缓存目录位置"
            },
            'cache_dir_not_found': {
                Language.ENGLISH: "Cache directory not found.",
                Language.CHINESE: "未找到缓存目录。"
            },
            "error_occurred": {
                self.ENGLISH: "An error occurred: {}",
                self.CHINESE: "发生错误：{}"
            },
            "history_stats": {
                self.ENGLISH: "=== Extracted History Statistics ===",
                self.CHINESE: "=== 提取历史统计 ==="
            },
            "files_recorded": {
                self.ENGLISH: "Files recorded in history: {}",
                self.CHINESE: "历史记录中的文件数：{}"
            },
            "history_file_location": {
                self.ENGLISH: "History file location: {}",
                self.CHINESE: "历史记录文件位置：{}"
            },
            "confirm_clear_history": {
                self.ENGLISH: "Are you sure you want to clear all download history?  ",
                self.CHINESE: "您确定要清除所有提取历史吗？"
            },
            "history_cleared": {
                self.ENGLISH: "Extracted history has been cleared.",
                self.CHINESE: "提取历史已清除。"
            },
            "operation_cancelled": {
                self.ENGLISH: "Operation cancelled.",
                self.CHINESE: "操作已取消。"
            },
            # 新增分类方法相关翻译
            "classification_method": {
                self.ENGLISH: "Classification Method",
                self.CHINESE: "分类方法"
            },
            "classify_by_duration": {
                self.ENGLISH: "1. Classify by audio duration (audio only, requires FFmpeg)",
                self.CHINESE: "1. 按音频时长分类 (仅音频，需要安装FFmpeg)"
            },
            "classify_by_size": {
                self.ENGLISH: "2. Classify by file size",
                self.CHINESE: "2. 按文件大小分类"
            },
            "classify_by_type": {
                self.ENGLISH: "3. Classify by file type (recommended)",
                self.CHINESE: "3. 按文件类型分类 (推荐)"
            },
            "asset_types": {
                self.ENGLISH: "Asset Types to Extract",
                self.CHINESE: "要提取的资源类型"
            },
            "extract_audio": {
                self.ENGLISH: "Audio Files (OGG)",
                self.CHINESE: "音频文件 (OGG)"
            },
            "extract_images": {
                self.ENGLISH: "Image Files (PNG, WEBP)",
                self.CHINESE: "图片文件 (PNG, WEBP)"
            },
            "extract_textures": {
                self.ENGLISH: "Texture Files (KTX)",
                self.CHINESE: "纹理文件 (KTX)"
            },
            "extract_models": {
                self.ENGLISH: "Model Files (RBXM)",
                self.CHINESE: "模型文件 (RBXM)"
            },
            "ffmpeg_not_found_warning": {
                self.ENGLISH: "Warning: FFmpeg not found. Duration classification may not work correctly.",
                self.CHINESE: "警告：未找到FFmpeg。按时长分类可能无法正常工作。"
            },
            "ultra_small": {
                self.ENGLISH: "Ultra Small (0-50KB)",
                self.CHINESE: "极小文件 (0-50KB)"
            },
            "small": {
                self.ENGLISH: "Small (50KB-200KB)",
                self.CHINESE: "小文件 (50KB-200KB)"
            },
            "medium": {
                self.ENGLISH: "Medium (200KB-1MB)",
                self.CHINESE: "中等文件 (200KB-1MB)"
            },
            "large": {
                self.ENGLISH: "Large (1MB-5MB)",
                self.CHINESE: "大文件 (1MB-5MB)"
            },
            "ultra_large": {
                self.ENGLISH: "Ultra Large (5MB+)",
                self.CHINESE: "极大文件 (5MB以上)"
            },
            "size_classification_info": {
                self.ENGLISH: "• Files will be organized by file size in different folders",
                self.CHINESE: "• 文件将按文件大小分类到不同文件夹中"
            },
            "duration_classification_info": {
                self.ENGLISH: "• Audio files will be organized by duration in different folders",
                self.CHINESE: "• 音频文件将按时长分类到不同文件夹中"
            },
            "type_classification_info": {
                self.ENGLISH: "• Files will be organized by type: Audio, Images, Textures, Models",
                self.CHINESE: "• 文件将按类型分类: 音频、图片、纹理、模型"
            },
            # 文件类型翻译
            "audio_files": {
                self.ENGLISH: "Audio Files",
                self.CHINESE: "音频文件"
            },
            "image_files": {
                self.ENGLISH: "Image Files",
                self.CHINESE: "图片文件"
            },
            "texture_files": {
                self.ENGLISH: "Texture Files",
                self.CHINESE: "纹理文件"
            },
            "model_files": {
                self.ENGLISH: "Model Files",
                self.CHINESE: "模型文件"
            },
        }
        # 添加剩余的翻译
        self._add_remaining_translations()

    def _add_remaining_translations(self):
        """添加剩余的翻译项"""
        remaining = {

            "Creators & Contributors": {
                self.ENGLISH: "Creators & Contributor：JustKanade",
                self.CHINESE: "创作&贡献者：JustKanade："
            },

            "about_info": {
                self.ENGLISH: "This is an open-source tool for extracting asset files (audio, images, textures, models) from Roblox cache and organizing them by type or other criteria.",
                self.CHINESE: "这是一个开源工具，旨在用于从 Roblox 缓存中提取资源文件（音频、图片、纹理、模型）并按类型或其他标准组织它们。"
            },

            "default_dir": {
                self.ENGLISH: "Default directory: ",
                self.CHINESE: "默认目录："
            },
            "input_dir": {
                self.ENGLISH: "Enter directory (press Enter for default): ",
                self.CHINESE: "输入目录（按回车使用默认值）："
            },
            "dir_not_exist": {
                self.ENGLISH: "Directory does not exist: {}",
                self.CHINESE: "目录不存在：{}"
            },
            "create_dir_prompt": {
                self.ENGLISH: "Create directory? (y/n): ",
                self.CHINESE: "创建目录？(y/n)："
            },
            "dir_created": {
                self.ENGLISH: "Directory created: {}",
                self.CHINESE: "目录已创建：{}"
            },
            "dir_create_failed": {
                self.ENGLISH: "Failed to create directory: {}",
                self.CHINESE: "创建目录失败：{}"
            },
            "processing_info": {
                self.ENGLISH: "=== Processing Information ===",
                self.CHINESE: "=== 处理信息 ==="
            },
            "info_duration_categories": {
                self.ENGLISH: "• Audio files will be organized by duration in different folders",
                self.CHINESE: "• 音频文件将按时长分类到不同文件夹中"
            },
            "info_mp3_conversion": {
                self.ENGLISH: "• You can convert OGG files to MP3 after extraction",
                self.CHINESE: "• 提取后可以将OGG文件转换为MP3"
            },
            "info_skip_downloaded": {
                self.ENGLISH: "• Previously extracted files will be skipped",
                self.CHINESE: "• 将跳过之前提取过的文件"
            },
            "threads_prompt": {
                self.ENGLISH: "Enter number of threads (default: {}): ",
                self.CHINESE: "输入线程数（默认：{}）："
            },
            "threads_min_error": {
                self.ENGLISH: "Number of threads must be at least 1",
                self.CHINESE: "线程数必须至少为1"
            },
            "threads_high_warning": {
                self.ENGLISH: "Warning: Using a high number of threads may slow down your computer",
                self.CHINESE: "警告：使用过多线程可能会降低计算机性能"
            },
            "confirm_high_threads": {
                self.ENGLISH: "Continue with high thread count anyway? (y/n): ",
                self.CHINESE: "是否仍使用这么多线程？(y/n)："
            },
            "threads_adjusted": {
                self.ENGLISH: "Thread count adjusted to: {}",
                self.CHINESE: "线程数已调整为：{}"
            },
            "input_invalid": {
                self.ENGLISH: "Invalid input, using default value",
                self.CHINESE: "输入无效，使用默认值"
            },
            "extraction_complete": {
                self.ENGLISH: "Extraction completed successfully!",
                self.CHINESE: "提取成功完成！"
            },
            "processed": {
                self.ENGLISH: "Processed: {} files",
                self.CHINESE: "已处理：{} 个文件"
            },
            "skipped_duplicates": {
                self.ENGLISH: "Skipped duplicates: {} files",
                self.CHINESE: "跳过重复：{} 个文件"
            },
            "skipped_already_processed": {
                self.ENGLISH: "Skipped already processed: {} files",
                self.CHINESE: "跳过已处理：{} 个文件"
            },
            "errors": {
                self.ENGLISH: "Errors: {} files",
                self.CHINESE: "错误：{} 个文件"
            },
            "time_spent": {
                self.ENGLISH: "Time spent: {:.2f} seconds",
                self.CHINESE: "耗时：{:.2f} 秒"
            },
            "files_per_sec": {
                self.ENGLISH: "Processing speed: {:.2f} files/second",
                self.CHINESE: "处理速度：{:.2f} 文件/秒"
            },
            "output_dir": {
                self.ENGLISH: "Output directory: {}",
                self.CHINESE: "输出目录：{}"
            },
            "convert_to_mp3_prompt": {
                self.ENGLISH: "Do you want to convert extracted OGG files to MP3? (y/n): ",
                self.CHINESE: "是否将提取的OGG文件转换为MP3？(y/n)："
            },
            "mp3_conversion_complete": {
                self.ENGLISH: "MP3 conversion completed!",
                self.CHINESE: "MP3转换完成！"
            },
            "converted": {
                self.ENGLISH: "Converted: {} of {} files",
                self.CHINESE: "已转换：{} / {} 个文件"
            },
            "mp3_conversion_failed": {
                self.ENGLISH: "MP3 conversion failed: {}",
                self.CHINESE: "MP3转换失败：{}"
            },
            "opening_output_dir": {
                self.ENGLISH: "Opening {} output directory...",
                self.CHINESE: "正在打开{}输出目录..."
            },
            "manual_navigate": {
                self.ENGLISH: "Please navigate manually to: {}",
                self.CHINESE: "请手动导航到：{}"
            },
            "no_files_processed": {
                self.ENGLISH: "No files were processed",
                self.CHINESE: "没有处理任何文件"
            },
            "total_runtime": {
                self.ENGLISH: "Total runtime: {:.2f} seconds",
                self.CHINESE: "总运行时间：{:.2f} 秒"
            },
            "canceled_by_user": {
                self.ENGLISH: "Operation canceled by user",
                self.CHINESE: "操作被用户取消"
            },
            "scanning_files": {
                self.ENGLISH: "Scanning for files...",
                self.CHINESE: "正在扫描文件..."
            },
            "found_files": {
                self.ENGLISH: "Found {} files in {:.2f} seconds",
                self.CHINESE: "在 {:.2f} 秒内找到 {} 个文件"
            },
            "no_files_found": {
                self.ENGLISH: "No files found in the specified directory",
                self.CHINESE: "在指定目录中未找到文件"
            },
            "processing_with_threads": {
                self.ENGLISH: "Processing with {} threads...",
                self.CHINESE: "使用 {} 个线程处理..."
            },
            "mp3_category": {
                self.ENGLISH: "MP3",
                self.CHINESE: "MP3"
            },
            "ogg_category": {
                self.ENGLISH: "OGG",
                self.CHINESE: "OGG"
            },
            "readme_title": {
                self.ENGLISH: "Roblox Asset Files - Classification Information",
                self.CHINESE: "Roblox 资源文件 - 分类信息"
            },
            "ffmpeg_not_installed": {
                self.ENGLISH: "FFmpeg is not installed. Please install FFmpeg to convert files and get duration information.",
                self.CHINESE: "未安装FFmpeg。请安装FFmpeg以转换文件并获取时长信息。"
            },
            "no_ogg_files": {
                self.ENGLISH: "No OGG files found to convert",
                self.CHINESE: "未找到要转换的OGG文件"
            },
            "mp3_conversion": {
                self.ENGLISH: "Converting {} OGG files to MP3...",
                self.CHINESE: "正在将 {} 个OGG文件转换为MP3..."
            },
            "current_language": {
                self.ENGLISH: "Current language: {}",
                self.CHINESE: "当前语言：{}"
            },
            "select_language": {
                self.ENGLISH: "Select language (1. Chinese, 2. English): ",
                self.CHINESE: "选择语言 (1. 中文, 2. 英文): "
            },
            "language_set": {
                self.ENGLISH: "Language set to: {}",
                self.CHINESE: "语言设置为：{}"
            },
            "about_title": {
                self.ENGLISH: "About Roblox Asset Extractor",
                self.CHINESE: "关于 Roblox Asset Extractor"
            },
            "about_version": {
                self.ENGLISH: "Current Version: 0.15.0 ",
                self.CHINESE: "当前版本: 0.15.0"
            },
            "mp3_conversion_info": {
                self.ENGLISH: "Starting MP3 conversion...",
                self.CHINESE: "开始MP3转换..."
            },
            "getting_duration": {
                self.ENGLISH: "Getting audio duration...",
                self.CHINESE: "正在获取音频时长..."
            },
            "duration_unknown": {
                self.ENGLISH: "Unknown duration",
                self.CHINESE: "未知时长"
            },
            "readme_duration_title": {
                self.ENGLISH: "Audio Duration Categories:",
                self.CHINESE: "音频时长分类:"
            },
            "readme_size_title": {
                self.ENGLISH: "File Size Categories:",
                self.CHINESE: "文件大小分类:"
            },
            "readme_type_title": {
                self.ENGLISH: "File Type Categories:",
                self.CHINESE: "文件类型分类:"
            },
            "classification_method_used": {
                self.ENGLISH: "Classification method: {}",
                self.CHINESE: "分类方法: {}"
            },
            "classification_by_duration": {
                self.ENGLISH: "by audio duration",
                self.CHINESE: "按音频时长"
            },
            "classification_by_size": {
                self.ENGLISH: "by file size",
                self.CHINESE: "按文件大小"
            },
            "classification_by_type": {
                self.ENGLISH: "by file type",
                self.CHINESE: "按文件类型"
            },
        }
        # 合并词典
        self.TRANSLATIONS.update(remaining)

    @lru_cache(maxsize=128)
    def _detect_system_language(self) -> Language:
        """检测系统语言并返回相应的语言枚举"""
        try:
            import locale
            system_lang = locale.getdefaultlocale()[0].lower()
            if system_lang and ('zh_' in system_lang or 'cn' in system_lang):
                return self.CHINESE
            return self.ENGLISH
        except:
            return self.ENGLISH

    def get(self, key: str, *args) -> str:
        """获取指定键的翻译并应用格式化参数"""
        # 检查缓存
        cache_key = (key, self.current_language, args)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 如果键不存在，返回键本身
        if key not in self.TRANSLATIONS:
            return key

        translations = self.TRANSLATIONS[key]
        if self.current_language not in translations:
            # 回退到英语
            if self.ENGLISH in translations:
                message = translations[self.ENGLISH]
            else:
                # 使用任何可用的翻译
                message = next(iter(translations.values()))
        else:
            message = translations[self.current_language]

        # 应用格式化参数
        if args:
            try:
                message = message.format(*args)
            except:
                pass

        # 更新缓存
        if len(self._cache) > 1000:  # 避免缓存无限增长
            self._cache.clear()
        self._cache[cache_key] = message
        return message

    def set_language(self, language: Language) -> None:
        """设置当前语言"""
        if self.current_language != language:
            self.current_language = language
            self._cache.clear()  # 清除缓存

    def get_language_name(self) -> str:
        """获取当前语言的名称"""
        return "中文" if self.current_language == self.CHINESE else "English"


class ExtractedHistory:
    """管理提取历史，避免重复处理文件"""

    def __init__(self, history_file: str):
        """初始化提取历史"""
        import_libs()  # 确保已导入所需库
        self.history_file = history_file
        self.file_hashes: Set[str] = set()
        self.modified = False  # 跟踪是否修改过，避免不必要的保存
        self._lock = threading.Lock()  # 添加锁以保证线程安全
        self.load_history()

    def load_history(self) -> None:
        """从JSON文件加载历史记录"""
        try:
            if os.path.exists(self.history_file):
                import json
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    with self._lock:
                        if isinstance(data, list):
                            self.file_hashes = set(data)
                        elif isinstance(data, dict) and 'hashes' in data:
                            self.file_hashes = set(data['hashes'])
        except Exception as e:
            logger.error(f"Error loading history: {str(e)}")
            with self._lock:
                self.file_hashes = set()

    def save_history(self) -> None:
        """将历史记录保存到JSON文件"""
        with self._lock:
            if not self.modified:
                return  # 如果没有修改，不需要保存

            try:
                import json
                with open(self.history_file, 'w') as f:
                    json.dump(list(self.file_hashes), f)
                self.modified = False
            except Exception as e:
                logger.error(f"Error saving history: {str(e)}")

    def add_hash(self, file_hash: str) -> None:
        """添加文件哈希到历史记录"""
        with self._lock:
            if file_hash not in self.file_hashes:
                self.file_hashes.add(file_hash)
                self.modified = True

    def is_processed(self, file_hash: str) -> bool:
        """检查文件是否已处理"""
        with self._lock:
            return file_hash in self.file_hashes

    def clear_history(self) -> None:
        """清除所有提取历史"""
        with self._lock:
            if self.file_hashes:
                self.file_hashes = set()
                self.modified = True
                self.save_history()

    def get_history_size(self) -> int:
        """获取历史记录中的文件数量"""
        with self._lock:
            return len(self.file_hashes)


class ContentHashCache:
    """缓存文件内容哈希以检测重复"""

    def __init__(self):
        """初始化哈希缓存"""
        self.hashes: Set[str] = set()
        self.lock = threading.Lock()

    def is_duplicate(self, content_hash: str) -> bool:
        """检查内容哈希是否重复"""
        with self.lock:
            if content_hash in self.hashes:
                return True
            self.hashes.add(content_hash)
            return False

    def clear(self) -> None:
        """清除缓存"""
        with self.lock:
            self.hashes.clear()


class ProcessingStats:
    """跟踪处理统计信息"""

    def __init__(self):
        """初始化统计对象"""
        self.stats = {}
        self.lock = threading.Lock()
        self.reset()
        self._last_update_time = 0
        self._update_interval = 0.1  # 限制更新频率，单位秒

    def reset(self) -> None:
        """重置所有统计数据"""
        with self.lock:
            self.stats = {
                'processed_files': 0,
                'duplicate_files': 0,
                'already_processed': 0,
                'error_files': 0,
                'mp3_converted': 0,
                'mp3_skipped': 0,
                'mp3_errors': 0,
                'audio_files': 0,
                'image_files': 0,
                'texture_files': 0,
                'model_files': 0,
                'last_update': time.time()
            }
            self._last_update_time = 0

    def increment(self, stat_key: str, amount: int = 1) -> None:
        """增加特定统计计数"""
        # 限制更新频率，减少锁争用
        current_time = time.time()
        if current_time - self._last_update_time < self._update_interval:
            return  # 如果距离上次更新时间太短，直接返回

        with self.lock:
            if stat_key in self.stats:
                self.stats[stat_key] += amount
                self.stats['last_update'] = current_time
            else:
                self.stats[stat_key] = amount
            self._last_update_time = current_time

    def get(self, stat_key: str) -> int:
        """获取特定统计计数"""
        with self.lock:
            return self.stats.get(stat_key, 0)

    def get_all(self) -> Dict[str, int]:
        """获取所有统计数据"""
        with self.lock:
            return self.stats.copy()


class ProgressBar:
    """可视化进度条，提供更直观的进度显示"""

    def __init__(self, total, width=40, title="", fill_char="█", empty_char="░"):
        """初始化进度条"""
        self.total = max(1, total)  # 避免除以零
        self.width = width
        self.title = title
        self.fill_char = fill_char
        self.empty_char = empty_char
        self.last_progress = -1
        self.last_update_time = 0
        self.update_interval = 0.2  # 限制更新频率，单位秒

    def update(self, current, extra_info=""):
        """更新进度条显示"""
        # 限制更新频率
        current_time = time.time()
        if current_time - self.last_update_time < self.update_interval:
            return

        progress = min(100, int((current / self.total) * 100))

        # 只有在进度变化时才更新显示
        if progress != self.last_progress:
            self.last_progress = progress
            self.last_update_time = current_time

            filled_width = int(self.width * progress / 100)
            bar = self.fill_char * filled_width + self.empty_char * (self.width - filled_width)

            # 构建显示文本
            if self.title:
                display = f"{self.title} [{bar}] {progress}% ({current}/{self.total}) {extra_info}"
            else:
                display = f"[{bar}] {progress}% ({current}/{self.total}) {extra_info}"

            # 显示进度
            sys.stdout.write(f"\r{display}")
            sys.stdout.flush()

            # 如果完成则换行
            if progress >= 100:
                print()

    def complete(self):
        """完成进度条，确保最后状态正确"""
        if self.last_progress < 100:
            self.update(self.total)
            print()  # 确保换行


class RobloxAssetExtractor:
    """从Roblox临时文件中提取各种资源的主类"""

    def __init__(self, base_dir: str, num_threads: int = None,
                 download_history: Optional['ExtractedHistory'] = None,
                 classification_method: ClassificationMethod = ClassificationMethod.TYPE,
                 extract_types: Set[FileType] = None):
        """初始化提取器"""
        import_libs()  # 确保已导入所需库

        self.base_dir = os.path.abspath(base_dir)
        self.num_threads = num_threads or min(32, multiprocessing.cpu_count() * 2)
        self.download_history = download_history
        self.classification_method = classification_method
        self.extract_types = extract_types or {FileType.AUDIO_OGG, FileType.IMAGE_PNG, FileType.IMAGE_WEBP,
                                               FileType.TEXTURE_KTX, FileType.MODEL_RBXM}

        # 输出目录
        self.output_dir = os.path.join(self.base_dir, "extracted_assets")
        self.logs_dir = os.path.join(self.output_dir, "logs")

        # 创建日志和临时目录
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

        # 初始化处理对象
        self.stats = ProcessingStats()
        self.hash_cache = ContentHashCache()
        self.file_lock = threading.Lock()

        # 文件计数器，使用原子操作而不是锁
        self.processed_count = 0
        self.cancelled = False

        # 文件类型关键词映射
        self.file_type_keywords = {
            FileType.AUDIO_OGG: [b'OggS'],
            FileType.IMAGE_PNG: [b'PNG', b'\x89PNG'],
            FileType.IMAGE_WEBP: [b'WEBP'],
            FileType.TEXTURE_KTX: [b'KTX'],
            FileType.MODEL_RBXM: [b'<roblox!']
        }

        # 文件类型扩展名映射
        self.file_type_extensions = {
            FileType.AUDIO_OGG: '.ogg',
            FileType.IMAGE_PNG: '.png',
            FileType.IMAGE_WEBP: '.webp',
            FileType.TEXTURE_KTX: '.ktx',
            FileType.MODEL_RBXM: '.rbxm'
        }

        # 按音频时长分类文件 (秒)
        self.duration_categories = {
            "ultra_short_0-5s": (0, 5),  # 0-5秒 (音效、提示音)
            "short_5-15s": (5, 15),  # 5-15秒 (短音效、通知音)
            "medium_15-60s": (15, 60),  # 15-60秒 (循环音乐、短背景音)
            "long_60-300s": (60, 300),  # 1-5分钟 (完整音乐、长背景音)
            "ultra_long_300s+": (300, float('inf'))  # 5分钟+ (长音乐、语音)
        }

        # 按文件大小分类 (字节)
        self.size_categories = {
            "ultra_small_0-50KB": (0, 50 * 1024),  # 0-50KB
            "small_50-200KB": (50 * 1024, 200 * 1024),  # 50KB-200KB
            "medium_200KB-1MB": (200 * 1024, 1024 * 1024),  # 200KB-1MB
            "large_1MB-5MB": (1024 * 1024, 5 * 1024 * 1024),  # 1MB-5MB
            "ultra_large_5MB+": (5 * 1024 * 1024, float('inf'))  # 5MB+
        }

        # 按文件类型分类
        self.type_categories = {
            "audio_ogg": [FileType.AUDIO_OGG],
            "images": [FileType.IMAGE_PNG, FileType.IMAGE_WEBP],
            "textures_ktx": [FileType.TEXTURE_KTX],
            "models_rbxm": [FileType.MODEL_RBXM]
        }

        # 按具体格式分类
        self.format_categories = {
            "ogg_audio": [FileType.AUDIO_OGG],
            "png_images": [FileType.IMAGE_PNG],
            "webp_images": [FileType.IMAGE_WEBP],
            "ktx_textures": [FileType.TEXTURE_KTX],
            "rbxm_models": [FileType.MODEL_RBXM]
        }

        # 为每个类别创建目录
        self.category_dirs = {}
        self._create_category_directories()

    def _create_category_directories(self):
        """根据分类方法创建目录"""
        if self.classification_method == ClassificationMethod.DURATION:
            categories = self.duration_categories
        elif self.classification_method == ClassificationMethod.SIZE:
            categories = self.size_categories
        elif self.classification_method == ClassificationMethod.FORMAT:
            categories = self.format_categories
        else:  # TYPE
            categories = self.type_categories

        for category in categories:
            path = os.path.join(self.output_dir, category)
            os.makedirs(path, exist_ok=True)
            self.category_dirs[category] = path

    def find_files_to_process(self) -> List[str]:
        """查找需要处理的文件 - 使用os.scandir优化性能"""
        files_to_process = []
        output_path_norm = os.path.normpath(self.output_dir)

        # 需要排除的文件夹
        exclude_dirs = {'extracted_assets', 'extracted_mp3', 'extracted_oggs'}

        def scan_directory(dir_path):
            """递归扫描目录"""
            try:
                with os.scandir(dir_path) as entries:
                    for entry in entries:
                        # 如果当前条目是目录
                        if entry.is_dir():
                            # 检查是否为需要排除的目录
                            entry_path_norm = os.path.normpath(entry.path)
                            dir_name = os.path.basename(entry_path_norm)

                            # 如果目录不是输出目录且不在排除列表中
                            if (output_path_norm not in entry_path_norm and
                                    dir_name not in exclude_dirs and
                                    not any(excluded in entry_path_norm for excluded in exclude_dirs)):
                                scan_directory(entry.path)
                        elif entry.is_file():
                            # 检查文件大小
                            try:
                                stat_info = entry.stat()
                                if stat_info.st_size >= 10:  # 如果文件大小至少为10字节
                                    files_to_process.append(entry.path)
                            except OSError:
                                # 忽略无法访问的文件
                                pass
            except (PermissionError, OSError):
                # 忽略无法访问的目录
                pass

        # 开始扫描
        scan_directory(self.base_dir)
        return files_to_process

    def process_files(self) -> Dict[str, Any]:
        """处理目录中的文件"""
        # 扫描文件并记录开始时间
        start_time = time.time()
        print(f"\n• {lang.get('scanning_files')}")

        # 查找要处理的文件
        files_to_process = self.find_files_to_process()

        scan_duration = time.time() - start_time
        print(f"✓ {lang.get('found_files', len(files_to_process), scan_duration)}")

        if not files_to_process:
            print(f"! {lang.get('no_files_found')}")
            return {
                "processed": 0,
                "duplicates": 0,
                "already_processed": 0,
                "errors": 0,
                "output_dir": self.output_dir,
                "duration": 0,
                "files_per_second": 0,
                "by_type": {}
            }

        # 创建README文件
        self.create_readme()

        # 重置统计信息
        self.stats.reset()
        self.hash_cache.clear()
        self.processed_count = 0
        self.cancelled = False

        # 处理文件
        processing_start = time.time()
        print(f"\n• {lang.get('processing_with_threads', self.num_threads)}")

        # 启动进度条
        total_files = len(files_to_process)
        progress_bar = ProgressBar(total_files, title="Processing:", width=40)

        # 使用线程池处理文件
        batch_size = min(5000, total_files)  # 增加批次大小

        # 创建一个工作队列和一个结果队列
        work_queue = queue.Queue()

        # 填充工作队列
        for file_path in files_to_process:
            work_queue.put(file_path)

        # 创建工作线程
        def worker():
            while not self.cancelled:
                try:
                    # 从队列获取项目，如果队列为空5秒则退出
                    file_path = work_queue.get(timeout=5)
                    try:
                        self.process_file(file_path)
                    finally:
                        work_queue.task_done()
                        # 更新进度
                        self.processed_count += 1
                        # 更新显示，无需频繁更新
                        if self.processed_count % 10 == 0:
                            stats = self.stats.get_all()
                            elapsed = time.time() - processing_start
                            speed = self.processed_count / elapsed if elapsed > 0 else 0
                            remaining = (total_files - self.processed_count) / speed if speed > 0 else 0
                            remaining_str = f"{int(remaining // 60)}m {int(remaining % 60)}s"
                            extra_info = f"| {speed:.1f} files/s | ETA: {remaining_str}"
                            progress_bar.update(self.processed_count, extra_info)
                except queue.Empty:
                    break
                except Exception:
                    # 确保任何一个任务的失败不会中断整个处理
                    pass

        # 启动工作线程
        threads = []
        for _ in range(self.num_threads):
            thread = threading.Thread(target=worker)
            thread.daemon = True
            thread.start()
            threads.append(thread)

        # 等待所有工作完成
        try:
            # 主线程监控进度并更新进度条
            while not work_queue.empty() and not self.cancelled:
                stats = self.stats.get_all()
                elapsed = time.time() - processing_start
                speed = self.processed_count / elapsed if elapsed > 0 else 0
                remaining = (total_files - self.processed_count) / speed if speed > 0 else 0
                remaining_str = f"{int(remaining // 60)}m {int(remaining % 60)}s"
                extra_info = f"| {speed:.1f} files/s | ETA: {remaining_str}"
                progress_bar.update(self.processed_count, extra_info)
                time.sleep(0.5)  # 减少CPU使用

            # 等待所有工作完成
            work_queue.join()
        except KeyboardInterrupt:
            # 允许用户中断处理
            self.cancelled = True
            print("\n操作被用户取消.")

        # 完成进度条
        progress_bar.complete()

        # 如果提取历史记录可用，保存它
        if self.download_history:
            self.download_history.save_history()

        # 计算结果统计
        total_time = time.time() - processing_start
        stats = self.stats.get_all()
        files_per_second = stats['processed_files'] / total_time if total_time > 0 else 0

        return {
            "processed": stats['processed_files'],
            "duplicates": stats['duplicate_files'],
            "already_processed": stats['already_processed'],
            "errors": stats['error_files'],
            "output_dir": self.output_dir,
            "duration": total_time,
            "files_per_second": files_per_second,
            "by_type": {
                "audio": stats['audio_files'],
                "images": stats['image_files'],
                "textures": stats['texture_files'],
                "models": stats['model_files']
            }
        }

    def detect_and_extract_file_content(self, file_path: str, content: bytes) -> Tuple[
        Optional[FileType], Optional[bytes]]:
        """检测文件类型并提取对应格式的内容"""
        # 检查每种文件类型并提取相应内容
        for file_type in self.extract_types:
            extracted_content = None

            if file_type == FileType.AUDIO_OGG:
                if b'OggS' in content:
                    extracted_content = self._extract_ogg_from_content(content)
            elif file_type == FileType.IMAGE_PNG:
                if b'PNG' in content or b'\x89PNG' in content:
                    extracted_content = self._extract_png_from_content(content)
            elif file_type == FileType.IMAGE_WEBP:
                if b'WEBP' in content:
                    extracted_content = self._extract_webp_from_content(content)
            elif file_type == FileType.TEXTURE_KTX:
                if b'KTX' in content:
                    extracted_content = self._extract_ktx_from_content(content)
            elif file_type == FileType.MODEL_RBXM:
                if b'<roblox!' in content.lower():
                    extracted_content = self._extract_rbxm_from_content(content)

            if extracted_content and len(extracted_content) > 10:  # 确保提取的内容有效
                return file_type, extracted_content

        return None, None

    def process_file(self, file_path: str) -> bool:
        """处理单个文件并提取资源"""
        if self.cancelled:
            return False

        try:
            # 计算文件哈希
            file_hash = self._get_file_hash(file_path)

            # 如果文件已经处理过了，则跳过
            if self.download_history and self.download_history.is_processed(file_hash):
                self.stats.increment('already_processed')
                return False

            # 尝试读取文件内容
            file_content = self._extract_file_content(file_path)
            if not file_content:
                return False

            # 检测文件类型并提取相应内容
            file_type, extracted_content = self.detect_and_extract_file_content(file_path, file_content)
            if not file_type or not extracted_content:
                return False

            # 计算内容哈希以检测重复
            content_hash = hashlib.md5(extracted_content).hexdigest()
            if self.hash_cache.is_duplicate(content_hash):
                self.stats.increment('duplicate_files')
                return False

            # 保存文件
            output_path = self._save_asset_file(file_path, extracted_content, file_type)
            if output_path:
                # 成功保存文件，增加处理计数
                self.stats.increment('processed_files')

                # 按类型统计
                if file_type == FileType.AUDIO_OGG:
                    self.stats.increment('audio_files')
                elif file_type in [FileType.IMAGE_PNG, FileType.IMAGE_WEBP]:
                    self.stats.increment('image_files')
                elif file_type == FileType.TEXTURE_KTX:
                    self.stats.increment('texture_files')
                elif file_type == FileType.MODEL_RBXM:
                    self.stats.increment('model_files')

                # 如果可用，将哈希添加到提取历史记录
                if self.download_history:
                    self.download_history.add_hash(file_hash)

                return True

            return False

        except Exception as e:
            # 增加错误计数
            self.stats.increment('error_files')
            # 将错误写入日志
            self._log_error(file_path, str(e))
            return False

    def _extract_file_content(self, file_path: str) -> Optional[bytes]:
        """提取文件中的资源内容并进行格式处理"""
        try:
            # 使用二进制模式打开文件
            with open(file_path, 'rb') as f:
                content = f.read()

            # 首先尝试解压（如果是gzip压缩）
            try:
                if gzip is None:
                    import_libs()
                decompressed = gzip.decompress(content)
                content = decompressed
            except Exception:
                # 如果解压失败，使用原始内容
                pass

            return content

        except Exception:
            return None

    def _extract_ogg_from_content(self, content: bytes) -> Optional[bytes]:
        """从内容中提取OGG音频数据"""
        # 查找OGG标记
        ogg_start = content.find(b'OggS')
        if ogg_start >= 0:
            return content[ogg_start:]
        return None

    def _extract_png_from_content(self, content: bytes) -> Optional[bytes]:
        """从内容中提取PNG图片数据"""
        # 查找PNG文件头
        png_start = content.find(b'\x89PNG')
        if png_start >= 0:
            # PNG文件头之后查找IEND块来确定文件结束
            iend_pos = content.find(b'IEND', png_start)
            if iend_pos >= 0:
                return content[png_start:iend_pos + 8]  # IEND + 4字节CRC
        return None

    def _extract_webp_from_content(self, content: bytes) -> Optional[bytes]:
        """从内容中提取WEBP图片数据"""
        # 查找WEBP标记
        webp_start = content.find(b'WEBP')
        if webp_start >= 0:
            # 查找RIFF头
            riff_start = content.rfind(b'RIFF', 0, webp_start)
            if riff_start >= 0:
                # 读取文件大小
                try:
                    file_size = int.from_bytes(content[riff_start + 4:riff_start + 8], 'little')
                    return content[riff_start:riff_start + file_size + 8]
                except:
                    # 如果无法确定大小，返回从RIFF开始的所有内容
                    return content[riff_start:]
        return None

    def _extract_ktx_from_content(self, content: bytes) -> Optional[bytes]:
        """从内容中提取KTX纹理数据"""
        # KTX文件头标识
        ktx_header = b'\xabKTX 11\xbb\r\n\x1a\n'
        ktx_start = content.find(ktx_header)
        if ktx_start >= 0:
            return content[ktx_start:]

        # 也检查简单的KTX标记
        ktx_start = content.find(b'KTX')
        if ktx_start >= 0:
            return content[ktx_start:]
        return None

    def _extract_rbxm_from_content(self, content: bytes) -> Optional[bytes]:
        """从内容中提取RBXM模型数据"""
        # 查找roblox标记
        roblox_start = content.lower().find(b'<roblox!')
        if roblox_start >= 0:
            return content[roblox_start:]
        return None

    def _get_audio_duration(self, file_path: str) -> float:
        """获取音频文件的时长（秒）"""
        try:
            if subprocess is None:
                import_libs()

            subprocess_flags = 0
            if os.name == 'nt':  # Windows
                subprocess_flags = subprocess.CREATE_NO_WINDOW

            # 使用ffprobe获取音频时长
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess_flags,
                text=True
            )

            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())

            return 0.0  # 默认时长为0，会被分类到最短的类别
        except Exception:
            return 0.0  # 如果获取失败，默认为0秒

    def _get_duration_category(self, file_path: str) -> str:
        """根据音频时长确定类别"""
        duration = self._get_audio_duration(file_path)

        for category, (min_duration, max_duration) in self.duration_categories.items():
            if min_duration <= duration < max_duration:
                return category

        # 默认类别：如果没有匹配项，分配到第一个类别
        return next(iter(self.duration_categories.keys()))

    def _get_size_category(self, file_size: int) -> str:
        """根据文件大小确定类别"""
        for category, (min_size, max_size) in self.size_categories.items():
            if min_size <= file_size < max_size:
                return category

        # 默认类别：如果没有匹配项，分配到第一个类别
        return next(iter(self.size_categories.keys()))

    def _get_type_category(self, file_type: FileType) -> str:
        """根据文件类型确定类别"""
        for category, types in self.type_categories.items():
            if file_type in types:
                return category

        # 默认返回第一个类别
        return next(iter(self.type_categories.keys()))

    def _get_format_category(self, file_type: FileType) -> str:
        """根据文件格式确定类别"""
        for category, types in self.format_categories.items():
            if file_type in types:
                return category

        # 默认返回第一个类别
        return next(iter(self.format_categories.keys()))

    def _save_asset_file(self, source_path: str, content: bytes, file_type: FileType) -> Optional[str]:
        """保存提取的资源文件"""
        try:
            # 生成临时文件名
            base_name = os.path.basename(source_path)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            if random is None:
                import_libs()
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))

            # 获取正确的文件扩展名
            extension = self.file_type_extensions[file_type]
            temp_name = f"temp_{base_name}_{timestamp}_{random_suffix}{extension}"
            temp_path = os.path.join(self.output_dir, temp_name)

            # 保存临时文件
            with open(temp_path, 'wb', buffering=1024 * 8) as f:
                f.write(content)

            # 确定分类类别
            if self.classification_method == ClassificationMethod.DURATION and file_type == FileType.AUDIO_OGG:
                # 按时长分类（仅音频）
                category = self._get_duration_category(temp_path)
            elif self.classification_method == ClassificationMethod.SIZE:
                # 按大小分类
                file_size = len(content)
                category = self._get_size_category(file_size)
            elif self.classification_method == ClassificationMethod.FORMAT:
                # 按格式分类
                category = self._get_format_category(file_type)
            else:
                # 按类型分类（默认）
                category = self._get_type_category(file_type)

            output_dir = self.category_dirs[category]

            # 生成最终文件名
            output_name = f"{base_name}_{timestamp}_{random_suffix}{extension}"
            output_path = os.path.join(output_dir, output_name)

            # 移动文件到正确的类别目录
            if shutil is None:
                import_libs()
            shutil.move(temp_path, output_path)

            return output_path

        except Exception as e:
            # 如果处理失败，删除临时文件
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            self._log_error(source_path, f"Failed to save file: {str(e)}")
            return None

    def _get_file_hash(self, file_path: str) -> str:
        """计算文件的哈希值"""
        # 使用文件路径和修改时间作为简单哈希，避免读取文件内容
        try:
            file_stat = os.stat(file_path)
            return hashlib.md5(f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}".encode()).hexdigest()
        except Exception:
            # 如果无法获取文件信息，使用文件路径
            return hashlib.md5(file_path.encode()).hexdigest()

    def _log_error(self, file_path: str, error_message: str) -> None:
        """记录处理错误 - 使用缓冲写入"""
        try:
            log_file = os.path.join(self.logs_dir, "extraction_errors.log")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with self.file_lock:
                with open(log_file, 'a', encoding='utf-8', buffering=8192) as f:
                    f.write(f"[{timestamp}] {file_path}: {error_message}\n")
        except Exception:
            pass  # 如果日志记录失败，则没有太大影响

    def create_readme(self) -> None:
        """创建README文件解释资源类别"""
        try:
            # 创建自述文件，解释不同的分类类别
            readme_path = os.path.join(self.output_dir, "README.txt")
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(f"{lang.get('readme_title')}\n")
                f.write("=" * 60 + "\n\n")

                # 添加分类方法信息
                if self.classification_method == ClassificationMethod.DURATION:
                    f.write(f"{lang.get('classification_method_used', lang.get('classification_by_duration'))}\n\n")
                    f.write(f"{lang.get('readme_duration_title')}\n\n")
                    f.write(
                        "1. ultra_short_0-5s     (0-5 seconds / 0-5秒)      - Sound effects, notification sounds / 音效、提示音\n")
                    f.write(
                        "2. short_5-15s          (5-15 seconds / 5-15秒)     - Short effects, alerts / 短音效、通知音\n")
                    f.write(
                        "3. medium_15-60s        (15-60 seconds / 15-60秒)   - Loop music, short BGM / 循环音乐、短背景音\n")
                    f.write(
                        "4. long_60-300s         (1-5 minutes / 1-5分钟)     - Full music, long BGM / 完整音乐、长背景音\n")
                    f.write("5. ultra_long_300s+     (5+ minutes / 5分钟以上)    - Long music, voice / 长音乐、语音\n\n")
                    f.write(
                        f"Note: Duration classification requires FFmpeg to be installed. / 注意：时长分类需要安装FFmpeg。\n")
                elif self.classification_method == ClassificationMethod.SIZE:
                    f.write(f"{lang.get('classification_method_used', lang.get('classification_by_size'))}\n\n")
                    f.write(f"{lang.get('readme_size_title')}\n\n")
                    f.write("1. ultra_small_0-50KB     (0-50KB)       - Very small files / 极小文件\n")
                    f.write("2. small_50-200KB         (50KB-200KB)   - Small files / 小型文件\n")
                    f.write("3. medium_200KB-1MB       (200KB-1MB)    - Medium size files / 中等大小文件\n")
                    f.write("4. large_1MB-5MB          (1MB-5MB)      - Large files / 大型文件\n")
                    f.write("5. ultra_large_5MB+       (5MB+)         - Very large files / 极大文件\n\n")
                elif self.classification_method == ClassificationMethod.FORMAT:
                    f.write(f"{lang.get('classification_method_used', 'by file format / 按文件格式')}\n\n")
                    f.write("File Format Categories / 文件格式分类:\n\n")
                    f.write("1. ogg_audio              - OGG audio files / OGG音频文件\n")
                    f.write("2. png_images             - PNG image files / PNG图片文件\n")
                    f.write("3. webp_images            - WEBP image files / WEBP图片文件\n")
                    f.write("4. ktx_textures           - KTX texture files / KTX纹理文件\n")
                    f.write("5. rbxm_models            - RBXM model files / RBXM模型文件\n\n")
                else:  # TYPE
                    f.write(f"{lang.get('classification_method_used', lang.get('classification_by_type'))}\n\n")
                    f.write(f"{lang.get('readme_type_title')}\n\n")
                    f.write("1. audio_ogg              - OGG audio files / OGG音频文件\n")
                    f.write("2. images                 - PNG and WEBP image files / PNG和WEBP图片文件\n")
                    f.write("3. textures_ktx           - KTX texture files / KTX纹理文件\n")
                    f.write("4. models_rbxm            - RBXM model files / RBXM模型文件\n\n")

                f.write(f"Extraction Time / 提取时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

                # 添加提取的文件类型信息
                f.write(f"\nExtracted Asset Types / 提取的资源类型:\n")
                for file_type in self.extract_types:
                    if file_type == FileType.AUDIO_OGG:
                        f.write("- Audio (OGG) / 音频 (OGG)\n")
                    elif file_type == FileType.IMAGE_PNG:
                        f.write("- Images (PNG) / 图片 (PNG)\n")
                    elif file_type == FileType.IMAGE_WEBP:
                        f.write("- Images (WEBP) / 图片 (WEBP)\n")
                    elif file_type == FileType.TEXTURE_KTX:
                        f.write("- Textures (KTX) / 纹理 (KTX)\n")
                    elif file_type == FileType.MODEL_RBXM:
                        f.write("- Models (RBXM) / 模型 (RBXM)\n")

        except Exception:
            pass  # 非关键操作


class MP3Converter:
    """将OGG文件转换为MP3，保持分类结构"""

    def __init__(self, input_dir: str, output_dir: str, num_threads: int = None):
        """初始化MP3转换器"""
        import_libs()  # 确保已导入所需库

        self.input_dir = input_dir
        self.output_dir = output_dir
        self.num_threads = num_threads or min(16, multiprocessing.cpu_count())
        self.stats = ProcessingStats()
        self.file_lock = threading.Lock()
        self.cancelled = False
        self.processed_count = 0

        # 缓存已经转换过的文件哈希
        self.converted_hashes = set()

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

    def find_ogg_files(self) -> List[str]:
        """查找所有OGG文件 - 使用os.scandir优化"""
        ogg_files = []

        def scan_directory(dir_path):
            try:
                with os.scandir(dir_path) as entries:
                    for entry in entries:
                        if entry.is_dir():
                            scan_directory(entry.path)
                        elif entry.is_file() and entry.name.lower().endswith('.ogg'):
                            ogg_files.append(entry.path)
            except (PermissionError, OSError):
                pass

        scan_directory(self.input_dir)
        return ogg_files

    def convert_all(self) -> Dict[str, Any]:
        """转换所有找到的OGG文件"""
        # 检查ffmpeg是否可用
        if not self._is_ffmpeg_available():
            return {
                "success": False,
                "error": lang.get("ffmpeg_not_installed")
            }

        # 查找所有的OGG文件
        ogg_files = self.find_ogg_files()

        if not ogg_files:
            return {
                "success": False,
                "error": lang.get("no_ogg_files")
            }

        # 创建相应的输出目录结构
        self._create_output_structure()

        # 重置统计
        self.stats.reset()
        self.converted_hashes.clear()
        self.processed_count = 0
        self.cancelled = False

        # 显示转换进度
        print(f"\n• {lang.get('mp3_conversion', len(ogg_files))}")

        # 创建进度条
        progress_bar = ProgressBar(len(ogg_files), title="Converting:", width=40)

        # 使用线程池处理文件
        start_time = time.time()

        # 创建工作队列
        work_queue = queue.Queue()

        # 填充工作队列
        for file_path in ogg_files:
            work_queue.put(file_path)

        # 创建工作线程
        def worker():
            while not self.cancelled:
                try:
                    # 从队列获取项目，如果队列为空5秒则退出
                    file_path = work_queue.get(timeout=5)
                    try:
                        self.convert_file(file_path)
                    finally:
                        work_queue.task_done()
                        # 更新进度
                        self.processed_count += 1
                        # 更新显示，无需频繁更新
                        if self.processed_count % 10 == 0:
                            stats = self.stats.get_all()
                            elapsed = time.time() - start_time
                            speed = self.processed_count / elapsed if elapsed > 0 else 0
                            remaining = (len(ogg_files) - self.processed_count) / speed if speed > 0 else 0
                            remaining_str = f"{int(remaining // 60)}m {int(remaining % 60)}s"
                            extra_info = f"| {speed:.1f} files/s | ETA: {remaining_str}"
                            progress_bar.update(self.processed_count, extra_info)
                except queue.Empty:
                    break
                except Exception:
                    # 确保任何一个任务的失败不会中断整个处理
                    pass

        # 启动工作线程
        threads = []
        for _ in range(self.num_threads):
            thread = threading.Thread(target=worker)
            thread.daemon = True
            thread.start()
            threads.append(thread)

        # 等待所有工作完成
        try:
            # 主线程监控进度并更新进度条
            while not work_queue.empty() and not self.cancelled:
                elapsed = time.time() - start_time
                speed = self.processed_count / elapsed if elapsed > 0 else 0
                remaining = (len(ogg_files) - self.processed_count) / speed if speed > 0 else 0
                remaining_str = f"{int(remaining // 60)}m {int(remaining % 60)}s"
                extra_info = f"| {speed:.1f} files/s | ETA: {remaining_str}"
                progress_bar.update(self.processed_count, extra_info)
                time.sleep(0.5)  # 减少CPU使用

            # 等待所有工作完成
            work_queue.join()
        except KeyboardInterrupt:
            # 允许用户中断处理
            self.cancelled = True
            print("\n操作被用户取消.")

        # 完成进度条
        progress_bar.complete()

        # 计算结果统计
        stats = self.stats.get_all()
        total_time = time.time() - start_time

        return {
            "success": True,
            "converted": stats['mp3_converted'],
            "skipped": stats['mp3_skipped'],
            "errors": stats['mp3_errors'],
            "total": len(ogg_files),
            "duration": total_time,
            "output_dir": self.output_dir
        }

    def convert_file(self, ogg_path: str) -> bool:
        """转换单个OGG文件为MP3，保持目录结构"""
        if self.cancelled:
            return False

        try:
            # 计算文件哈希以检测重复转换
            file_hash = self._get_file_hash(ogg_path)

            # 检查是否已转换
            with self.file_lock:
                if file_hash in self.converted_hashes:
                    self.stats.increment('mp3_skipped')
                    return False
                # 记录哈希
                self.converted_hashes.add(file_hash)

            # 获取相对输入路径以构建输出路径
            rel_path = os.path.relpath(ogg_path, self.input_dir)
            rel_dir = os.path.dirname(rel_path)
            basename = os.path.basename(ogg_path)
            basename_noext = os.path.splitext(basename)[0]

            # 为输出文件创建目录（保持分类结构）
            output_dir = os.path.join(self.output_dir, rel_dir)
            os.makedirs(output_dir, exist_ok=True)

            # 创建MP3文件名，保留原始格式
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            if random is None:
                import_libs()
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
            mp3_filename = f"{basename_noext}_{timestamp}_{random_suffix}.mp3"
            mp3_path = os.path.join(output_dir, mp3_filename)

            # 使用ffmpeg转换文件 - 使用更高效的参数
            try:
                subprocess_flags = 0
                if os.name == 'nt':  # Windows
                    if subprocess is None:
                        import_libs()
                    subprocess_flags = subprocess.CREATE_NO_WINDOW

                # 使用更好的ffmpeg参数 - 增加转换速度
                result = subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", ogg_path,
                     "-codec:a", "libmp3lame", "-qscale:a", "2", "-threads", "2", mp3_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    creationflags=subprocess_flags
                )
                # 转换成功
                self.stats.increment('mp3_converted')
                return True
            except subprocess.CalledProcessError as e:
                self.stats.increment('mp3_errors')
                self._log_error(ogg_path, f"Conversion failed: {e.stderr.decode('utf-8', errors='ignore')}")
                return False
        except Exception as e:
            self.stats.increment('mp3_errors')
            self._log_error(ogg_path, f"Unexpected error: {str(e)}")
            return False

    def _get_file_hash(self, file_path: str) -> str:
        """计算文件的哈希值"""
        # 使用文件路径和修改时间作为简单哈希，避免读取文件内容
        try:
            file_stat = os.stat(file_path)
            return hashlib.md5(f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}".encode()).hexdigest()
        except Exception:
            # 如果无法获取文件信息，使用文件路径
            return hashlib.md5(file_path.encode()).hexdigest()

    def _is_ffmpeg_available(self) -> bool:
        """检查ffmpeg是否可用"""
        try:
            if subprocess is None:
                import_libs()

            subprocess_flags = 0
            if os.name == 'nt':  # Windows
                subprocess_flags = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess_flags
            )
            return result.returncode == 0
        except Exception:
            return False

    def _create_output_structure(self) -> None:
        """创建与输入目录相对应的输出目录结构"""

        # 使用os.scandir优化性能
        def create_dirs(base_path, relative_path=""):
            full_input_path = os.path.join(base_path, relative_path)
            full_output_path = os.path.join(self.output_dir, relative_path)

            if relative_path:  # 避免创建根目录
                os.makedirs(full_output_path, exist_ok=True)

            try:
                with os.scandir(full_input_path) as entries:
                    for entry in entries:
                        if entry.is_dir():
                            new_rel_path = os.path.join(relative_path, entry.name)
                            create_dirs(base_path, new_rel_path)
            except (PermissionError, OSError):
                pass

        create_dirs(self.input_dir)

    def _log_error(self, file_path: str, error_message: str) -> None:
        """记录转换错误 - 使用缓冲写入"""
        try:
            log_dir = os.path.join(self.output_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "conversion_errors.log")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with self.file_lock:
                with open(log_file, 'a', encoding='utf-8', buffering=8192) as f:
                    f.write(f"[{timestamp}] {file_path}: {error_message}\n")
        except Exception:
            pass  # 如果日志记录失败，则没有太大影响


def open_directory(path: str) -> bool:
    """在文件资源管理器/Finder中打开目录"""
    try:
        if os.name == 'nt':  # Windows
            os.startfile(path)
        elif os.name == 'posix':  # macOS, Linux
            if sys.platform == 'darwin':  # macOS
                subprocess.call(['open', path])
            else:  # Linux
                subprocess.call(['xdg-open', path])
        return True
    except Exception:
        return False


class ConsoleRedirector:
    """控制台输出重定向器，将控制台输出重定向到 GUI 文本控件"""

    def __init__(self, text_widget, tag=None):
        """初始化重定向器"""
        self.text_widget = text_widget
        self.tag = tag
        self.buffer = ""
        self.buffer_size = 1024  # 缓冲区大小
        self.last_update = 0
        self.update_interval = 0.1  # 更新间隔时间(秒)

    def write(self, message):
        """写入消息到文本控件 - 使用缓冲和节流优化"""
        # 防止空消息
        if not message or message.isspace():
            return

        # 将消息添加到缓冲区
        self.buffer += message

        # 检查是否应该刷新缓冲区
        current_time = time.time()
        should_flush = (
                len(self.buffer) >= self.buffer_size or
                "\n" in self.buffer or
                (current_time - self.last_update) >= self.update_interval
        )

        if should_flush:
            # 更新界面必须在主线程中进行
            self.text_widget.insert(tk.END, self.buffer, self.tag)
            self.text_widget.see(tk.END)  # 自动滚动到最新内容
            self.text_widget.update_idletasks()  # 更轻量级的更新
            self.buffer = ""
            self.last_update = current_time

    def flush(self):
        """刷新输出（为兼容sys.stdout而需要）"""
        if self.buffer:
            self.text_widget.insert(tk.END, self.buffer, self.tag)
            self.text_widget.see(tk.END)
            self.text_widget.update_idletasks()
            self.buffer = ""


class GUILogger:
    """GUI 日志记录器，在 GUI 中显示日志消息并保持不同类型消息的格式"""

    def __init__(self, text_widget):
        """初始化日志记录器"""
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.running = True
        self.buffer = []  # 消息缓冲
        self.buffer_size = 10  # 批处理大小
        self.last_update = 0
        self.update_interval = 0.1  # 更新间隔(秒)

        # 配置文本标签
        self.text_widget.tag_configure("info", foreground="black")
        self.text_widget.tag_configure("success", foreground="green")
        self.text_widget.tag_configure("warning", foreground="orange")
        self.text_widget.tag_configure("error", foreground="red")

        # 启动处理线程
        self.thread = threading.Thread(target=self._process_queue)
        self.thread.daemon = True
        self.thread.start()

    def _process_queue(self):
        """处理消息队列 - 使用批处理减少UI更新"""
        batch = []
        while self.running:
            try:
                # 获取消息，有短暂超时以便可以退出循环
                message, tag = self.queue.get(timeout=0.1)
                batch.append((message, tag))

                # 尝试获取更多消息直到达到批处理大小或队列为空
                while len(batch) < self.buffer_size:
                    try:
                        message, tag = self.queue.get_nowait()
                        batch.append((message, tag))
                    except queue.Empty:
                        break

                # 处理批次
                if batch:
                    # 在主线程中更新 UI
                    self.text_widget.after(0, self._update_text_batch, batch)
                    batch = []

            except queue.Empty:
                # 如果队列为空但有待处理的消息，处理它们
                if batch:
                    self.text_widget.after(0, self._update_text_batch, batch)
                    batch = []
                continue

    def _update_text_batch(self, messages):
        """在主线程中批量更新文本控件"""
        for message, tag in messages:
            if not message.endswith('\n'):
                message += '\n'
            self.text_widget.insert(tk.END, message, tag)
        self.text_widget.see(tk.END)
        self.text_widget.update_idletasks()  # 更轻量级的更新

    def info(self, message):
        """记录信息消息"""
        self.queue.put((message, "info"))

    def success(self, message):
        """记录成功消息"""
        self.queue.put((message, "success"))

    def warning(self, message):
        """记录警告消息"""
        self.queue.put((message, "warning"))

    def error(self, message):
        """记录错误消息"""
        self.queue.put((message, "error"))

    def stop(self):
        """停止日志记录器"""
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=2)


class RobloxAssetExtractorGUI:
    """Roblox 资源提取器 GUI 界面"""

    def __init__(self, root):
        """初始化 GUI 界面"""
        # 延迟导入所需库，加快启动速度
        import_libs()

        # 全局引用
        self.root = root

        # 初始化语言管理器
        global lang
        lang = LanguageManager()

        # 获取默认目录
        self.default_dir = get_roblox_default_dir()

        # 设置提取历史记录文件
        app_data_dir = os.path.join(os.path.expanduser("~"), ".roblox_asset_extractor")
        os.makedirs(app_data_dir, exist_ok=True)
        history_file = os.path.join(app_data_dir, "extracted_history.json")

        # 初始化提取历史
        self.download_history = ExtractedHistory(history_file)

        # 设置主窗口属性
        self.root.title("Roblox Asset Extractor")
        self.root.geometry("1000x700")  # 增大窗口大小以容纳新功能
        self.root.minsize(950, 500)  # 最小窗口大小

        # 根据系统选择合适的字体
        def get_default_font():
            system = platform.system()
            if system == 'Windows':
                return ('Microsoft YaHei', 11)
            elif system == 'Darwin':  # macOS
                return ('Helvetica', 11)
            else:  # Linux 和其他
                return ('Ubuntu', 11)

        default_font = get_default_font()
        header_font = (default_font[0], 14, 'bold')

        # 应用样式
        style = ttk.Style()
        style.configure('TLabel', font=default_font)
        style.configure('TButton', font=default_font)
        style.configure('TFrame', background='#f5f5f5')
        style.configure('Header.TLabel', font=header_font)
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)



        # 创建主布局为左侧菜单和右侧内容
        self.content_frame = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # 创建左侧菜单框架
        self.menu_frame = ttk.Frame(self.content_frame, padding="5 5 5 5", width=200)
        self.content_frame.add(self.menu_frame, weight=1)

        # 创建右侧内容框架
        self.right_frame = ttk.Frame(self.content_frame, padding="5 5 5 5")
        self.content_frame.add(self.right_frame, weight=4)

        # 设置菜单按钮
        self.setup_menu()

        # 创建状态栏框架
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

        # 左侧状态信息
        self.status_bar = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 右侧系统信息框架
        info_frame = ttk.Frame(status_frame)
        info_frame.pack(side=tk.RIGHT)



        # GitHub链接
        self.github_label = ttk.Label(info_frame, text="GitHub Repository", foreground="blue", cursor="hand2")
        self.github_label.pack(side=tk.RIGHT, padx=(0, 10))
        self.github_label.bind("<Button-1>", self.open_github)

        # 系统时间
        self.time_label = ttk.Label(info_frame, text="", foreground="black")
        self.time_label.pack(side=tk.RIGHT, padx=(0, 10))

        # 启动时间更新
        self.update_time()

        # 初始化日志区域
        self.log_frame = ttk.LabelFrame(self.right_frame, text="Log")
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 初始化日志记录器
        self.gui_logger = GUILogger(self.log_text)

        # 设置重定向控制台输出
        self.original_stdout = sys.stdout
        sys.stdout = ConsoleRedirector(self.log_text, "info")

        # 设置本地化界面
        self.update_language()

        # 当前活动任务
        self.active_task = None
        self.task_cancelled = False

        # 分类方法和提取类型
        self.classification_method = ClassificationMethod.TYPE
        self.extract_types = {FileType.AUDIO_OGG, FileType.IMAGE_PNG, FileType.IMAGE_WEBP, FileType.TEXTURE_KTX,
                              FileType.MODEL_RBXM}

        # 显示欢迎消息
        self.gui_logger.info(lang.get('welcome_message'))
        self.gui_logger.info((lang.get('about_version')).strip())
        self.gui_logger.info((lang.get('default_dir') + ": " + self.default_dir).strip())

        # 当窗口关闭时恢复标准输出和停止所有任务
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_scrollable_frame(self, parent):
        """创建可滚动的框架，支持鼠标滚轮"""
        # 创建带滚动条的画布
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # 配置滚动
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # 在画布中创建窗口
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 打包元素
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 添加鼠标滚轮绑定
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # 不同操作系统的不同绑定
        if sys.platform.startswith("win"):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        elif sys.platform.startswith("darwin"):  # macOS
            canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * event.delta), "units"))
        else:  # Linux
            canvas.bind_all("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
            canvas.bind_all("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))

        return scrollable_frame

    def on_closing(self):
        """窗口关闭处理函数"""
        # 取消任何正在运行的任务
        self.cancel_active_task()

        # 恢复标准输出
        sys.stdout = self.original_stdout

        # 停止日志记录器
        self.gui_logger.stop()

        # 保存可能的历史更改
        if self.download_history and hasattr(self.download_history, 'modified') and self.download_history.modified:
            self.download_history.save_history()

        # 销毁窗口
        self.root.destroy()

    def setup_menu(self):
        """设置左侧菜单按钮"""
        # 菜单容器，使用垂直方向布局
        self.menu_buttons_frame = ttk.Frame(self.menu_frame)
        self.menu_buttons_frame.pack(fill=tk.Y, expand=False)

        # 创建菜单按钮
        self.btn_extract = ttk.Button(
            self.menu_buttons_frame,
            text="1. Extract Assets",
            command=self.show_extract_frame,
            width=25
        )
        self.btn_extract.pack(fill=tk.X, padx=5, pady=5)

        self.btn_clear_cache = ttk.Button(
            self.menu_buttons_frame,
            text=lang.get('clear_cache'),
            command=self.show_clear_cache_frame,
            width=25
        )
        self.btn_clear_cache.pack(fill=tk.X, padx=5, pady=5)

        self.btn_history = ttk.Button(
            self.menu_buttons_frame,
            text="3. View History",
            command=self.show_history_frame,
            width=25
        )
        self.btn_history.pack(fill=tk.X, padx=5, pady=5)

        self.btn_language = ttk.Button(
            self.menu_buttons_frame,
            text="4. Language Settings",
            command=self.show_language_frame,
            width=25
        )
        self.btn_language.pack(fill=tk.X, padx=5, pady=5)

        self.btn_about = ttk.Button(
            self.menu_buttons_frame,
            text="5. About",
            command=self.show_about_frame,
            width=25
        )
        self.btn_about.pack(fill=tk.X, padx=5, pady=5)

    def show_clear_cache_frame(self):
        """显示清除缓存界面"""
        # 清除右侧框架
        self.clear_right_frame()

        # 创建清除缓存框架
        cache_frame = ttk.LabelFrame(self.right_frame, text=lang.get('clear_cache'))
        cache_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)

        # 创建可滚动内容
        content_frame = self.create_scrollable_frame(cache_frame)

        # 添加说明文本
        ttk.Label(content_frame, text=lang.get('cache_description'),
                  wraplength=400).pack(anchor=tk.W, padx=10, pady=5)

        ttk.Label(content_frame, text=lang.get('cache_location') + f":\n{self.default_dir}",
                  wraplength=400).pack(anchor=tk.W, padx=10, pady=5)

        # 添加操作按钮
        clear_btn = ttk.Button(content_frame, text=lang.get('clear_cache'),
                               command=self.clear_asset_cache)
        clear_btn.pack(anchor=tk.CENTER, pady=10)

        # 显示日志框架
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def cancel_active_task(self):
        """取消活动任务"""
        if self.active_task is not None and self.active_task.is_alive():
            # 设置取消标志
            self.task_cancelled = True
            # 等待最多2秒让任务终止
            self.active_task.join(timeout=2)
            # 更新状态
            self.task_cancelled = False
            self.active_task = None
            self.gui_logger.warning(lang.get('canceled_by_user'))
            self.status_bar.config(text="Ready / 就绪")

    def update_language(self):
        """更新界面语言"""
        # 更新标题


        # 更新菜单按钮文本
        self.btn_extract.config(text=lang.get('extract_assets'))
        self.btn_history.config(text=lang.get('view_history'))
        self.btn_language.config(text=lang.get('language_settings'))
        self.btn_about.config(text=lang.get('about'))
        self.btn_clear_cache.config(text=lang.get('clear_cache'))

        # 更新状态栏
        self.status_bar.config(text="Ready / 就绪")

    def clear_right_frame(self):
        """清除右侧内容框架中的所有小部件"""
        # 取消任何正在运行的任务
        self.cancel_active_task()

        for widget in self.right_frame.winfo_children():
            widget.destroy()

        # 重新创建日志区域
        self.log_frame = ttk.LabelFrame(self.right_frame, text="Log")
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD, height=5)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 重新初始化日志记录器
        self.gui_logger = GUILogger(self.log_text)

        # 重设重定向控制台输出
        sys.stdout = ConsoleRedirector(self.log_text, "info")

    def show_extract_frame(self):
        """显示提取资源界面"""
        # 清除右侧框架
        self.clear_right_frame()

        # 创建提取资源框架
        extract_frame = ttk.LabelFrame(self.right_frame, text=lang.get('extract_assets'))
        extract_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)

        # 创建可滚动内容
        content_frame = self.create_scrollable_frame(extract_frame)

        # 目录选择
        dir_frame = ttk.Frame(content_frame)
        dir_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(dir_frame, text=lang.get('default_dir', '')).pack(side=tk.LEFT, padx=5)

        self.dir_var = tk.StringVar(value=self.default_dir)
        dir_entry = ttk.Entry(dir_frame, textvariable=self.dir_var, width=50)
        dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        browse_btn = ttk.Button(dir_frame, text="Browse...", command=self.browse_directory)
        browse_btn.pack(side=tk.LEFT, padx=5)

        # 资源类型选择
        asset_types_frame = ttk.LabelFrame(content_frame, text=lang.get('asset_types'))
        asset_types_frame.pack(fill=tk.X, padx=5, pady=5)

        # 创建复选框变量
        self.extract_audio_var = tk.BooleanVar(value=True)
        self.extract_images_var = tk.BooleanVar(value=True)
        self.extract_textures_var = tk.BooleanVar(value=True)
        self.extract_models_var = tk.BooleanVar(value=True)

        # 创建复选框
        ttk.Checkbutton(
            asset_types_frame,
            text=lang.get('extract_audio'),
            variable=self.extract_audio_var
        ).pack(anchor=tk.W, padx=10, pady=2)

        ttk.Checkbutton(
            asset_types_frame,
            text=lang.get('extract_images'),
            variable=self.extract_images_var
        ).pack(anchor=tk.W, padx=10, pady=2)

        ttk.Checkbutton(
            asset_types_frame,
            text=lang.get('extract_textures'),
            variable=self.extract_textures_var
        ).pack(anchor=tk.W, padx=10, pady=2)

        ttk.Checkbutton(
            asset_types_frame,
            text=lang.get('extract_models'),
            variable=self.extract_models_var
        ).pack(anchor=tk.W, padx=10, pady=2)

        # 分类方法选择
        classification_frame = ttk.LabelFrame(content_frame, text=lang.get('classification_method'))
        classification_frame.pack(fill=tk.X, padx=5, pady=5)

        self.classification_var = tk.StringVar(value="type")

        # 创建单选按钮
        ttk.Radiobutton(
            classification_frame,
            text=lang.get('classify_by_type'),
            variable=self.classification_var,
            value="type",
            command=self.update_classification_info
        ).pack(anchor=tk.W, padx=10, pady=2)

        # 音频专用分类方法
        audio_frame = ttk.LabelFrame(classification_frame, text="Audio Specific / 音频专用")
        audio_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Radiobutton(
            audio_frame,
            text=lang.get('classify_by_duration'),
            variable=self.classification_var,
            value="duration",
            command=self.update_classification_info
        ).pack(anchor=tk.W, padx=10, pady=2)

        # 通用分类方法
        general_frame = ttk.LabelFrame(classification_frame, text="General / 通用")
        general_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Radiobutton(
            general_frame,
            text=lang.get('classify_by_size'),
            variable=self.classification_var,
            value="size",
            command=self.update_classification_info
        ).pack(anchor=tk.W, padx=10, pady=2)

        # 详细分类选项
        detail_frame = ttk.LabelFrame(classification_frame, text="Detailed Classification / 详细分类")
        detail_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Radiobutton(
            detail_frame,
            text="By file format (PNG/WEBP separate) / 按文件格式（PNG/WEBP分开）",
            variable=self.classification_var,
            value="format",
            command=self.update_classification_info
        ).pack(anchor=tk.W, padx=10, pady=2)

        # 检查FFmpeg是否可用
        if not self._is_ffmpeg_available():
            ttk.Label(
                audio_frame,
                text=lang.get('ffmpeg_not_found_warning'),
                foreground="red"
            ).pack(anchor=tk.W, padx=10, pady=2)

        # 处理选项
        self.options_frame = ttk.LabelFrame(content_frame, text=lang.get('processing_info'))
        self.options_frame.pack(fill=tk.X, padx=5, pady=5)

        # 动态显示分类信息
        self.classification_info_label = ttk.Label(self.options_frame, text=lang.get('type_classification_info'))
        self.classification_info_label.pack(anchor=tk.W, padx=5, pady=2)

        ttk.Label(self.options_frame, text=lang.get('info_mp3_conversion')).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(self.options_frame, text=lang.get('info_skip_downloaded')).pack(anchor=tk.W, padx=5, pady=2)

        # 线程设置
        threads_frame = ttk.Frame(content_frame)
        threads_frame.pack(fill=tk.X, padx=5, pady=5)

        default_threads = min(32, multiprocessing.cpu_count() * 2)
        ttk.Label(threads_frame, text=lang.get('threads_prompt', default_threads).split(':')[0] + ':').pack(
            side=tk.LEFT, padx=5)

        self.threads_var = tk.StringVar(value=str(default_threads))
        threads_spinbox = ttk.Spinbox(threads_frame, from_=1, to=64, textvariable=self.threads_var, width=5)
        threads_spinbox.pack(side=tk.LEFT, padx=5)

        # MP3 转换选项（仅音频）
        convert_frame = ttk.Frame(content_frame)
        convert_frame.pack(fill=tk.X, padx=5, pady=5)

        self.convert_mp3_var = tk.BooleanVar(value=True)
        convert_check = ttk.Checkbutton(convert_frame, text=lang.get('convert_to_mp3_prompt').replace("?", ""),
                                        variable=self.convert_mp3_var)
        convert_check.pack(anchor=tk.W, padx=5)

        # 操作按钮
        buttons_frame = ttk.Frame(content_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=10)

        self.extract_btn = ttk.Button(buttons_frame, text=lang.get('extract_assets'), command=self.start_extraction)
        self.extract_btn.pack(side=tk.RIGHT, padx=5)

        # 进度条
        self.progress_frame = ttk.Frame(content_frame)
        self.progress_frame.pack(fill=tk.X, padx=5, pady=5)

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)

        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack(anchor=tk.W, padx=5)

        # 显示日志框架
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def update_time(self):
        """更新系统时间显示"""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        # 每秒更新一次
        self.root.after(1000, self.update_time)

    def open_github(self, event):
        """打开GitHub仓库"""
        import webbrowser
        webbrowser.open("https://github.com/JustKanade/Roblox-Audio-Extractor")

    def update_classification_info(self):
        """根据所选分类方法更新显示信息"""
        selected = self.classification_var.get()

        if selected == "duration":
            self.classification_method = ClassificationMethod.DURATION
            self.classification_info_label.config(text=lang.get('duration_classification_info'))
        elif selected == "size":
            self.classification_method = ClassificationMethod.SIZE
            self.classification_info_label.config(text=lang.get('size_classification_info'))
        elif selected == "format":
            self.classification_method = ClassificationMethod.FORMAT
            self.classification_info_label.config(
                text="• Files will be organized by specific format: OGG, PNG, WEBP, KTX, RBXM / • 文件将按具体格式分类: OGG, PNG, WEBP, KTX, RBXM")
        else:  # type
            self.classification_method = ClassificationMethod.TYPE
            self.classification_info_label.config(text=lang.get('type_classification_info'))

    def _is_ffmpeg_available(self) -> bool:
        """检查FFmpeg是否可用"""
        try:
            if subprocess is None:
                import_libs()

            subprocess_flags = 0
            if os.name == 'nt':  # Windows
                subprocess_flags = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess_flags
            )
            return result.returncode == 0
        except Exception:
            return False

    def clear_asset_cache(self):
        """清除资源缓存文件"""
        try:
            # 确认对话框
            if not messagebox.askyesno(
                    lang.get('clear_cache'),
                    lang.get('confirm_clear_cache')
            ):
                self.gui_logger.info(lang.get('operation_cancelled'))
                return

            # 计数器
            total_files = 0
            cleared_files = 0

            # 需要排除的文件夹
            exclude_dirs = {'extracted_assets', 'extracted_mp3', 'extracted_oggs'}

            self.gui_logger.info("开始清除资源缓存文件... / Starting to clear asset cache files...")

            # 递归搜索所有文件
            for root, dirs, files in os.walk(self.default_dir):
                # 跳过排除的目录 - 检查路径中是否包含排除的目录名
                if any(excluded in root for excluded in exclude_dirs):
                    continue

                # 也从dirs列表中移除排除的目录，防止os.walk进入这些目录
                dirs[:] = [d for d in dirs if d not in exclude_dirs]

                for file in files:
                    file_path = os.path.join(root, file)
                    total_files += 1

                    try:
                        # 读取文件的前8KB内容
                        with open(file_path, 'rb') as f:
                            content = f.read(8192)

                        # 检查各种资源文件头或其他标识
                        if (b'OggS' in content or  # OGG音频标识
                                b'PNG' in content or  # PNG图片标识
                                b'WEBP' in content or  # WEBP图片标识
                                b'KTX' in content or  # KTX纹理标识
                                b'<roblox!' in content.lower() or  # RBXM模型标识
                                b'.ogg' in content.lower() or  # .ogg扩展名
                                b'.png' in content.lower() or  # .png扩展名
                                b'.webp' in content.lower() or  # .webp扩展名
                                b'.ktx' in content.lower() or  # .ktx扩展名
                                b'.rbxm' in content.lower() or  # .rbxm扩展名
                                b'audio' in content.lower() or  # 音频关键字
                                b'sound' in content.lower() or  # 声音关键字
                                b'image' in content.lower() or  # 图片关键字
                                b'texture' in content.lower() or  # 纹理关键字
                                b'model' in content.lower()):  # 模型关键字

                            # 删除文件
                            os.remove(file_path)
                            cleared_files += 1

                    except (IOError, OSError, PermissionError):
                        continue

            # 显示结果
            self.gui_logger.success(lang.get('cache_cleared', cleared_files, total_files))
            self.gui_logger.info(f"排除的文件夹 / Excluded folders: {', '.join(exclude_dirs)}")
        except Exception as e:
            self.gui_logger.error(lang.get('clear_cache_failed', str(e)))

    def browse_directory(self):
        """浏览并选择目录"""
        directory = filedialog.askdirectory(initialdir=self.dir_var.get())
        if directory:
            self.dir_var.set(directory)

    def start_extraction(self):
        """开始提取资源文件"""
        # 获取用户选择的目录
        selected_dir = self.dir_var.get()

        # 检查目录是否存在
        if not os.path.exists(selected_dir):
            result = messagebox.askquestion(
                "Directory not found",
                lang.get('dir_not_exist', selected_dir) + "\n" + lang.get('create_dir_prompt'),
                icon='warning'
            )

            if result == 'yes':
                try:
                    os.makedirs(selected_dir, exist_ok=True)
                    self.gui_logger.success(lang.get('dir_created', selected_dir))
                except Exception as e:
                    self.gui_logger.error(lang.get('dir_create_failed', str(e)))
                    return
            else:
                self.gui_logger.warning(lang.get('operation_cancelled'))
                return

        # 获取要提取的资源类型
        extract_types = set()
        if self.extract_audio_var.get():
            extract_types.add(FileType.AUDIO_OGG)
        if self.extract_images_var.get():
            extract_types.add(FileType.IMAGE_PNG)
            extract_types.add(FileType.IMAGE_WEBP)
        if self.extract_textures_var.get():
            extract_types.add(FileType.TEXTURE_KTX)
        if self.extract_models_var.get():
            extract_types.add(FileType.MODEL_RBXM)

        if not extract_types:
            self.gui_logger.warning("Please select at least one asset type to extract / 请至少选择一种要提取的资源类型")
            return

        # 获取线程数
        try:
            num_threads = int(self.threads_var.get())
            if num_threads < 1:
                self.gui_logger.warning(lang.get('threads_min_error'))
                num_threads = min(32, multiprocessing.cpu_count() * 2)
                self.threads_var.set(str(num_threads))

            if num_threads > 64:
                result = messagebox.askquestion(
                    "Warning",
                    lang.get('threads_high_warning') + "\n" + lang.get('confirm_high_threads'),
                    icon='warning'
                )

                if result != 'yes':
                    num_threads = min(32, multiprocessing.cpu_count() * 2)
                    self.threads_var.set(str(num_threads))
                    self.gui_logger.info(lang.get('threads_adjusted', num_threads))
        except ValueError:
            self.gui_logger.warning(lang.get('input_invalid'))
            num_threads = min(32, multiprocessing.cpu_count() * 2)
            self.threads_var.set(str(num_threads))

        # 获取分类方法
        classification_method = ClassificationMethod.TYPE
        if self.classification_var.get() == "duration":
            classification_method = ClassificationMethod.DURATION
        elif self.classification_var.get() == "size":
            classification_method = ClassificationMethod.SIZE
        elif self.classification_var.get() == "format":
            classification_method = ClassificationMethod.FORMAT

        # 如果选择时长分类但没有ffmpeg，显示警告
        if classification_method == ClassificationMethod.DURATION and not self._is_ffmpeg_available():
            result = messagebox.askquestion(
                "Warning",
                lang.get('ffmpeg_not_installed') + "\n\nContinue anyway? / 仍要继续吗?",
                icon='warning'
            )
            if result != 'yes':
                self.gui_logger.warning(lang.get('operation_cancelled'))
                return

        # 创建并启动提取线程
        self.task_cancelled = False
        self.active_task = threading.Thread(target=self.run_extraction_process,
                                            args=(selected_dir, num_threads, classification_method, extract_types))
        self.active_task.daemon = True
        self.active_task.start()

    def run_extraction_process(self, selected_dir, num_threads, classification_method, extract_types):
        """运行提取过程"""
        try:
            # 更新状态栏
            self.status_bar.config(text=lang.get('scanning_files'))

            # 初始化并运行提取器
            start_time = time.time()
            extractor = RobloxAssetExtractor(selected_dir, num_threads,
                                             self.download_history, classification_method, extract_types)

            # 覆盖extractor的cancelled属性，使其检查self.task_cancelled的当前值
            def is_cancelled():
                return self.task_cancelled

            extractor.cancelled = is_cancelled

            # 显示正在扫描文件的消息
            self.gui_logger.info(lang.get('scanning_files'))

            # 查找要处理的文件
            files_to_process = extractor.find_files_to_process()
            total_files = len(files_to_process)

            scan_duration = time.time() - start_time
            self.gui_logger.info(lang.get('found_files', total_files, scan_duration))

            if not files_to_process:
                self.gui_logger.warning(lang.get('no_files_found'))
                self.status_bar.config(text="Ready / 就绪")
                self.extract_btn.configure(state='normal')
                self.active_task = None
                return

            # 设置进度更新
            self.processed_count = 0

            # 创建一个周期性的进度更新函数
            def update_progress():
                if self.task_cancelled:
                    return

                # 计算进度百分比
                progress = min(100, int((self.processed_count / total_files) * 100)) if total_files > 0 else 0

                # 计算剩余时间
                elapsed = time.time() - start_time
                speed = self.processed_count / elapsed if elapsed > 0 else 0
                remaining = (total_files - self.processed_count) / speed if speed > 0 else 0
                remaining_str = f"{int(remaining // 60)}m {int(remaining % 60)}s"

                # 构建状态文本
                status_text = f"{progress}% - {self.processed_count}/{total_files} | {speed:.1f} files/s | ETA: {remaining_str}"

                # 更新UI
                self.progress_var.set(progress)
                self.progress_label.config(text=status_text)

                # 如果仍在处理，继续更新
                if self.processed_count < total_files and not self.task_cancelled and self.active_task and self.active_task.is_alive():
                    self.root.after(100, update_progress)

            # 替换extractor的process_file方法来跟踪进度
            original_process_file = extractor.process_file

            def process_file_with_progress(file_path):
                result = original_process_file(file_path)
                self.processed_count += 1
                return result

            extractor.process_file = process_file_with_progress

            # 启动进度更新
            self.root.after(100, update_progress)

            # 更新状态栏
            self.status_bar.config(text=lang.get('processing_with_threads', num_threads))

            # 处理文件
            extraction_result = extractor.process_files()

            # 显示提取结果
            output_dir = extraction_result["output_dir"]
            if extraction_result["processed"] > 0:
                self.gui_logger.success(lang.get('extraction_complete'))
                self.gui_logger.info(lang.get('processed', extraction_result['processed']))
                self.gui_logger.info(lang.get('skipped_duplicates', extraction_result['duplicates']))
                self.gui_logger.info(lang.get('skipped_already_processed', extraction_result['already_processed']))
                self.gui_logger.info(lang.get('errors', extraction_result['errors']))
                self.gui_logger.info(lang.get('time_spent', extraction_result['duration']))
                self.gui_logger.info(lang.get('files_per_sec', extraction_result['files_per_second']))
                self.gui_logger.info(lang.get('output_dir', output_dir))

                # 显示按类型统计
                by_type = extraction_result['by_type']
                if by_type['audio'] > 0:
                    self.gui_logger.info(f"Audio files / 音频文件: {by_type['audio']}")
                if by_type['images'] > 0:
                    self.gui_logger.info(f"Image files / 图片文件: {by_type['images']}")
                if by_type['textures'] > 0:
                    self.gui_logger.info(f"Texture files / 纹理文件: {by_type['textures']}")
                if by_type['models'] > 0:
                    self.gui_logger.info(f"Model files / 模型文件: {by_type['models']}")

                # 询问用户是否要转换为MP3（仅音频）
                convert_to_mp3 = self.convert_mp3_var.get() and by_type['audio'] > 0

                mp3_dir = None
                if convert_to_mp3 and not self.task_cancelled:
                    self.gui_logger.info(lang.get('mp3_conversion_info'))
                    mp3_dir = os.path.join(selected_dir, "extracted_mp3")
                    mp3_converter = MP3Converter(output_dir, mp3_dir, num_threads)

                    # 设置MP3转换器的取消参数
                    def mp3_is_cancelled():
                        return self.task_cancelled

                    mp3_converter.cancelled = mp3_is_cancelled

                    # 运行MP3转换
                    self.run_mp3_conversion(mp3_converter)

                # 打开输出目录
                final_dir = mp3_dir if convert_to_mp3 and mp3_dir and hasattr(self,
                                                                              'mp3_result') and self.mp3_result.get(
                    "success") else output_dir

                # 使用基于平台的方法打开目录
                if not self.task_cancelled:
                    try:
                        if os.name == 'nt':
                            os.startfile(final_dir)
                        elif sys.platform == 'darwin':
                            subprocess.call(['open', final_dir])
                        else:
                            subprocess.call(['xdg-open', final_dir])

                        self.gui_logger.info(lang.get('opening_output_dir',
                                                      "MP3" if convert_to_mp3 and mp3_dir and hasattr(self,
                                                                                                      'mp3_result') and self.mp3_result.get(
                                                          "success") else "Assets"))
                    except Exception as e:
                        self.gui_logger.error(f"Failed to open directory: {str(e)}")
            else:
                self.gui_logger.warning(lang.get('no_files_processed'))

            # 更新状态栏
            self.status_bar.config(text="Ready / 就绪")
        except Exception as e:
            self.gui_logger.error(lang.get('error_occurred', str(e)))
            self.gui_logger.error(traceback.format_exc())
            self.status_bar.config(text="Error / 错误")
        finally:
            # 确保提取按钮重新启用
            self.extract_btn.configure(state='normal')
            self.active_task = None

    def run_mp3_conversion(self, mp3_converter):
        """运行MP3转换"""
        try:
            # 转换所有找到的OGG文件
            mp3_result = mp3_converter.convert_all()
            self.mp3_result = mp3_result

            # 显示转换结果
            if mp3_result["success"]:
                self.gui_logger.success(lang.get('mp3_conversion_complete'))
                self.gui_logger.info(lang.get('converted', mp3_result['converted'], mp3_result['total']))
                self.gui_logger.info(f"Skipped duplicates: {mp3_result['skipped']} files")
                self.gui_logger.info(f"Errors: {mp3_result['errors']} files")
                self.gui_logger.info(f"Total time: {mp3_result['duration']:.2f} seconds")
            else:
                self.gui_logger.error(mp3_result['error'])
        except Exception as e:
            self.gui_logger.error(lang.get('mp3_conversion_failed', str(e)))

    def show_history_frame(self):
        """显示提取历史界面"""
        # 清除右侧框架
        self.clear_right_frame()

        # 创建历史框架
        history_frame = ttk.LabelFrame(self.right_frame, text=lang.get('history_stats'))
        history_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)

        # 创建可滚动内容
        content_frame = self.create_scrollable_frame(history_frame)

        # 获取历史数据
        history_size = self.download_history.get_history_size()

        # 显示历史统计信息
        ttk.Label(content_frame, text=lang.get('files_recorded', history_size)).pack(anchor=tk.W, padx=10, pady=5)

        if history_size > 0:
            history_file = os.path.join(os.path.expanduser("~"), ".roblox_asset_extractor", "extracted_history.json")
            ttk.Label(content_frame, text=lang.get('history_file_location', history_file)).pack(anchor=tk.W, padx=10,
                                                                                                pady=5)

        # 操作按钮
        buttons_frame = ttk.Frame(content_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=10)

        clear_btn = ttk.Button(buttons_frame, text=lang.get('clear_history'), command=self.clear_history)
        clear_btn.pack(side=tk.RIGHT, padx=5)

        # 显示日志框架
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 显示历史信息
        self.gui_logger.info(lang.get('history_stats'))
        self.gui_logger.info(lang.get('files_recorded', history_size))

        if history_size > 0:
            self.gui_logger.info(lang.get('history_file_location', history_file))

    def clear_history(self):
        """清除提取历史"""
        # 显示确认对话框
        result = messagebox.askquestion(
            lang.get('clear_history'),
            lang.get('confirm_clear_history'),
            icon='warning'
        )

        if result == 'yes':
            try:
                # 获取历史文件路径并创建空历史文件
                history_file = self.download_history.history_file
                with open(history_file, 'w') as f:
                    f.write("[]")

                # 显示成功消息（使用messagebox避免使用可能被销毁的日志控件）
                messagebox.showinfo("", lang.get('history_cleared'))

                # 完全重新启动UI
                self.root.after(100, lambda: self._restart_history_view(history_file))

            except Exception as e:
                messagebox.showerror("Error", f"Error clearing history: {str(e)}")
                traceback.print_exc()
        else:
            messagebox.showinfo("Cancelled", lang.get('operation_cancelled'))

    def _restart_history_view(self, history_file):
        """完全重启历史视图"""
        # 停止当前日志记录器
        if hasattr(self, 'gui_logger') and self.gui_logger:
            try:
                self.gui_logger.running = False
            except:
                pass

        # 恢复原始stdout
        sys.stdout = self.original_stdout

        # 重新创建历史对象
        self.download_history = ExtractedHistory(history_file)

        # 清除右侧内容并重新显示历史界面
        for widget in self.right_frame.winfo_children():
            widget.destroy()

        self.show_history_frame()

    def show_language_frame(self):
        """显示语言设置界面"""
        # 清除右侧框架
        self.clear_right_frame()

        # 创建语言设置框架
        language_frame = ttk.LabelFrame(self.right_frame, text=lang.get('language_settings'))
        language_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)

        # 创建可滚动内容
        content_frame = self.create_scrollable_frame(language_frame)

        # 显示当前语言
        ttk.Label(content_frame, text=lang.get('current_language', lang.get_language_name())).pack(anchor=tk.W,
                                                                                                   padx=10, pady=10)

        # 语言选择
        select_frame = ttk.Frame(content_frame)
        select_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(select_frame, text=lang.get('select_language').split(':')[0] + ':').pack(side=tk.LEFT, padx=5)

        self.lang_var = tk.StringVar()
        self.lang_var.set("2" if lang.current_language == Language.ENGLISH else "1")

        chinese_radio = ttk.Radiobutton(select_frame, text="中文", variable=self.lang_var, value="1")
        chinese_radio.pack(side=tk.LEFT, padx=20)

        english_radio = ttk.Radiobutton(select_frame, text="English", variable=self.lang_var, value="2")
        english_radio.pack(side=tk.LEFT, padx=20)

        # 操作按钮
        buttons_frame = ttk.Frame(content_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=10)

        apply_btn = ttk.Button(buttons_frame, text="Apply / 应用", command=self.apply_language)
        apply_btn.pack(side=tk.RIGHT, padx=5)

        # 显示日志框架
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def apply_language(self):
        """应用语言设置"""
        choice = self.lang_var.get()

        if choice == "1":
            lang.set_language(Language.CHINESE)

        elif choice == "2":
            lang.set_language(Language.ENGLISH)

        # 更新界面语言
        self.update_language()

        # 刷新当前界面
        self.show_language_frame()

        # 显示语言已更改消息
        self.gui_logger.success(lang.get('language_set', lang.get_language_name()))

    def show_about_frame(self):
        """显示关于界面"""
        # 清除右侧框架
        self.clear_right_frame()

        # 创建关于框架
        about_frame = ttk.LabelFrame(self.right_frame, text=lang.get('about_title'))
        about_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)

        # 创建可滚动内容
        content_frame = self.create_scrollable_frame(about_frame)

        # 创建顶部框架来显示图标和标题
        top_frame = ttk.Frame(content_frame)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        # 加载并显示图标
        try:
            if sys.platform.startswith("win"):
                # Windows: 使用PhotoImage加载ico文件
                from PIL import Image, ImageTk
                icon = Image.open(resource_path(os.path.join(".readme", "ui-images", "Roblox-Audio-Extractor.ico")))
                app_icon = ImageTk.PhotoImage(icon)

            # 创建标签显示图标
            icon_label = ttk.Label(top_frame, image=app_icon)
            icon_label.image = app_icon  # 保持引用以防止被垃圾回收
            icon_label.pack(side=tk.LEFT, padx=10)

            # 创建标题标签
            title_label = ttk.Label(top_frame, text="Roblox Asset Extractor (Enhanced Version)",
                                    font=("Arial", 16, "bold"))
            title_label.pack(side=tk.LEFT, padx=10)

        except Exception as e:
            # 如果无法加载图标，只显示标题
            title_label = ttk.Label(top_frame, text="Roblox Asset Extractor (Enhanced Version)",
                                    font=("Arial", 16, "bold"))
            title_label.pack(side=tk.LEFT, padx=10)

        # 关于信息
        ttk.Label(content_frame,
                  text=lang.get('about_info'),
                  wraplength=600).pack(anchor=tk.W, padx=10, pady=5)
        ttk.Label(content_frame, text=lang.get('about_version')).pack(anchor=tk.W, padx=10, pady=5)
        ttk.Label(content_frame, text=lang.get('Creators & Contributors')).pack(anchor=tk.W, padx=10, pady=5)

        # 分隔线
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)

        # 显示支持的文件类型信息
        file_types_frame = ttk.LabelFrame(content_frame, text="Supported Asset Types / 支持的资源类型")
        file_types_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(file_types_frame, text="Audio Files / 音频文件: OGG format",
                  wraplength=600).pack(anchor=tk.W, padx=10, pady=2)
        ttk.Label(file_types_frame, text="Image Files / 图片文件: PNG, WEBP formats",
                  wraplength=600).pack(anchor=tk.W, padx=10, pady=2)
        ttk.Label(file_types_frame, text="Texture Files / 纹理文件: KTX format",
                  wraplength=600).pack(anchor=tk.W, padx=10, pady=2)
        ttk.Label(file_types_frame, text="Model Files / 模型文件: RBXM format",
                  wraplength=600).pack(anchor=tk.W, padx=10, pady=2)

        # 分隔线
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)

        # 链接和许可信息
        ttk.Label(content_frame, text="GitHub: https://github.com/JustKanade/Roblox-Audio-Extractor").pack(anchor=tk.W,
                                                                                                           padx=10,
                                                                                                           pady=5)
        ttk.Label(content_frame, text="License: GNU Affero General Public License v3.0 (AGPLv3)").pack(anchor=tk.W,
                                                                                                       padx=10, pady=5)

        # 显示内存使用情况
        try:
            # 动态导入psutil (如果可用)
            try:
                import psutil
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024  # 转换为MB

                ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)
                ttk.Label(content_frame, text=f"Current memory usage: {memory_mb:.2f} MB").pack(anchor=tk.W, padx=10,
                                                                                                pady=5)
            except ImportError:
                pass
        except:
            pass

        # 显示日志框架
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)


def main():
    """主函数 - 程序入口点，使用 GUI 界面"""
    try:
        # 创建并运行 GUI 应用程序
        root = tk.Tk()
        # 根据操作系统设置应用程序图标
        try:
            if sys.platform.startswith("win"):  # Windows
                root.iconbitmap(resource_path(os.path.join(".readme", "ui-images", "Roblox-Audio-Extractor.ico")))
            elif sys.platform == "darwin":  # macOS
                # macOS 不支持 .ico 格式，可以使用 .icns 或其他支持的格式
                root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(
                    file=resource_path(os.path.join(".readme", "ui-images", "Roblox-Audio-Extractor.png"))))
            else:  # Linux 或其他
                root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(
                    file=resource_path(os.path.join(".readme", "ui-images", "Roblox-Audio-Extractor.png"))))
        except Exception as e:
            print(f"无法设置图标: {e}")

        app = RobloxAssetExtractorGUI(root)
        root.mainloop()

        return 0
    except Exception as e:
        print(f"程序出错: {e}")
        return 1
    except Exception as e:
        # 显示错误消息
        traceback.print_exc()
        messagebox.showerror("Error", f"An error occurred: {str(e)}")
        return 1


if __name__ == "__main__":
    # 初始化语言管理器
    lang = LanguageManager()

    try:
        sys.exit(main())
    except Exception as e:
        # 在终端模式下记录错误
        logger.error(f"An error occurred: {str(e)}")
        traceback.print_exc()

        # 在 GUI 模式下显示错误对话框
        try:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        except:
            pass

        input("\n> Press Enter to continue...")
        sys.exit(1)
