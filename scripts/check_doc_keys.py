#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계약 문서의 예시에 나오는 번역 키가 실재하는지 확인한다.

서버 코드가 그 키를 쓰는지, 클라이언트 번역 파일에 있는지 둘 다 본다. 어느
쪽에도 없으면 예시가 지어낸 키다. 실제로 `combat.damage_dealt` 가 그랬고,
클라이언트를 그 예시대로 구현하다가 드러났다.

클라이언트 저장소 경로가 필요하다. 인자로 받거나 형제 디렉터리에서 찾는다.

실행:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_doc_keys.py
    ... scripts/check_doc_keys.py <클라이언트 저장소 경로>
"""

import json
import pathlib
import re
import sys

SERVER = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_CLIENT = SERVER.parent / "KarnasChronicles-DividedDominio-client"
CLIENT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CLIENT
DOCS = SERVER / "docs" / "protocol"
TRANSLATIONS = CLIENT / "godot" / "resources" / "translations"

KEY_IN_DOC = re.compile(r'"(?:key|message_key)"\s*:\s*"([a-z][\w.]+)"')


def main() -> int:
    if not TRANSLATIONS.is_dir():
        print("번역 디렉터리를 찾을 수 없습니다: %s" % TRANSLATIONS)
        print("클라이언트 저장소 경로를 인자로 주세요")
        return 2

    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (SERVER / "src").rglob("*.py")
    )

    known: set[str] = set()
    for path in TRANSLATIONS.glob("*.json"):
        known |= set(json.loads(path.read_text(encoding="utf-8")))

    missing: list[tuple[str, str]] = []
    seen: set[str] = set()

    for doc in sorted(DOCS.glob("*.md")):
        for key in KEY_IN_DOC.findall(doc.read_text(encoding="utf-8")):
            if key in seen:
                continue
            seen.add(key)

            in_server = '"%s"' % key in source
            in_client = key in known

            if not in_server and not in_client:
                missing.append((doc.name, key))
            elif not in_client:
                missing.append((doc.name, "%s  (서버만 있고 번역 없음)" % key))

    print("문서 예시의 키 %d개, 번역 파일 %d개" % (len(seen), len(known)))

    if missing:
        print("확인 필요:")
        for doc, key in missing:
            print("  %-22s %s" % (doc, key))
        return 1

    print("모두 실재한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
