"""
대화 스크립트 존재 확인 단위 테스트

can_talk 산출은 configs/dialogues/{npc_id}.lua 존재 여부에 의존한다.
파일을 읽지 않고 확인해야 방 정보를 만들 때마다 호출할 수 있다.
"""

import os

from src.mud_engine.game.lua_script_loader import LuaScriptLoader


class TestGetScriptPath:
    """경로 생성"""

    def test_path_uses_npc_id(self):
        loader = LuaScriptLoader()
        path = loader.get_script_path("3914fbe8-c8a9-493a-b451-1084ee4d6d2a")

        assert path == os.path.join(
            "configs", "dialogues", "3914fbe8-c8a9-493a-b451-1084ee4d6d2a.lua"
        )

    def test_path_is_relative_to_configs(self):
        loader = LuaScriptLoader()
        path = loader.get_script_path("any-id")

        assert path.startswith(os.path.join("configs", "dialogues"))
        assert path.endswith(".lua")


class TestHasDialogueScript:
    """존재 확인"""

    def test_returns_false_for_unknown_id(self):
        loader = LuaScriptLoader()
        assert loader.has_dialogue_script("no-such-npc-id") is False

    def test_returns_true_for_existing_script(self, tmp_path, monkeypatch):
        """실제 파일이 있으면 참을 반환한다"""
        loader = LuaScriptLoader()

        script_dir = tmp_path / "configs" / "dialogues"
        script_dir.mkdir(parents=True)
        (script_dir / "npc-1.lua").write_text("-- stub", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        assert loader.has_dialogue_script("npc-1") is True

    def test_directory_is_not_treated_as_script(self, tmp_path, monkeypatch):
        """같은 이름의 디렉터리를 스크립트로 오인하지 않는다"""
        loader = LuaScriptLoader()

        script_dir = tmp_path / "configs" / "dialogues" / "npc-2.lua"
        script_dir.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)
        assert loader.has_dialogue_script("npc-2") is False

    def test_does_not_read_file(self, tmp_path, monkeypatch):
        """파일을 읽지 않으므로 내용이 깨져 있어도 참을 반환한다"""
        loader = LuaScriptLoader()

        script_dir = tmp_path / "configs" / "dialogues"
        script_dir.mkdir(parents=True)
        # UTF-8 로 디코딩할 수 없는 바이트
        (script_dir / "npc-3.lua").write_bytes(b"\xff\xfe\x00invalid")

        monkeypatch.chdir(tmp_path)
        assert loader.has_dialogue_script("npc-3") is True

    def test_matches_production_scripts(self):
        """프로덕션 스크립트가 있으면 확인된다

        configs/dialogues 에는 NPC 인스턴스 id 를 파일명으로 하는 스크립트가 있다.
        실행 위치가 프로젝트 루트가 아니면 건너뛴다.
        """
        script_dir = os.path.join("configs", "dialogues")
        if not os.path.isdir(script_dir):
            return

        names = [n for n in os.listdir(script_dir) if n.endswith(".lua")]
        if not names:
            return

        loader = LuaScriptLoader()
        npc_id = os.path.splitext(names[0])[0]

        assert loader.has_dialogue_script(npc_id) is True
