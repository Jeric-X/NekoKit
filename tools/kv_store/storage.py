import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from astrbot.api import logger
from ...core import HUMAN_AI_ID, RecordScope, StorageBackend


def _safe_store_name(store_name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in store_name)
    return safe or "kvstore"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _visible_records(records: List[Dict[str, Any]], key: str, scope: RecordScope):
    return [r for r in records if r.get("key") == key and scope.matches(r)]


def _pick_record(
    records: List[Dict[str, Any]],
    scope: RecordScope,
    prefer_user: bool = False,
) -> Optional[Dict[str, Any]]:
    """记录选择优先级。

    读取（get）：优先当前 AI 在当前会话的私有记录，其次当前 AI 的记录，
    最后第一条（存储顺序）。
    写入（set，prefer_user=True）：优先 user 共享记录（避免合并时
    吞掉共享层导致其他 AI 失去可见数据），其次当前 AI 的记录，否则第一条。
    """
    if not records:
        return None
    own_private = [
        r
        for r in records
        if r.get("private")
        and r.get("ai_id") == scope.ai_id
        and r.get("session_id") == scope.session_id
    ]
    if own_private:
        return own_private[0]
    if prefer_user:
        shared = [r for r in records if r.get("ai_id") == HUMAN_AI_ID]
        if shared:
            return shared[0]
    own = [r for r in records if r.get("ai_id") == scope.ai_id]
    pool = own or records
    return pool[0]


class JSONStorageBackend(StorageBackend):
    """JSON 文件存储后端：单一文件，记录来源由 ai_id/session_id 字段控制"""

    def __init__(self, data_dir: str, store_name: str = "kvstore"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.store_name = _safe_store_name(store_name)
        self.data_file = self.data_dir / f"{self.store_name}.json"
        self._records: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if not self.data_file.exists():
            return
        try:
            with open(self.data_file, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("records"), list):
                self._records = [
                    r for r in data["records"] if isinstance(r, dict) and r.get("key")
                ]
        except Exception as e:
            logger.error(f"[JSONStorage] 加载数据失败: {e}")
            self._records = []

    def _save(self) -> None:
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"records": self._records}, f, ensure_ascii=False, indent=2
                )
        except Exception as e:
            logger.error(f"[JSONStorage] 保存数据失败: {e}")

    def get(self, key: str, scope: RecordScope) -> Optional[Any]:
        with self._lock:
            record = _pick_record(_visible_records(self._records, key, scope), scope)
            return record.get("value") if record else None

    def set(self, key: str, value: Any, scope: RecordScope, private: bool = False) -> None:
        with self._lock:
            now = _utc_now()
            visible = _visible_records(self._records, key, scope)
            if private:
                # 私有写入：仅命中自己的私有记录（可见的私有记录即精确匹配
                # 来源的记录），不触碰其他可见记录
                target = next((r for r in visible if r.get("private")), None)
                if target:
                    target["value"] = value
                    target["updated_at"] = now
                else:
                    self._records.append(
                        {
                            "key": key,
                            "value": value,
                            "ai_id": scope.ai_id,
                            "session_id": scope.session_id,
                            "private": True,
                            "created_at": now,
                            "updated_at": now,
                        }
                    )
            else:
                # 公共写入：私有记录不参与更新与合并
                candidates = [r for r in visible if not r.get("private")]
                if candidates:
                    # 更新选中的记录，并合并（删除）其余可见的同 key 重复记录
                    target = _pick_record(candidates, scope, prefer_user=True)
                    target["value"] = value
                    target["updated_at"] = now
                    remove = {id(r) for r in candidates} - {id(target)}
                    if remove:
                        self._records = [
                            r for r in self._records if id(r) not in remove
                        ]
                else:
                    self._records.append(
                        {
                            "key": key,
                            "value": value,
                            "ai_id": scope.ai_id,
                            "session_id": scope.session_id,
                            "created_at": now,
                            "updated_at": now,
                        }
                    )
            self._save()

    def delete(self, key: str, scope: RecordScope) -> bool:
        with self._lock:
            visible = _visible_records(self._records, key, scope)
            if not visible:
                return False
            self._records = [
                r for r in self._records if r not in visible
            ]
            self._save()
            return True

    def list_keys(self, scope: RecordScope) -> List[str]:
        with self._lock:
            keys = {
                r.get("key")
                for r in self._records
                if r.get("key") and scope.matches(r)
            }
            return sorted(keys)

    def list_records(self, scope: RecordScope) -> List[Dict[str, Any]]:
        with self._lock:
            records = [
                {
                    "key": r.get("key"),
                    "ai_id": r.get("ai_id"),
                    "session_id": r.get("session_id"),
                    "private": bool(r.get("private")),
                    "updated_at": r.get("updated_at"),
                }
                for r in self._records
                if r.get("key") and scope.matches(r)
            ]
            records.sort(key=lambda r: (str(r["key"]), str(r.get("updated_at") or "")))
            return records

    def search(self, keyword: str, scope: RecordScope) -> List[Dict[str, Any]]:
        with self._lock:
            matched: Dict[str, Dict[str, Any]] = {}
            keyword_lower = keyword.lower()
            for record in self._records:
                key = record.get("key")
                if not key or not scope.matches(record):
                    continue
                if keyword_lower not in str(key).lower():
                    continue
                current = matched.get(key)
                if current is None or str(record.get("updated_at") or "") > str(
                    current.get("updated_at") or ""
                ):
                    matched[key] = record
            return [
                {"key": key, "value": record.get("value")}
                for key, record in matched.items()
            ]


class SQLiteStorageBackend(StorageBackend):
    """SQLite 数据库存储后端：记录来源由 ai_id/session_id 字段控制"""

    def __init__(self, data_dir: str, store_name: str = "kvstore"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.store_name = _safe_store_name(store_name)
        self.db_file = self.data_dir / f"{self.store_name}.db"
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(str(self.db_file), check_same_thread=False)

    def _init_db(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kvstore (
                key TEXT NOT NULL,
                ai_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                value TEXT NOT NULL,
                is_private INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (key, ai_id, session_id, is_private)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_key ON kvstore(key)")
        conn.commit()
        conn.close()

    @staticmethod
    def _scope_clause(scope: RecordScope) -> tuple:
        """根据开关生成可见性过滤条件。

        私有记录无视共享开关，仅精确匹配来源 (ai_id, session_id) 时可见；
        管理员（is_admin）不受私有限制。
        """
        clauses, params = [], []
        if scope.ai_isolation:
            clauses.append(
                "((is_private = 0 AND (ai_id = ? OR ai_id = ?))"
                " OR (is_private = 1 AND ai_id = ? AND session_id = ?))"
            )
            params.extend([scope.ai_id, HUMAN_AI_ID, scope.ai_id, scope.session_id])
        elif not scope.is_admin:
            clauses.append("(is_private = 0 OR (ai_id = ? AND session_id = ?))")
            params.extend([scope.ai_id, scope.session_id])
        if scope.session_scope:
            if scope.is_admin:
                # 管理员可见私有记录，其余按会话过滤
                clauses.append("(is_private = 1 OR session_id = ?)")
            else:
                clauses.append("session_id = ?")
            params.append(scope.session_id)
        where = (" AND " + " AND ".join(clauses)) if clauses else ""
        return where, params

    def get(self, key: str, scope: RecordScope) -> Optional[Any]:
        with self._lock:
            where, params = self._scope_clause(scope)
            conn = self._get_connection()
            cursor = conn.cursor()
            # 优先当前 AI 在当前会话的私有记录，其次当前 AI 的记录，最后第一条
            cursor.execute(
                "SELECT value FROM kvstore WHERE key = ?"
                f"{where} ORDER BY (is_private = 1 AND ai_id = ? AND session_id = ?)"
                " DESC, (ai_id = ?) DESC, rowid ASC LIMIT 1",
                (key, *params, scope.ai_id, scope.session_id, scope.ai_id),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                try:
                    return json.loads(row[0])
                except Exception:
                    return row[0]
            return None

    def set(self, key: str, value: Any, scope: RecordScope, private: bool = False) -> None:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            value_str = json.dumps(value, ensure_ascii=False)
            if private:
                # 私有写入：仅命中自己的私有记录，不触碰其他可见记录
                cursor.execute(
                    "SELECT rowid FROM kvstore WHERE key = ? AND ai_id = ? "
                    "AND session_id = ? AND is_private = 1",
                    (key, scope.ai_id, scope.session_id),
                )
                row = cursor.fetchone()
                if row:
                    cursor.execute(
                        "UPDATE kvstore SET value = ?, "
                        "updated_at = CURRENT_TIMESTAMP WHERE rowid = ?",
                        (value_str, row[0]),
                    )
                else:
                    cursor.execute(
                        "INSERT INTO kvstore (key, ai_id, session_id, value, "
                        "is_private) VALUES (?, ?, ?, ?, 1)",
                        (key, scope.ai_id, scope.session_id, value_str),
                    )
            else:
                where, params = self._scope_clause(scope)
                # 公共写入：私有记录不参与更新与合并；
                # 目标优先级 user 共享记录 > 当前 AI 记录 > 第一条（写入顺序）
                cursor.execute(
                    "SELECT rowid FROM kvstore WHERE key = ? AND is_private = 0"
                    f"{where} ORDER BY (ai_id = ?) DESC, (ai_id = ?) DESC, rowid ASC",
                    (key, *params, HUMAN_AI_ID, scope.ai_id),
                )
                rowids = [row[0] for row in cursor.fetchall()]
                if rowids:
                    # 更新选中的记录，并合并（删除）其余可见的同 key 重复记录
                    cursor.execute(
                        "UPDATE kvstore SET value = ?, updated_at = CURRENT_TIMESTAMP "
                        "WHERE rowid = ?",
                        (value_str, rowids[0]),
                    )
                    for rowid in rowids[1:]:
                        cursor.execute("DELETE FROM kvstore WHERE rowid = ?", (rowid,))
                else:
                    cursor.execute(
                        "INSERT INTO kvstore (key, ai_id, session_id, value) "
                        "VALUES (?, ?, ?, ?)",
                        (key, scope.ai_id, scope.session_id, value_str),
                    )
            conn.commit()
            conn.close()

    def delete(self, key: str, scope: RecordScope) -> bool:
        with self._lock:
            where, params = self._scope_clause(scope)
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                f"DELETE FROM kvstore WHERE key = ?{where}", (key, *params)
            )
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            return affected > 0

    def list_keys(self, scope: RecordScope) -> List[str]:
        with self._lock:
            where, params = self._scope_clause(scope)
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT DISTINCT key FROM kvstore WHERE 1=1{where}", params
            )
            rows = cursor.fetchall()
            conn.close()
            return sorted(row[0] for row in rows)

    def list_records(self, scope: RecordScope) -> List[Dict[str, Any]]:
        with self._lock:
            where, params = self._scope_clause(scope)
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT key, ai_id, session_id, is_private, updated_at FROM kvstore "
                f"WHERE 1=1{where} ORDER BY key, updated_at",
                params,
            )
            rows = cursor.fetchall()
            conn.close()
            return [
                {
                    "key": row[0],
                    "ai_id": row[1],
                    "session_id": row[2],
                    "private": bool(row[3]),
                    "updated_at": row[4],
                }
                for row in rows
            ]

    def search(self, keyword: str, scope: RecordScope) -> List[Dict[str, Any]]:
        with self._lock:
            where, params = self._scope_clause(scope)
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT key, value FROM kvstore WHERE key LIKE ?"
                f"{where} ORDER BY updated_at DESC, rowid DESC",
                (f"%{keyword}%", *params),
            )
            rows = cursor.fetchall()
            conn.close()
            results = []
            seen = set()
            for key, value in rows:
                if key in seen:
                    continue
                seen.add(key)
                try:
                    parsed = json.loads(value)
                except Exception:
                    parsed = value
                results.append({"key": key, "value": parsed})
            return results


def create_storage_backend(
    data_dir: str, use_sqlite: bool = False, store_name: str = "kvstore"
) -> StorageBackend:
    """工厂函数：创建存储后端"""
    if use_sqlite:
        return SQLiteStorageBackend(data_dir, store_name=store_name)
    return JSONStorageBackend(data_dir, store_name=store_name)
