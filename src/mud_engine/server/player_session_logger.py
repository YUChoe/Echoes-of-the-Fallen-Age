# -*- coding: utf-8 -*-
"""
플레이어별 세션 로그 관리 모듈

인증된 각 플레이어의 세션 활동을 개별 로그 파일에 기록한다. 파일명은
`logs/players/{player_id}-{YYYYMMDD}.log` 다. 날짜를 넣는 것은 로그 줄이 시각만
담기 때문이다. 한 파일에 여러 날이 쌓이면 어제 줄과 오늘 줄이 구별되지 않는다.

Python 표준 logging 모듈의 named logger 방식을 사용하며, 기존 통합
로그(Global_Logger)에는 영향을 주지 않는다.
"""

import gzip
import logging
import logging.handlers
import os
import shutil
from datetime import date
from typing import Any, Dict, Optional


# 글로벌 로거 (오류 보고용)
logger = logging.getLogger(__name__)

# 플레이어 로그 디렉토리
PLAYER_LOG_DIR = "logs/players"

# 로테이션 설정
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5

# params 를 한 줄에 담을 때의 상한. 대사 선택지나 채팅이 길어질 수 있다
MAX_PARAMS_LENGTH = 200


def write(player_id: str, message: str) -> None:
    """설정된 플레이어 로거에만 기록한다.

    로거를 인스턴스로 들고 다니지 않아도 되게 모듈 함수로 둔다. 액션
    디스패처처럼 `PlayerSessionLogger` 를 참조하지 않는 곳에서도 쓴다.

    핸들러가 없으면 버린다. 인증 전이거나 세션이 끝난 뒤다. 그대로 기록하면
    `propagate` 기본값 때문에 통합 로그로 새어 나간다.
    """
    if not player_id:
        return

    player_logger = logging.getLogger(f"player.{player_id}")
    if not player_logger.handlers:
        return

    player_logger.info(message)


def log_action(
    player_id: str,
    verb: str,
    target: Optional[str],
    params: Optional[Dict[str, Any]],
    outcome: str,
) -> None:
    """액션 한 건을 기록한다.

    대상은 uuid 를 그대로 적는다. 번호 기반 대상 지정은 폐기됐고, 로그를
    사후에 읽을 때 그 번호로는 무엇을 가리켰는지 되찾을 수 없다.

    Args:
        player_id: 플레이어 고유 ID
        verb: 액션 동사
        target: 대상 uuid. 없으면 생략한다
        params: 액션 파라미터. 없으면 생략한다
        outcome: 결과. `success` 또는 `rejected(CODE)` 형태
    """
    parts = [f"액션: {verb}"]

    if target:
        parts.append(f"target={target}")

    if params:
        text = str(params)
        if len(text) > MAX_PARAMS_LENGTH:
            text = text[:MAX_PARAMS_LENGTH] + "…"
        parts.append(f"params={text}")

    parts.append(f"-> {outcome}")
    write(player_id, " ".join(parts))


def log_chat(
    player_id: str, channel: str, content: str, target: Optional[str] = None
) -> None:
    """채팅 한 건을 기록한다.

    Args:
        player_id: 말한 사람
        channel: `room` 또는 `whisper`
        content: 발화 내용
        target: 귓속말 대상 uuid
    """
    parts = [f"채팅[{channel}]"]

    if target:
        parts.append(f"target={target}")

    parts.append(content)
    write(player_id, " ".join(parts))


class PlayerSessionFormatter(logging.Formatter):
    """플레이어 세션 로그 포맷터.

    파일명 자체가 player_id이므로 로거 이름/라인 번호는 생략한다.
    포맷: {HH:MM:SS.mmm} {LEVEL} {message}
    """

    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 포맷팅한다."""
        timestamp = self.formatTime(record, '%H:%M:%S')
        ms = int(record.created * 1000) % 1000
        time_with_ms = f"{timestamp}.{ms:03d}"
        return f"{time_with_ms} {record.levelname} {record.getMessage()}"


class GzipRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """로테이션 시 백업 파일을 gzip 압축하는 RotatingFileHandler.

    기존 통합 로그의 CustomRotatingHandler와 동일한 압축 방식을 사용한다.
    백업 파일명 형식: {player_id}.log.{n}.gz
    """

    def doRollover(self) -> None:
        """로테이션 수행. 백업 파일을 .gz로 압축한다."""
        # 현재 스트림 닫기
        if self.stream:
            self.stream.close()
            self.stream = None  # type: ignore[assignment]

        # 가장 오래된 백업이 backupCount를 초과하면 삭제
        if self.backupCount > 0:
            # 기존 .gz 백업 파일들의 번호를 시프트
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename(f"{self.baseFilename}.{i}.gz")
                dfn = self.rotation_filename(f"{self.baseFilename}.{i + 1}.gz")
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)

            # 현재 로그 파일을 .1.gz로 압축
            dfn = self.rotation_filename(f"{self.baseFilename}.1.gz")
            if os.path.exists(dfn):
                os.remove(dfn)

            if os.path.exists(self.baseFilename):
                with open(self.baseFilename, 'rb') as f_in:
                    with gzip.open(dfn, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(self.baseFilename)

        # backupCount 초과 시 가장 오래된 백업 삭제
        if self.backupCount > 0:
            oldest = self.rotation_filename(
                f"{self.baseFilename}.{self.backupCount + 1}.gz"
            )
            if os.path.exists(oldest):
                os.remove(oldest)

        # 새 스트림 열기
        if not self.delay:
            self.stream = self._open()


class PlayerSessionLogger:
    """플레이어별 세션 로그 관리자.

    인증된 플레이어마다 개별 named logger를 생성하고,
    GzipRotatingFileHandler를 부착하여 세션 활동을 기록한다.
    """

    def __init__(self) -> None:
        """초기화. logs/players/ 디렉토리를 생성하고 내부 상태를 초기화한다."""
        try:
            os.makedirs(PLAYER_LOG_DIR, exist_ok=True)
        except OSError as e:
            logger.error(f"플레이어 로그 디렉토리 생성 실패: {e}")

        # 활성 플레이어 로거 추적 (player_id -> logger_name)
        self._active_loggers: Dict[str, str] = {}
        # 공유 포맷터 인스턴스
        self._formatter = PlayerSessionFormatter()

    def setup_player_logger(
        self,
        player_id: str,
        player_username: str,
        session_id: str,
        ip_address: str,
    ) -> None:
        """플레이어별 로거를 설정하고 세션 시작 로그를 기록한다.

        이미 핸들러가 존재하면 기존 것을 정리 후 재설정한다.

        Args:
            player_id: 플레이어 고유 ID
            player_username: 플레이어 사용자명
            session_id: 세션 고유 ID
            ip_address: 클라이언트 IP 주소
        """
        try:
            # 기존 핸들러가 있으면 정리
            if player_id in self._active_loggers:
                self.cleanup_player_logger(player_id)

            logger_name = f"player.{player_id}"
            player_logger = logging.getLogger(logger_name)
            player_logger.setLevel(logging.INFO)
            # 루트 로거로 전파 차단
            player_logger.propagate = False

            # GzipRotatingFileHandler 부착. 파일명에 날짜를 넣는다.
            # 자정을 넘긴 세션은 시작한 날의 파일에 계속 쓴다. 통합 로그와
            # 같은 규칙이며, 한 세션의 줄이 두 파일로 갈리지 않는 편이 낫다
            today = date.today().strftime("%Y%m%d")
            log_file = os.path.join(PLAYER_LOG_DIR, f"{player_id}-{today}.log")
            handler = GzipRotatingFileHandler(
                filename=log_file,
                maxBytes=MAX_BYTES,
                backupCount=BACKUP_COUNT,
                encoding='utf-8',
            )
            handler.setFormatter(self._formatter)
            player_logger.addHandler(handler)

            # 활성 로거 추적
            self._active_loggers[player_id] = logger_name

            # 세션 시작 로그 기록
            player_logger.info(
                "세션 시작 - session_id=%s, player_id=%s, username=%s, ip=%s",
                session_id,
                player_id,
                player_username,
                ip_address,
            )
        except Exception as e:
            logger.error(f"플레이어 로거 설정 실패 (player_id={player_id}): {e}")

    def log_session_end(self, player_id: str, reason: str) -> None:
        """세션 종료 로그를 기록한다.

        Args:
            player_id: 플레이어 고유 ID
            reason: 종료 사유
        """
        try:
            if player_id not in self._active_loggers:
                return

            logger_name = self._active_loggers[player_id]
            player_logger = logging.getLogger(logger_name)
            player_logger.info("세션 종료 - 사유: %s", reason)
        except Exception as e:
            logger.warning(f"세션 종료 로그 기록 실패 (player_id={player_id}): {e}")

    def cleanup_player_logger(self, player_id: str) -> None:
        """플레이어 로거의 핸들러를 제거하고 닫는다.

        Args:
            player_id: 플레이어 고유 ID
        """
        try:
            if player_id not in self._active_loggers:
                return

            logger_name = self._active_loggers.pop(player_id)
            player_logger = logging.getLogger(logger_name)

            # 모든 핸들러 제거 및 close
            for handler in player_logger.handlers[:]:
                player_logger.removeHandler(handler)
                handler.close()
        except Exception as e:
            logger.warning(
                f"플레이어 로거 정리 실패 (player_id={player_id}): {e}"
            )

    def cleanup_all(self) -> None:
        """모든 활성 플레이어 로거의 핸들러를 정리한다."""
        # 딕셔너리 순회 중 변경을 피하기 위해 키 목록 복사
        player_ids = list(self._active_loggers.keys())
        for player_id in player_ids:
            try:
                self.cleanup_player_logger(player_id)
            except Exception as e:
                logger.warning(
                    f"cleanup_all 중 로거 정리 실패 (player_id={player_id}): {e}"
                )
