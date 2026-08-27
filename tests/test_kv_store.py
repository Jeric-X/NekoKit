"""KV 存储（JSON 后端）行为测试。

覆盖：AI 隔离、user 共享层、开关切换、get 优先级、set 合并、私有记录。
"""

from conftest import CAT, CAT_G2, HUMAN, MAID, FakeContext


def _use(kv, who):
    """切换工具上下文到指定 (persona, session)"""
    kv.set_context(FakeContext(*who))


async def _set(kv, who, key, value, **kw):
    _use(kv, who)
    return await kv.execute(action="set", key=key, value=value, **kw)


class TestAIIsolation:
    async def test_private_records_invisible_across_ai(self, kv_tool, fake_context):
        kv = kv_tool
        await _set(kv, CAT, "mine", "猫娘私有")
        kv.set_context(fake_context(*MAID))
        result = await kv.execute(action="get", key="mine")
        assert not result.success

    async def test_same_ai_visible_across_sessions(self, kv_tool, fake_context):
        kv = kv_tool
        await _set(kv, CAT, "mine", "会话1写的")
        kv.set_context(fake_context(*CAT_G2))
        result = await kv.execute(action="get", key="mine")
        assert result.success and result.data["value"] == "会话1写的"

    async def test_isolation_disabled_shares_all(self, kv_tool, fake_context):
        kv = kv_tool
        await _set(kv, CAT, "mine", "猫娘的")
        kv.set_config({"ai_isolation": False, "session_scope": False})
        kv.set_context(fake_context(*MAID))
        result = await kv.execute(action="get", key="mine")
        assert result.success and result.data["value"] == "猫娘的"


class TestHumanSharedLayer:
    async def test_user_record_visible_to_all_ai(self, kv_tool, fake_context):
        kv = kv_tool
        _use(kv, HUMAN)
        await kv.execute_admin(action="set", key="notice", value="明早八点开会")
        for who in (CAT, MAID):
            kv.set_context(fake_context(*who))
            result = await kv.execute(action="get", key="notice")
            assert result.success
            assert result.data["value"] == "明早八点开会"

    async def test_ai_write_updates_user_record_in_place(self, kv_tool, fake_context):
        kv = kv_tool
        _use(kv, HUMAN)
        await kv.execute_admin(action="set", key="notice", value="v1")
        _use(kv, MAID)
        await kv.execute(action="set", key="notice", value="v2")
        _use(kv, HUMAN)
        records = (await kv.execute_admin(action="list")).data["records"]
        notice = [r for r in records if r["key"] == "notice"]
        assert len(notice) == 1 and notice[0]["ai_id"] == "user"
        kv.set_context(fake_context(*CAT))
        result = await kv.execute(action="get", key="notice")
        assert result.data["value"] == "v2"

    async def test_admin_set_existing_key_keeps_ownership(self, kv_tool, fake_context):
        kv = kv_tool
        await _set(kv, CAT, "mine", "猫娘的")
        _use(kv, HUMAN)
        await kv.execute_admin(action="set", key="mine", value="管理员改的")
        records = (await kv.execute_admin(action="list")).data["records"]
        mine = [r for r in records if r["key"] == "mine"]
        assert len(mine) == 1 and mine[0]["ai_id"] == "catgirl"


class TestGetPriorityAndMerge:
    async def test_get_prefers_own_record(self, kv_tool, fake_context):
        kv = kv_tool
        # session_scope 开启期间制造多条记录
        kv.set_config({"ai_isolation": True, "session_scope": True})
        await _set(kv, CAT, "k", "cat在会话1写的")
        await _set(kv, CAT_G2, "k", "cat在会话2写的")
        kv.set_config({"ai_isolation": True, "session_scope": False})
        kv.set_context(fake_context(*CAT))
        result = await kv.execute(action="get", key="k")
        assert result.data["value"] == "cat在会话1写的"

    async def test_get_falls_back_to_first_record(self, kv_tool, fake_context):
        kv = kv_tool
        kv.set_config({"ai_isolation": True, "session_scope": True})
        await _set(kv, CAT, "k", "cat写的")
        await _set(kv, CAT_G2, "k", "cat在会话2写的")
        kv.set_config({"ai_isolation": False, "session_scope": False})
        kv.set_context(fake_context(*MAID))
        result = await kv.execute(action="get", key="k")
        assert result.data["value"] == "cat写的"

    async def test_list_returns_all_matching_records(self, kv_tool, fake_context):
        kv = kv_tool
        kv.set_config({"ai_isolation": True, "session_scope": True})
        await _set(kv, CAT, "k", "v1")
        await _set(kv, CAT_G2, "k", "v2")
        kv.set_config({"ai_isolation": True, "session_scope": False})
        kv.set_context(fake_context(*CAT))
        result = await kv.execute(action="list")
        records = result.data["records"]
        assert len(records) == 2
        assert result.data["keys"] == ["k"]

    async def test_set_merges_duplicates_keeps_user_first(self, kv_tool, fake_context):
        kv = kv_tool
        kv.set_config({"ai_isolation": True, "session_scope": True})
        await _set(kv, CAT, "k", "cat的")
        await _set(kv, CAT_G2, "k", "cat在会话2写的")
        kv.set_config({"ai_isolation": True, "session_scope": False})
        await _set(kv, CAT, "k", "合并后的值")
        records = (await kv.execute_admin(action="list")).data["records"]
        remaining = [r for r in records if r["key"] == "k"]
        assert len(remaining) == 1
        assert remaining[0]["ai_id"] == "catgirl"
        kv.set_config({"ai_isolation": False, "session_scope": False})
        kv.set_context(fake_context(*MAID))
        result = await kv.execute(action="get", key="k")
        assert result.data["value"] == "合并后的值"

    async def test_delete_removes_all_visible(self, kv_tool, fake_context):
        kv = kv_tool
        kv.set_config({"ai_isolation": True, "session_scope": True})
        await _set(kv, CAT, "k", "v1")
        await _set(kv, CAT_G2, "k", "v2")
        kv.set_config({"ai_isolation": True, "session_scope": False})
        kv.set_context(fake_context(*CAT))
        result = await kv.execute(action="delete", key="k")
        assert result.success
        records = (await kv.execute_admin(action="list")).data["records"]
        assert all(r["key"] != "k" for r in records)


class TestPrivateRecords:
    async def test_private_invisible_even_when_sharing_all(self, kv_tool, fake_context):
        kv = kv_tool
        kv.set_config({"ai_isolation": False, "session_scope": False})
        await _set(kv, CAT, "secret", "猫娘的秘密", private=True)

        # 写入者自己可见
        kv.set_context(fake_context(*CAT))
        result = await kv.execute(action="get", key="secret")
        assert result.success and result.data["value"] == "猫娘的秘密"

        # 同 AI 不同会话不可见
        kv.set_context(fake_context(*CAT_G2))
        assert not (await kv.execute(action="get", key="secret")).success

        # 其他 AI 不可见（get 与 list）
        kv.set_context(fake_context(*MAID))
        assert not (await kv.execute(action="get", key="secret")).success
        listed = (await kv.execute(action="list")).data["records"]
        assert all(r["key"] != "secret" for r in listed)

    async def test_admin_sees_private_with_flag(self, kv_tool, fake_context):
        kv = kv_tool
        kv.set_config({"ai_isolation": False, "session_scope": False})
        await _set(kv, CAT, "secret", "s", private=True)
        kv.set_context(fake_context(*HUMAN))
        records = (await kv.execute_admin(action="list")).data["records"]
        secret = [r for r in records if r["key"] == "secret"]
        assert len(secret) == 1
        assert secret[0]["private"] is True
        assert secret[0]["ai_id"] == "catgirl"

    async def test_private_and_public_coexist(self, kv_tool, fake_context):
        kv = kv_tool
        await _set(kv, CAT, "note", "公共笔记")
        await _set(kv, CAT, "note", "私有笔记", private=True)
        records = (await kv.execute_admin(action="list")).data["records"]
        notes = [r for r in records if r["key"] == "note"]
        assert len(notes) == 2
        assert sorted(n["private"] for n in notes) == [False, True]

    async def test_get_prefers_own_private(self, kv_tool, fake_context):
        kv = kv_tool
        await _set(kv, CAT, "note", "公共笔记")
        await _set(kv, CAT, "note", "私有笔记", private=True)
        kv.set_context(fake_context(*CAT))
        result = await kv.execute(action="get", key="note")
        assert result.data["value"] == "私有笔记"
        # 其他 AI（关闭隔离）看到公共的那条
        kv.set_config({"ai_isolation": False, "session_scope": False})
        kv.set_context(fake_context(*MAID))
        result = await kv.execute(action="get", key="note")
        assert result.data["value"] == "公共笔记"

    async def test_private_write_updates_own_private_only(self, kv_tool, fake_context):
        kv = kv_tool
        await _set(kv, CAT, "note", "公共笔记")
        await _set(kv, CAT, "note", "私有笔记", private=True)
        await _set(kv, CAT, "note", "私有笔记2", private=True)
        records = (await kv.execute_admin(action="list")).data["records"]
        notes = [r for r in records if r["key"] == "note"]
        assert len(notes) == 2  # 未新建
        kv.set_context(fake_context(*CAT))
        result = await kv.execute(action="get", key="note")
        assert result.data["value"] == "私有笔记2"
        kv.set_config({"ai_isolation": False, "session_scope": False})
        kv.set_context(fake_context(*MAID))
        result = await kv.execute(action="get", key="note")
        assert result.data["value"] == "公共笔记"  # 公共记录未被动

    async def test_public_write_does_not_touch_private(self, kv_tool, fake_context):
        kv = kv_tool
        await _set(kv, CAT, "note", "私有笔记", private=True)
        await _set(kv, CAT, "note", "公共笔记")  # 公共写入
        records = (await kv.execute_admin(action="list")).data["records"]
        notes = [r for r in records if r["key"] == "note"]
        assert len(notes) == 2  # 私有记录未被合并/覆盖
