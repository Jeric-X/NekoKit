"""KV 存储（SQLite 后端）行为测试：与 JSON 后端同套语义。"""

from conftest import CAT, CAT_G2, HUMAN, MAID, FakeContext


def _use(kv, who):
    kv.set_context(FakeContext(*who))


class TestSQLiteBackend:
    async def test_basic_isolation(self, kv_tool_sqlite):
        kv = kv_tool_sqlite
        _use(kv, CAT)
        await kv.execute(action="set", key="mine", value="猫娘私有")
        _use(kv, MAID)
        assert not (await kv.execute(action="get", key="mine")).success

    async def test_user_shared_layer(self, kv_tool_sqlite):
        kv = kv_tool_sqlite
        _use(kv, HUMAN)
        await kv.execute_admin(action="set", key="notice", value="通知")
        for who in (CAT, MAID):
            _use(kv, who)
            result = await kv.execute(action="get", key="notice")
            assert result.success and result.data["value"] == "通知"

    async def test_get_priority_and_merge(self, kv_tool_sqlite):
        kv = kv_tool_sqlite
        kv.set_config({"ai_isolation": True, "session_scope": True})
        _use(kv, CAT)
        await kv.execute(action="set", key="k", value="cat-g1")
        _use(kv, CAT_G2)
        await kv.execute(action="set", key="k", value="cat-g2")
        kv.set_config({"ai_isolation": True, "session_scope": False})

        _use(kv, CAT)
        assert (await kv.execute(action="get", key="k")).data["value"] == "cat-g1"
        kv.set_config({"ai_isolation": False, "session_scope": False})
        _use(kv, MAID)
        assert (await kv.execute(action="get", key="k")).data["value"] == "cat-g1"
        kv.set_config({"ai_isolation": True, "session_scope": False})

        records = (await kv.execute_admin(action="list")).data["records"]
        assert len([r for r in records if r["key"] == "k"]) == 2

        _use(kv, CAT)
        await kv.execute(action="set", key="k", value="merged")
        records = (await kv.execute_admin(action="list")).data["records"]
        remaining = [r for r in records if r["key"] == "k"]
        assert len(remaining) == 1 and remaining[0]["session_id"] == "group1"

    async def test_private_records(self, kv_tool_sqlite):
        kv = kv_tool_sqlite
        kv.set_config({"ai_isolation": False, "session_scope": False})
        _use(kv, CAT)
        await kv.execute(action="set", key="s", value="秘密", private=True)

        _use(kv, CAT_G2)
        assert not (await kv.execute(action="get", key="s")).success
        _use(kv, MAID)
        assert not (await kv.execute(action="get", key="s")).success
        _use(kv, CAT)
        assert (await kv.execute(action="get", key="s")).data["value"] == "秘密"

        # 同三元组公共/私有两行共存（PK 含 is_private）
        kv.set_config({"ai_isolation": True, "session_scope": False})
        await kv.execute(action="set", key="s", value="公共")
        _use(kv, HUMAN)
        records = (await kv.execute_admin(action="list")).data["records"]
        ss = [r for r in records if r["key"] == "s"]
        assert len(ss) == 2
        assert sorted(r["private"] for r in ss) == [False, True]

        _use(kv, CAT)
        assert (await kv.execute(action="get", key="s")).data["value"] == "秘密"

    async def test_delete_removes_visible(self, kv_tool_sqlite):
        kv = kv_tool_sqlite
        _use(kv, CAT)
        await kv.execute(action="set", key="k", value="v")
        assert (await kv.execute(action="delete", key="k")).success
        assert not (await kv.execute(action="get", key="k")).success

    async def test_search(self, kv_tool_sqlite):
        kv = kv_tool_sqlite
        _use(kv, CAT)
        await kv.execute(action="set", key="hello_world", value="v")
        await kv.execute(action="set", key="other", value="v")
        results = (await kv.execute(action="search", key="hello")).data["results"]
        assert len(results) == 1 and results[0]["key"] == "hello_world"
