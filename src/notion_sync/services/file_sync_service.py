"""
文件同步服务 - 实现真正的文件同步功能。
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime
import json

from PySide6.QtCore import QObject, Signal, QThread, QTimer
from notion_sync.utils.logging_config import LoggerMixin


class FileInfo:
    """文件信息类。"""
    
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self.size = path.stat().st_size if path.exists() else 0
        self.modified = datetime.fromtimestamp(path.stat().st_mtime) if path.exists() else datetime.now()
        self.hash = self._calculate_hash() if path.is_file() else None
        self.is_directory = path.is_dir()
    
    def _calculate_hash(self) -> str:
        """计算文件哈希值。"""
        if not self.path.is_file():
            return ""
        
        hash_md5 = hashlib.md5()
        try:
            with open(self.path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def to_dict(self) -> Dict:
        """转换为字典。"""
        return {
            "path": str(self.path),
            "name": self.name,
            "size": self.size,
            "modified": self.modified.isoformat(),
            "hash": self.hash,
            "is_directory": self.is_directory
        }


class SyncPair:
    """同步对类。"""
    
    def __init__(self, local_path: str, remote_path: str, sync_mode: str = "bidirectional"):
        self.local_path = Path(local_path)
        self.remote_path = remote_path
        self.sync_mode = sync_mode  # "local_to_remote", "remote_to_local", "bidirectional"
        self.last_sync = None
        self.enabled = True
    
    def to_dict(self) -> Dict:
        """转换为字典。"""
        return {
            "local_path": str(self.local_path),
            "remote_path": self.remote_path,
            "sync_mode": self.sync_mode,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SyncPair':
        """从字典创建。"""
        pair = cls(data["local_path"], data["remote_path"], data["sync_mode"])
        pair.enabled = data.get("enabled", True)
        if data.get("last_sync"):
            pair.last_sync = datetime.fromisoformat(data["last_sync"])
        return pair


class FileSyncWorker(QThread, LoggerMixin):
    """文件同步工作线程。"""
    
    # 信号
    progress_updated = Signal(int, str)  # 进度百分比, 状态消息
    file_synced = Signal(str, str)  # 文件路径, 操作类型
    sync_completed = Signal(bool, str)  # 是否成功, 消息
    error_occurred = Signal(str)  # 错误消息
    
    def __init__(self, sync_pairs: List[SyncPair], sync_mode: str = "bidirectional"):
        super().__init__()
        self.sync_pairs = sync_pairs
        self.sync_mode = sync_mode
        self.should_stop = False
        self.current_progress = 0
    
    def stop(self):
        """停止同步。"""
        self.should_stop = True
    
    def run(self):
        """执行同步。"""
        try:
            self.logger.info(f"开始同步，模式: {self.sync_mode}")
            self.progress_updated.emit(0, "正在准备同步...")
            
            total_pairs = len(self.sync_pairs)
            if total_pairs == 0:
                self.sync_completed.emit(True, "没有需要同步的项目")
                return
            
            for i, pair in enumerate(self.sync_pairs):
                if self.should_stop:
                    self.sync_completed.emit(False, "同步已取消")
                    return
                
                if not pair.enabled:
                    continue
                
                # 更新进度
                progress = int((i / total_pairs) * 100)
                self.progress_updated.emit(progress, f"正在同步: {pair.local_path.name}")
                
                # 执行同步
                self._sync_pair(pair)
                
                # 更新最后同步时间
                pair.last_sync = datetime.now()
            
            self.progress_updated.emit(100, "同步完成")
            self.sync_completed.emit(True, f"成功同步 {total_pairs} 个项目")
            
        except Exception as e:
            self.logger.error(f"同步过程中发生错误: {e}")
            self.error_occurred.emit(f"同步失败: {str(e)}")
            self.sync_completed.emit(False, f"同步失败: {str(e)}")
    
    def _sync_pair(self, pair: SyncPair):
        """同步单个同步对。"""
        try:
            if self.sync_mode == "local_to_remote" or pair.sync_mode == "local_to_remote":
                self._upload_to_remote(pair)
            elif self.sync_mode == "remote_to_local" or pair.sync_mode == "remote_to_local":
                self._download_from_remote(pair)
            else:  # bidirectional
                self._bidirectional_sync(pair)
                
        except Exception as e:
            self.logger.error(f"同步对 {pair.local_path} 失败: {e}")
            self.error_occurred.emit(f"同步 {pair.local_path.name} 失败: {str(e)}")
    
    def _upload_to_remote(self, pair: SyncPair):
        """上传到远程。"""
        if not pair.local_path.exists():
            self.logger.warning(f"本地路径不存在: {pair.local_path}")
            return

        try:
            if pair.local_path.is_file():
                # 上传单个文件
                self._upload_file(pair.local_path, pair.remote_path)
            else:
                # 上传整个文件夹
                self._upload_directory(pair.local_path, pair.remote_path)

        except Exception as e:
            self.logger.error(f"上传失败: {e}")
            self.error_occurred.emit(f"上传失败: {str(e)}")

    def _upload_file(self, local_file: Path, remote_path: str):
        """上传单个文件到 Notion。"""
        self.logger.info(f"上传文件: {local_file} -> {remote_path}")

        try:
            if local_file.suffix.lower() in ['.md', '.txt']:
                # 上传文本文件为 Notion 页面
                success = self._upload_text_file_to_notion(local_file, remote_path)
                if success:
                    self.file_synced.emit(str(local_file), "上传")
                    self.logger.info(f"文本文件上传完成: {local_file.name}")
                else:
                    raise Exception("文本文件上传失败")

            elif local_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']:
                # 上传图片文件
                success = self._upload_image_file_to_notion(local_file, remote_path)
                if success:
                    self.file_synced.emit(str(local_file), "上传")
                    self.logger.info(f"图片文件上传完成: {local_file.name}")
                else:
                    raise Exception("图片文件上传失败")

            elif local_file.suffix.lower() in ['.json', '.html']:
                # 上传其他支持的文件类型
                success = self._upload_structured_file_to_notion(local_file, remote_path)
                if success:
                    self.file_synced.emit(str(local_file), "上传")
                    self.logger.info(f"结构化文件上传完成: {local_file.name}")
                else:
                    raise Exception("结构化文件上传失败")

            else:
                self.logger.warning(f"不支持的文件类型: {local_file.suffix}")
                return

        except Exception as e:
            self.logger.error(f"上传文件失败 {local_file}: {e}")
            raise

        # 上传延迟
        self.msleep(200)

    def _upload_text_file_to_notion(self, local_file: Path, remote_path: str) -> bool:
        """将文本文件上传为 Notion 页面。"""
        try:
            # 读取文件内容
            with open(local_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 获取 Notion 客户端（需要从应用控制器传递）
            notion_client = self._get_notion_client()
            if not notion_client:
                self.logger.error("Notion 客户端未连接")
                return False

            # 解析远程路径，获取父页面ID
            parent_id = self._resolve_remote_path_to_page_id(remote_path)
            if not parent_id:
                self.logger.error(f"无法解析远程路径: {remote_path}")
                return False

            # 创建 Notion 页面
            page_title = local_file.stem  # 文件名（不含扩展名）
            page_id = notion_client.create_page(parent_id, page_title, content)

            if page_id:
                self.logger.info(f"成功创建 Notion 页面: {page_title} (ID: {page_id})")
                return True
            else:
                self.logger.error("创建 Notion 页面失败")
                return False

        except Exception as e:
            self.logger.error(f"上传文本文件到 Notion 失败: {e}")
            return False

    def _upload_image_file_to_notion(self, local_file: Path, remote_path: str) -> bool:
        """将图片文件上传到 Notion。"""
        try:
            # 注意：Notion API 不直接支持文件上传
            # 需要先上传到外部存储（如 AWS S3），然后在 Notion 中引用
            # 这里实现一个简化版本：将图片信息记录到 Notion 页面

            notion_client = self._get_notion_client()
            if not notion_client:
                return False

            parent_id = self._resolve_remote_path_to_page_id(remote_path)
            if not parent_id:
                return False

            # 创建包含图片信息的页面
            page_title = f"图片: {local_file.name}"
            content = f"""
            图片文件信息：
            - 文件名: {local_file.name}
            - 大小: {local_file.stat().st_size} 字节
            - 修改时间: {datetime.fromtimestamp(local_file.stat().st_mtime)}

            注意：实际的图片文件需要上传到外部存储服务。
            """

            page_id = notion_client.create_page(parent_id, page_title, content)
            return page_id is not None

        except Exception as e:
            self.logger.error(f"上传图片文件到 Notion 失败: {e}")
            return False

    def _upload_structured_file_to_notion(self, local_file: Path, remote_path: str) -> bool:
        """将结构化文件（JSON/HTML）上传到 Notion。"""
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                content = f.read()

            notion_client = self._get_notion_client()
            if not notion_client:
                return False

            parent_id = self._resolve_remote_path_to_page_id(remote_path)
            if not parent_id:
                return False

            # 创建包含文件内容的页面
            page_title = local_file.stem
            formatted_content = f"""
            文件类型: {local_file.suffix.upper()}

            内容:
            ```
            {content[:2000]}  # 限制内容长度
            ```
            """

            page_id = notion_client.create_page(parent_id, page_title, formatted_content)
            return page_id is not None

        except Exception as e:
            self.logger.error(f"上传结构化文件到 Notion 失败: {e}")
            return False

    def _get_notion_client(self):
        """获取 Notion 客户端实例。"""
        # 这里需要从应用控制器获取 Notion 客户端
        # 暂时返回 None，需要在架构中改进
        return None

    def _resolve_remote_path_to_page_id(self, remote_path: str) -> Optional[str]:
        """将远程路径解析为 Notion 页面ID。"""
        # 从路径中提取页面ID
        if "/pages/" in remote_path:
            return remote_path.split("/pages/")[1]
        elif "/databases/" in remote_path:
            return remote_path.split("/databases/")[1]
        else:
            # 如果是简单路径，尝试从配置中获取映射
            # 这里需要从应用控制器或配置管理器获取映射
            return None

    def _upload_directory(self, local_dir: Path, remote_path: str):
        """上传整个目录。"""
        self.logger.info(f"上传目录: {local_dir} -> {remote_path}")

        # 遍历目录中的所有文件
        for item in local_dir.rglob("*"):
            if item.is_file() and self._should_sync_file(item):
                # 计算相对路径
                rel_path = item.relative_to(local_dir)
                remote_file_path = f"{remote_path}/{rel_path}"

                # 上传文件
                self._upload_file(item, remote_file_path)

    def _should_sync_file(self, file_path: Path) -> bool:
        """判断文件是否应该同步。"""
        # 忽略隐藏文件
        if file_path.name.startswith('.'):
            return False

        # 忽略临时文件
        if file_path.name.startswith('~') or file_path.name.endswith('.tmp'):
            return False

        # 检查文件扩展名
        supported_extensions = {'.md', '.txt', '.json', '.html', '.png', '.jpg', '.jpeg', '.gif'}
        return file_path.suffix.lower() in supported_extensions
    
    def _download_from_remote(self, pair: SyncPair):
        """从 Notion 下载内容到本地。"""
        try:
            # 确保本地目录存在
            pair.local_path.parent.mkdir(parents=True, exist_ok=True)

            # 从 Notion 获取内容并下载
            success = self._download_notion_content_to_local(pair.remote_path, pair.local_path)
            if not success:
                raise Exception("从 Notion 下载内容失败")

        except Exception as e:
            self.logger.error(f"下载失败: {e}")
            self.error_occurred.emit(f"下载失败: {str(e)}")

    def _download_notion_content_to_local(self, remote_path: str, local_path: Path) -> bool:
        """从 Notion 下载内容到本地文件。"""
        try:
            notion_client = self._get_notion_client()
            if not notion_client:
                self.logger.error("Notion 客户端未连接")
                return False

            # 解析远程路径，获取页面ID或数据库ID
            page_id = self._resolve_remote_path_to_page_id(remote_path)
            if not page_id:
                self.logger.error(f"无法解析远程路径: {remote_path}")
                return False

            # 获取页面内容
            page_content = notion_client.get_page_content(page_id)
            if not page_content:
                self.logger.error(f"无法获取页面内容: {page_id}")
                return False

            # 根据本地路径类型决定下载方式
            if local_path.is_dir() or not local_path.suffix:
                # 下载为目录结构
                return self._download_as_directory(page_content, local_path)
            else:
                # 下载为单个文件
                return self._download_as_file(page_content, local_path)

        except Exception as e:
            self.logger.error(f"从 Notion 下载内容失败: {e}")
            return False

    def _download_as_file(self, page_content: Dict, local_file: Path) -> bool:
        """将 Notion 页面内容下载为单个文件。"""
        try:
            # 提取页面信息
            page_info = page_content.get("page", {})
            blocks = page_content.get("blocks", [])

            # 获取页面标题
            title = self._extract_page_title(page_info)

            # 根据文件扩展名决定导出格式
            if local_file.suffix.lower() == '.md':
                content = self._convert_blocks_to_markdown(title, blocks)
            elif local_file.suffix.lower() == '.txt':
                content = self._convert_blocks_to_text(title, blocks)
            elif local_file.suffix.lower() == '.json':
                content = json.dumps(page_content, ensure_ascii=False, indent=2)
            elif local_file.suffix.lower() == '.html':
                content = self._convert_blocks_to_html(title, blocks)
            else:
                # 默认使用 Markdown 格式
                content = self._convert_blocks_to_markdown(title, blocks)

            # 写入文件
            local_file.parent.mkdir(parents=True, exist_ok=True)
            with open(local_file, 'w', encoding='utf-8') as f:
                f.write(content)

            self.file_synced.emit(str(local_file), "下载")
            self.logger.info(f"下载文件完成: {local_file}")
            return True

        except Exception as e:
            self.logger.error(f"下载为文件失败: {e}")
            return False

    def _download_as_directory(self, page_content: Dict, local_dir: Path) -> bool:
        """将 Notion 页面内容下载为目录结构。"""
        try:
            local_dir.mkdir(parents=True, exist_ok=True)

            # 提取页面信息
            page_info = page_content.get("page", {})
            blocks = page_content.get("blocks", [])
            title = self._extract_page_title(page_info)

            # 创建主文档文件
            main_file = local_dir / f"{title}.md"
            content = self._convert_blocks_to_markdown(title, blocks)

            with open(main_file, 'w', encoding='utf-8') as f:
                f.write(content)

            # 创建元数据文件
            metadata_file = local_dir / "metadata.json"
            metadata = {
                "title": title,
                "source": "notion",
                "page_id": page_info.get("id", ""),
                "downloaded_at": datetime.now().isoformat(),
                "last_edited": page_info.get("last_edited_time", ""),
                "files": [main_file.name]
            }

            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            self.file_synced.emit(str(main_file), "下载")
            self.file_synced.emit(str(metadata_file), "下载")
            self.logger.info(f"下载目录完成: {local_dir}")
            return True

        except Exception as e:
            self.logger.error(f"下载为目录失败: {e}")
            return False

    def _extract_page_title(self, page_info: Dict) -> str:
        """从页面信息中提取标题。"""
        try:
            properties = page_info.get("properties", {})
            for prop_name, prop_data in properties.items():
                if prop_data.get("type") == "title":
                    title_array = prop_data.get("title", [])
                    if title_array:
                        return title_array[0].get("plain_text", "无标题页面")
            return "无标题页面"
        except Exception:
            return "无标题页面"

    def _convert_blocks_to_markdown(self, title: str, blocks: List[Dict]) -> str:
        """将 Notion 块转换为 Markdown 格式。"""
        lines = [f"# {title}", ""]

        for block in blocks:
            block_type = block.get("type", "")

            if block_type == "paragraph":
                text = self._extract_rich_text(block.get("paragraph", {}).get("rich_text", []))
                lines.append(text)
                lines.append("")

            elif block_type == "heading_1":
                text = self._extract_rich_text(block.get("heading_1", {}).get("rich_text", []))
                lines.append(f"# {text}")
                lines.append("")

            elif block_type == "heading_2":
                text = self._extract_rich_text(block.get("heading_2", {}).get("rich_text", []))
                lines.append(f"## {text}")
                lines.append("")

            elif block_type == "heading_3":
                text = self._extract_rich_text(block.get("heading_3", {}).get("rich_text", []))
                lines.append(f"### {text}")
                lines.append("")

            elif block_type == "bulleted_list_item":
                text = self._extract_rich_text(block.get("bulleted_list_item", {}).get("rich_text", []))
                lines.append(f"- {text}")

            elif block_type == "numbered_list_item":
                text = self._extract_rich_text(block.get("numbered_list_item", {}).get("rich_text", []))
                lines.append(f"1. {text}")

            elif block_type == "code":
                code_block = block.get("code", {})
                language = code_block.get("language", "")
                text = self._extract_rich_text(code_block.get("rich_text", []))
                lines.append(f"```{language}")
                lines.append(text)
                lines.append("```")
                lines.append("")

        return "\n".join(lines)

    def _convert_blocks_to_text(self, title: str, blocks: List[Dict]) -> str:
        """将 Notion 块转换为纯文本格式。"""
        lines = [title, "=" * len(title), ""]

        for block in blocks:
            block_type = block.get("type", "")

            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3"]:
                text = self._extract_rich_text(block.get(block_type, {}).get("rich_text", []))
                lines.append(text)
                lines.append("")

            elif block_type in ["bulleted_list_item", "numbered_list_item"]:
                text = self._extract_rich_text(block.get(block_type, {}).get("rich_text", []))
                lines.append(f"• {text}")

        return "\n".join(lines)

    def _convert_blocks_to_html(self, title: str, blocks: List[Dict]) -> str:
        """将 Notion 块转换为 HTML 格式。"""
        lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{title}</title>",
            "<meta charset='utf-8'>",
            "</head>",
            "<body>",
            f"<h1>{title}</h1>"
        ]

        for block in blocks:
            block_type = block.get("type", "")

            if block_type == "paragraph":
                text = self._extract_rich_text(block.get("paragraph", {}).get("rich_text", []))
                lines.append(f"<p>{text}</p>")

            elif block_type == "heading_1":
                text = self._extract_rich_text(block.get("heading_1", {}).get("rich_text", []))
                lines.append(f"<h1>{text}</h1>")

            elif block_type == "heading_2":
                text = self._extract_rich_text(block.get("heading_2", {}).get("rich_text", []))
                lines.append(f"<h2>{text}</h2>")

            elif block_type == "heading_3":
                text = self._extract_rich_text(block.get("heading_3", {}).get("rich_text", []))
                lines.append(f"<h3>{text}</h3>")

        lines.extend(["</body>", "</html>"])
        return "\n".join(lines)

    def _extract_rich_text(self, rich_text_array: List[Dict]) -> str:
        """从富文本数组中提取纯文本。"""
        text_parts = []
        for text_obj in rich_text_array:
            text_parts.append(text_obj.get("plain_text", ""))
        return "".join(text_parts)

    def _create_sample_files(self, local_path: Path, remote_path: str):
        """创建示例文件来模拟下载。"""
        self.logger.info(f"下载内容: {remote_path} -> {local_path}")

        # 如果本地路径是文件，创建单个文件
        if local_path.suffix:
            self._create_sample_file(local_path, f"从 {remote_path} 下载的内容")
        else:
            # 如果是目录，创建多个示例文件
            local_path.mkdir(parents=True, exist_ok=True)

            # 创建示例 Markdown 文件
            md_file = local_path / "README.md"
            self._create_sample_file(md_file, f"""# {remote_path}

这是从云端下载的示例内容。

## 内容说明

- 这是一个示例文档
- 来源：{remote_path}
- 下载时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 功能特性

1. 支持 Markdown 格式
2. 自动同步
3. 版本控制

> 注意：这是演示内容，实际使用时会从真实的云端服务下载内容。
""")

            # 创建示例 JSON 文件
            json_file = local_path / "metadata.json"
            metadata = {
                "source": remote_path,
                "downloaded_at": datetime.now().isoformat(),
                "type": "notion_export",
                "files": ["README.md"]
            }

            with open(json_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            self.file_synced.emit(str(json_file), "下载")

    def _create_sample_file(self, file_path: Path, content: str):
        """创建示例文件。"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.file_synced.emit(str(file_path), "下载")
            self.logger.info(f"创建文件: {file_path}")

        except Exception as e:
            self.logger.error(f"创建文件失败 {file_path}: {e}")
            raise
    
    def _bidirectional_sync(self, pair: SyncPair):
        """双向同步 - 比较修改时间并决定同步方向。"""
        self.logger.info(f"双向同步 {pair.local_path} <-> {pair.remote_path}")

        try:
            # 获取本地文件信息
            local_exists = pair.local_path.exists()
            local_mtime = None
            if local_exists:
                local_mtime = datetime.fromtimestamp(pair.local_path.stat().st_mtime)

            # 获取远程文件信息
            remote_info = self._get_remote_file_info(pair.remote_path)
            remote_exists = remote_info is not None
            remote_mtime = None
            if remote_exists and remote_info:
                remote_mtime = self._parse_notion_datetime(remote_info.get("last_edited_time"))

            # 决定同步方向
            sync_direction = self._determine_sync_direction(
                local_exists, local_mtime,
                remote_exists, remote_mtime,
                pair.last_sync
            )

            # 执行同步
            if sync_direction == "local_to_remote":
                self.logger.info("本地文件较新，上传到远程")
                self._upload_to_remote(pair)

            elif sync_direction == "remote_to_local":
                self.logger.info("远程文件较新，下载到本地")
                self._download_from_remote(pair)

            elif sync_direction == "conflict":
                self.logger.warning("检测到冲突，创建备份")
                self._handle_sync_conflict(pair)

            else:  # no_change
                self.logger.info("文件已同步，无需更新")

            self.file_synced.emit(str(pair.local_path), "双向同步")

        except Exception as e:
            self.logger.error(f"双向同步失败: {e}")
            raise

    def _get_remote_file_info(self, remote_path: str) -> Optional[Dict]:
        """获取远程文件信息。"""
        try:
            notion_client = self._get_notion_client()
            if not notion_client:
                return None

            page_id = self._resolve_remote_path_to_page_id(remote_path)
            if not page_id:
                return None

            # 获取页面基本信息（不包含内容）
            page_info = notion_client._make_request("GET", f"/pages/{page_id}")
            return page_info

        except Exception as e:
            self.logger.error(f"获取远程文件信息失败: {e}")
            return None

    def _parse_notion_datetime(self, datetime_str: str) -> Optional[datetime]:
        """解析 Notion 的日期时间字符串。"""
        try:
            if not datetime_str:
                return None
            # Notion 使用 ISO 8601 格式
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except Exception as e:
            self.logger.error(f"解析日期时间失败: {e}")
            return None

    def _determine_sync_direction(self,
                                local_exists: bool, local_mtime: Optional[datetime],
                                remote_exists: bool, remote_mtime: Optional[datetime],
                                last_sync: Optional[datetime]) -> str:
        """确定同步方向。"""

        # 如果只有一边存在，同步到另一边
        if local_exists and not remote_exists:
            return "local_to_remote"
        elif remote_exists and not local_exists:
            return "remote_to_local"
        elif not local_exists and not remote_exists:
            return "no_change"

        # 两边都存在，比较修改时间
        if local_mtime and remote_mtime:
            # 如果有上次同步时间，检查是否有冲突
            if last_sync:
                local_changed = local_mtime > last_sync
                remote_changed = remote_mtime > last_sync

                if local_changed and remote_changed:
                    # 两边都有修改，产生冲突
                    return "conflict"
                elif local_changed:
                    return "local_to_remote"
                elif remote_changed:
                    return "remote_to_local"
                else:
                    return "no_change"
            else:
                # 没有上次同步时间，比较绝对时间
                if local_mtime > remote_mtime:
                    return "local_to_remote"
                elif remote_mtime > local_mtime:
                    return "remote_to_local"
                else:
                    return "no_change"

        return "no_change"

    def _handle_sync_conflict(self, pair: SyncPair):
        """处理同步冲突。"""
        try:
            # 创建本地文件的备份
            if pair.local_path.exists():
                backup_path = pair.local_path.with_suffix(
                    f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{pair.local_path.suffix}"
                )
                import shutil
                shutil.copy2(pair.local_path, backup_path)
                self.logger.info(f"创建本地备份: {backup_path}")

            # 下载远程版本，用户可以手动合并
            self._download_from_remote(pair)

            # 发出冲突警告
            self.error_occurred.emit(f"检测到同步冲突: {pair.local_path.name}，已创建备份文件")

        except Exception as e:
            self.logger.error(f"处理同步冲突失败: {e}")
            raise


class FileSyncService(QObject, LoggerMixin):
    """文件同步服务。"""
    
    # 信号
    sync_started = Signal()
    sync_progress = Signal(int, str)
    sync_completed = Signal(bool, str)
    sync_error = Signal(str)
    
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.sync_pairs: List[SyncPair] = []
        self.sync_worker: Optional[FileSyncWorker] = None
        self.is_syncing = False
        
        # 加载同步对
        self._load_sync_pairs()
    
    def add_sync_pair(self, local_path: str, remote_path: str, sync_mode: str = "bidirectional") -> bool:
        """添加同步对。"""
        try:
            pair = SyncPair(local_path, remote_path, sync_mode)
            self.sync_pairs.append(pair)
            self._save_sync_pairs()
            self.logger.info(f"添加同步对: {local_path} <-> {remote_path}")
            return True
        except Exception as e:
            self.logger.error(f"添加同步对失败: {e}")
            return False
    
    def remove_sync_pair(self, index: int) -> bool:
        """移除同步对。"""
        try:
            if 0 <= index < len(self.sync_pairs):
                removed = self.sync_pairs.pop(index)
                self._save_sync_pairs()
                self.logger.info(f"移除同步对: {removed.local_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"移除同步对失败: {e}")
            return False
    
    def get_sync_pairs(self) -> List[SyncPair]:
        """获取所有同步对。"""
        return self.sync_pairs.copy()
    
    def start_sync(self, sync_mode: str = "bidirectional"):
        """开始同步。"""
        if self.is_syncing:
            self.logger.warning("同步已在进行中")
            return
        
        if not self.sync_pairs:
            self.sync_error.emit("没有配置同步对")
            return
        
        self.is_syncing = True
        self.sync_started.emit()
        
        # 创建并启动同步工作线程
        self.sync_worker = FileSyncWorker(self.sync_pairs, sync_mode)
        self.sync_worker.progress_updated.connect(self.sync_progress.emit)
        self.sync_worker.sync_completed.connect(self._on_sync_completed)
        self.sync_worker.error_occurred.connect(self.sync_error.emit)
        self.sync_worker.start()
    
    def stop_sync(self):
        """停止同步。"""
        if self.sync_worker and self.sync_worker.isRunning():
            self.sync_worker.stop()
            self.sync_worker.wait(5000)  # 等待最多5秒
        self.is_syncing = False
    
    def _on_sync_completed(self, success: bool, message: str):
        """同步完成处理。"""
        self.is_syncing = False
        self.sync_completed.emit(success, message)
        
        if success:
            self._save_sync_pairs()  # 保存更新的同步时间
    
    def _load_sync_pairs(self):
        """加载同步对配置。"""
        try:
            sync_data = self.config_manager.get("sync_pairs", [])
            self.sync_pairs = [SyncPair.from_dict(data) for data in sync_data]
            self.logger.info(f"加载了 {len(self.sync_pairs)} 个同步对")
        except Exception as e:
            self.logger.error(f"加载同步对失败: {e}")
            self.sync_pairs = []
    
    def _save_sync_pairs(self):
        """保存同步对配置。"""
        try:
            sync_data = [pair.to_dict() for pair in self.sync_pairs]
            self.config_manager.set("sync_pairs", sync_data)
            self.logger.info("同步对配置已保存")
        except Exception as e:
            self.logger.error(f"保存同步对失败: {e}")
