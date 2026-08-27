import json
import shutil
import threading
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

from astrbot.api import logger

from ...core import HUMAN_AI_ID, RecordScope


def _filename_from_key(key: str) -> str:
    normalized = str(key).replace("\\", "/")
    basename = PurePosixPath(normalized).name.replace("\x00", "").strip()
    return _safe_filename(basename, "file")


def _safe_filename(value: str, fallback: str) -> str:
    basename = str(value or "").replace("\x00", "").strip()
    for char in '/\\:*?"<>|':
        basename = basename.replace(char, "_")
    if basename in {"", ".", ".."}:
        basename = fallback
    return basename


def _record_id(ai_id: str, session_id: str, key: str, private: bool = False) -> str:
    """记录唯一标识：由来源 (ai_id, session_id)、key 和私有标记派生"""
    marker = "\0private" if private else ""
    return sha256(f"{ai_id}\0{session_id}\0{key}{marker}".encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _parse_utc(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


class FileStorageBackend:
    """File storage backend: single index + blob dir, source controlled by record fields."""

    def __init__(self, data_dir: str, store_name: str = "file_store"):
        self.root = Path(data_dir) / store_name
        self.index_file = self.root / "index.json"
        self.blob_dir = self.root / "blobs"
        self.cleanup_state_file = self.root / "cleanup_state.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.blob_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def put_file(
        self,
        key: str,
        source_path: str,
        scope: RecordScope,
        retention_days: int = 7,
        source_filename: Optional[str] = None,
        private: bool = False,
    ) -> Dict[str, Any]:
        source = Path(source_path).expanduser().resolve(strict=True)
        if not source.is_file():
            raise ValueError(f"源路径不是文件: {source_path}")

        with self._lock:
            metadata, target = self._prepare_write(
                key,
                scope,
                retention_days,
                desired_filename=source_filename or source.name,
                preserve_filename=True,
                private=private,
            )
            shutil.copyfile(source, target)
            return self._finish_write(metadata, target)

    def put_bytes(
        self,
        key: str,
        content: bytes,
        scope: RecordScope,
        retention_days: int = 7,
        default_suffix: str = "",
        private: bool = False,
    ) -> Dict[str, Any]:
        with self._lock:
            metadata, target = self._prepare_write(
                key,
                scope,
                retention_days,
                preserve_filename=False,
                default_suffix=default_suffix,
                private=private,
            )
            target.write_bytes(content)
            return self._finish_write(metadata, target)

    def get_path(self, key: str, scope: RecordScope) -> Optional[str]:
        with self._lock:
            item = self._find_target(key, scope)
            if not item:
                return None
            if self._is_expired(item):
                return None
            path = self._path_from_metadata(item)
            if not path.is_file():
                return None
            return str(path)

    def get_metadata(self, key: str, scope: RecordScope) -> Optional[Dict[str, Any]]:
        with self._lock:
            item = self._find_target(key, scope)
            if not item:
                return None
            if self._is_expired(item):
                return None
            return dict(item)

    def list_files(self, scope: RecordScope, prefix: str = "") -> List[Dict[str, Any]]:
        with self._lock:
            index = self._load_index()
            items = []
            for item in index.values():
                if prefix and not item.get("key", "").startswith(prefix):
                    continue
                if not scope.matches(item):
                    continue
                if self._is_expired(item):
                    continue
                data = dict(item)
                data["exists"] = self._path_from_metadata(item).is_file()
                items.append(data)
            return sorted(items, key=lambda item: item.get("key", ""))

    def delete(self, key: str, scope: RecordScope) -> bool:
        with self._lock:
            index = self._load_index()
            victims = [
                record_id
                for record_id, item in index.items()
                if item.get("key") == key and scope.matches(item)
            ]
            if not victims:
                return False
            for record_id in victims:
                item = index.pop(record_id)
                path = self._path_from_metadata(item)
                if path.exists():
                    path.unlink()
            self._save_index(index)
            return True

    def cleanup_expired_once_per_day(self) -> int:
        today = datetime.now(timezone.utc).date().isoformat()
        with self._lock:
            state = self._load_cleanup_state()
            if state.get("last_cleanup_date") == today:
                return 0

            removed = 0
            index = self._load_index()
            changed = False
            for record_id, item in list(index.items()):
                if not self._is_expired(item):
                    continue
                path = self._path_from_metadata(item)
                if path.exists():
                    try:
                        path.unlink()
                    except Exception as e:
                        logger.warning(f"[FileStorage] 删除过期文件失败: {e}")
                        continue
                del index[record_id]
                removed += 1
                changed = True
            if changed:
                self._save_index(index)

            self._save_cleanup_state(
                {"last_cleanup_date": today, "last_removed_count": removed}
            )
            return removed

    def _find_target(self, key: str, scope: RecordScope) -> Optional[Dict[str, Any]]:
        """查找 key 对应的目标可见记录。

        优先当前 AI 在当前会话的私有记录，其次当前 AI 的记录，最后第一条（写入顺序）。
        """
        candidates = [
            item
            for item in self._load_index().values()
            if item.get("key") == key and scope.matches(item)
        ]
        if not candidates:
            return None
        own_private = [
            item
            for item in candidates
            if item.get("private")
            and item.get("ai_id") == scope.ai_id
            and item.get("session_id") == scope.session_id
        ]
        if own_private:
            return own_private[0]
        own = [item for item in candidates if item.get("ai_id") == scope.ai_id]
        return (own or candidates)[0]

    def _prepare_write(
        self,
        key: str,
        scope: RecordScope,
        retention_days: int,
        desired_filename: Optional[str] = None,
        preserve_filename: bool = False,
        default_suffix: str = "",
        private: bool = False,
    ) -> tuple[Dict[str, Any], Path]:
        if not key or not str(key).strip():
            raise ValueError("key 不能为空")

        index = self._load_index()
        candidates = [
            item
            for item in index.values()
            if item.get("key") == key and scope.matches(item)
        ]
        existing = None
        others: List[Dict[str, Any]] = []
        if private:
            # 私有写入：仅命中自己的私有记录（可见的私有记录即精确匹配
            # 来源的记录），不触碰其他可见记录
            privates = [item for item in candidates if item.get("private")]
            existing = privates[0] if privates else None
        else:
            # 公共写入：私有记录不参与更新与合并；
            # 目标优先级 user 共享记录 > 当前 AI 记录 > 第一条（写入顺序），
            # 避免合并时吞掉共享层导致其他 AI 失去可见数据
            candidates = [item for item in candidates if not item.get("private")]
            if candidates:
                shared = [
                    item for item in candidates if item.get("ai_id") == HUMAN_AI_ID
                ]
                if shared:
                    existing = shared[0]
                else:
                    own = [
                        item
                        for item in candidates
                        if item.get("ai_id") == scope.ai_id
                    ]
                    existing = (own or candidates)[0]
                others = [item for item in candidates if item is not existing]
        now = _utc_now()

        if existing:
            # 覆盖可见记录：保留原记录的来源字段、私有标记与创建时间
            ai_id = existing["ai_id"]
            session_id = existing["session_id"]
            file_id = existing["file_id"]
            created_at = existing.get("created_at", now)
            is_private = bool(existing.get("private"))
        else:
            ai_id = scope.ai_id
            session_id = scope.session_id
            file_id = _record_id(ai_id, session_id, key, private=private)
            created_at = now
            is_private = private

        filename = _filename_from_key(key)
        suffix = Path(filename).suffix or default_suffix

        if preserve_filename:
            filename = _safe_filename(desired_filename or filename, filename)
            blob_name = self._unique_blob_name(
                filename, existing.get("blob_name") if existing else None
            )
        else:
            blob_name = f"{file_id}{suffix}"
        target = (self.blob_dir / blob_name).resolve(strict=False)
        self._ensure_inside(target, self.blob_dir)

        expires_at = None
        if retention_days != -1:
            expires_at = (
                datetime.now(timezone.utc) + timedelta(days=retention_days)
            ).isoformat(timespec="seconds")
        metadata = {
            "key": key,
            "file_id": file_id,
            "filename": filename,
            "blob_name": blob_name,
            "ai_id": ai_id,
            "session_id": session_id,
            "created_at": created_at,
            "updated_at": now,
            "retention_days": retention_days,
            "expires_at": expires_at,
        }
        if is_private:
            metadata["private"] = True
        old_blob_name = existing.get("blob_name") if existing else None
        if old_blob_name and old_blob_name != blob_name:
            metadata["_old_blob_name"] = old_blob_name
        # 可见范围内的同 key 重复记录，写入完成后合并（删除）
        if others:
            metadata["_merged_records"] = [
                (item.get("file_id"), item.get("blob_name")) for item in others
            ]
        return metadata, target

    def _finish_write(
        self,
        metadata: Dict[str, Any],
        target: Path,
    ) -> Dict[str, Any]:
        old_blob_name = metadata.pop("_old_blob_name", None)
        merged_records = metadata.pop("_merged_records", None) or []
        metadata["size"] = target.stat().st_size
        index = self._load_index()
        index[metadata["file_id"]] = metadata
        for file_id, _blob_name in merged_records:
            if file_id and file_id != metadata["file_id"]:
                index.pop(file_id, None)
        self._save_index(index)
        blobs_to_remove = []
        if old_blob_name:
            blobs_to_remove.append(old_blob_name)
        blobs_to_remove.extend(
            blob_name for _file_id, blob_name in merged_records if blob_name
        )
        for blob_name in blobs_to_remove:
            old_path = (self.blob_dir / blob_name).resolve(strict=False)
            self._ensure_inside(old_path, self.blob_dir)
            if old_path.exists() and old_path != target:
                try:
                    old_path.unlink()
                except Exception as e:
                    logger.warning(f"[FileStorage] 删除旧文件失败: {e}")
        return dict(metadata)

    def _unique_blob_name(
        self, filename: str, existing_blob_name: Optional[str] = None
    ) -> str:
        safe_name = _safe_filename(filename, "file")
        if existing_blob_name == safe_name or not (
            self.blob_dir / safe_name
        ).exists():
            return safe_name

        path = Path(safe_name)
        stem = path.stem or "file"
        suffix = path.suffix
        for index in range(1, 10000):
            candidate = f"{stem}_{index}{suffix}"
            if existing_blob_name == candidate or not (
                self.blob_dir / candidate
            ).exists():
                return candidate
        digest = sha256(safe_name.encode("utf-8")).hexdigest()[:12]
        return f"{stem}_{digest}{suffix}"

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        if not self.index_file.exists():
            return {}
        try:
            data = self._load_json_file(self.index_file)
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.error(f"[FileStorage] 加载索引失败: {e}")
        return {}

    def _save_index(self, data: Dict[str, Dict[str, Any]]) -> None:
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _path_from_metadata(self, item: Dict[str, Any]) -> Path:
        blob_name = item.get("blob_name") or item.get("file_id") or ""
        path = (self.blob_dir / blob_name).resolve(strict=False)
        self._ensure_inside(path, self.blob_dir)
        return path

    def _load_cleanup_state(self) -> Dict[str, Any]:
        data = self._load_json_file(self.cleanup_state_file)
        if isinstance(data, dict):
            return data
        return {}

    def _save_cleanup_state(self, data: Dict[str, Any]) -> None:
        with open(self.cleanup_state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _load_json_file(path: Path) -> Any:
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _is_expired(item: Dict[str, Any]) -> bool:
        expires_at = _parse_utc(str(item.get("expires_at") or ""))
        if expires_at is None:
            return False
        return expires_at <= datetime.now(timezone.utc)

    @staticmethod
    def _ensure_inside(path: Path, root: Path) -> None:
        resolved_root = root.resolve(strict=False)
        try:
            path.relative_to(resolved_root)
        except ValueError:
            raise ValueError("文件路径越界")
