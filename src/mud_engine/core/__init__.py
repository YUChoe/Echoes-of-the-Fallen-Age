# -*- coding: utf-8 -*-
"""MUD 게임 엔진 코어 모듈

재export를 두지 않는다. `core.game_engine` 을 여기서 즉시 임포트하면
`core.localization` 같은 하위 모듈 하나를 불러도 GameEngine 초기화 연쇄가
돌아 순환 임포트가 발생한다. 필요한 심볼은 하위 모듈에서 직접 임포트한다.
"""
