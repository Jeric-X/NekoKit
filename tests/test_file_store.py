"""文件存储行为测试：隔离、user 共享层、get 优先级、合并、私有文件。"""

from pathlib import Path

from conftest import CAT, CAT_G2, HUMAN, MAID, FakeContext


def _use(fs, who):
    fs.set_context(FakeContext(*who))


async def _read(fs, who, key, admin=False):
    _use(fs, who)
    execute = fs.execute_admin if admin else fs.execute
    result = await execute(action="get_path", key=key)
    assert result.success, result.message
    with open(result.data["path"]) as f:
        return f.read()


class TestFileStore:
    async def test_basic_isolation(self, file_tool):
        fs = file_tool
        _use(fs, CAT)
        await fs.execute(action="save", key="doc", content="猫娘的文档")
        _use(fs, MAID)
        assert not (await fs.execute(action="get_path", key="doc")).success

    async def test_same_ai_across_sessions(self, file_tool):
        fs = file_tool
        _use(fs, CAT)
        await fs.execute(action="save", key="doc", content="会话1写的")
        assert await _read(fs, CAT_G2, "doc") == "会话1写的"

    async def test_user_shared_layer(self, file_tool, tmp_path):
        fs = file_tool
        _use(fs, HUMAN)
        await fs.execute_admin(action="save", key="doc", content="共享文档")
        for who in (CAT, MAID):
            assert await _read(fs, who, "doc") == "共享文档"
        files = (await fs.execute_admin(action="list")).data["files"]
        assert files[0]["ai_id"] == "user"

    async def test_ai_save_updates_user_file_in_place(self, file_tool):
        fs = file_tool
        _use(fs, HUMAN)
        await fs.execute_admin(action="save", key="doc", content="v1")
        _use(fs, CAT)
        await fs.execute(action="save", key="doc", content="AI 改过")
        files = (await fs.execute_admin(action="list")).data["files"]
        assert len(files) == 1 and files[0]["ai_id"] == "user"
        assert await _read(fs, MAID, "doc") == "AI 改过"

    async def test_get_priority_and_merge(self, file_tool):
        fs = file_tool
        fs.set_config({"ai_isolation": True, "session_scope": True})
        _use(fs, CAT)
        await fs.execute(action="save", key="f", content="cat-g1")
        _use(fs, CAT_G2)
        await fs.execute(action="save", key="f", content="cat-g2")
        fs.set_config({"ai_isolation": True, "session_scope": False})

        assert await _read(fs, CAT, "f") == "cat-g1"
        fs.set_config({"ai_isolation": False, "session_scope": False})
        assert await _read(fs, MAID, "f") == "cat-g1"
        fs.set_config({"ai_isolation": True, "session_scope": False})

        files = (await fs.execute_admin(action="list")).data["files"]
        assert len(files) == 2

        _use(fs, CAT)
        await fs.execute(action="save", key="f", content="merged")
        files = (await fs.execute_admin(action="list")).data["files"]
        assert len(files) == 1
        assert files[0]["session_id"] == "group1"

    async def test_merge_cleans_up_blobs(self, file_tool, tmp_path):
        fs = file_tool
        fs.set_config({"ai_isolation": True, "session_scope": True})
        _use(fs, CAT)
        await fs.execute(action="save", key="f", content="cat-g1")
        _use(fs, CAT_G2)
        await fs.execute(action="save", key="f", content="cat-g2")
        fs.set_config({"ai_isolation": True, "session_scope": False})

        blob_dir = Path(str(fs._storage.blob_dir))
        assert len(list(blob_dir.iterdir())) == 2

        _use(fs, CAT)
        await fs.execute(action="save", key="f", content="merged")
        assert len(list(blob_dir.iterdir())) == 1

    async def test_private_file_invisible_even_when_sharing_all(self, file_tool):
        fs = file_tool
        fs.set_config({"ai_isolation": False, "session_scope": False})
        _use(fs, CAT)
        await fs.execute(action="save", key="secret.txt", content="秘密文件", private=True)

        assert await _read(fs, CAT, "secret.txt") == "秘密文件"
        _use(fs, CAT_G2)
        assert not (await fs.execute(action="get_path", key="secret.txt")).success
        _use(fs, MAID)
        assert not (await fs.execute(action="get_path", key="secret.txt")).success
        files = (await fs.execute(action="list")).data["files"]
        assert all(f["key"] != "secret.txt" for f in files)

    async def test_admin_sees_private_file(self, file_tool):
        fs = file_tool
        fs.set_config({"ai_isolation": False, "session_scope": False})
        _use(fs, CAT)
        await fs.execute(action="save", key="secret.txt", content="s", private=True)
        _use(fs, HUMAN)
        files = (await fs.execute_admin(action="list")).data["files"]
        secret = [f for f in files if f["key"] == "secret.txt"]
        assert len(secret) == 1 and secret[0].get("private") is True

    async def test_private_and_public_coexist(self, file_tool, tmp_path):
        fs = file_tool
        _use(fs, CAT)
        await fs.execute(action="save", key="doc", content="公共文档")
        await fs.execute(action="save", key="doc", content="私有文档", private=True)

        files = (await fs.execute_admin(action="list")).data["files"]
        docs = [f for f in files if f["key"] == "doc"]
        assert len(docs) == 2

        assert await _read(fs, CAT, "doc") == "私有文档"
        fs.set_config({"ai_isolation": False, "session_scope": False})
        assert await _read(fs, MAID, "doc") == "公共文档"

        # 私有更新不新建
        fs.set_config({"ai_isolation": True, "session_scope": False})
        _use(fs, CAT)
        await fs.execute(action="save", key="doc", content="私有文档2", private=True)
        files = (await fs.execute_admin(action="list")).data["files"]
        assert len([f for f in files if f["key"] == "doc"]) == 2
        assert await _read(fs, CAT, "doc") == "私有文档2"

    async def test_delete_cleans_blobs(self, file_tool):
        fs = file_tool
        _use(fs, CAT)
        await fs.execute(action="save", key="doc", content="v")
        blob_dir = Path(str(fs._storage.blob_dir))
        assert len(list(blob_dir.iterdir())) == 1
        _use(fs, CAT)
        assert (await fs.execute(action="delete", key="doc")).success
        assert len(list(blob_dir.iterdir())) == 0

    async def test_retention_expiry(self, file_tool):
        fs = file_tool
        _use(fs, CAT)
        await fs.execute(action="save", key="tmp", content="v", retention_days=0)
        # 过期文件不可见（expires_at = now）
        _use(fs, CAT)
        assert not (await fs.execute(action="get_path", key="tmp")).success

    async def test_permanent_retention(self, file_tool):
        fs = file_tool
        _use(fs, CAT)
        await fs.execute(action="save", key="keep", content="v", retention_days=-1)
        assert await _read(fs, CAT, "keep") == "v"
