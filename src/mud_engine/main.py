"""
MUD Engine 메인 실행 파일
"""

import asyncio
import logging
import os
import signal
import sys

from dotenv import load_dotenv

from .database import get_database_manager, close_database_manager
from .game.managers import PlayerManager
from .game.repositories import PlayerRepository
from .server.telnet_server import TelnetServer
from .core.game_engine import GameEngine
from .server.session_manager import SessionManager


def setup_logging():
    """로깅 설정 - 새로운 포맷 및 파일 관리 규칙 적용"""
    import logging.handlers
    from datetime import datetime

    log_level = os.getenv("LOG_LEVEL", "INFO")

    # 로그 디렉토리 생성
    os.makedirs('logs', exist_ok=True)

    # 커스텀 포맷터 클래스
    class MudEngineFormatter(logging.Formatter):
        def format(self, record):
            # 시분초.밀리초 형식
            timestamp = self.formatTime(record, '%H:%M:%S')
            ms = int(record.created * 1000) % 1000
            time_with_ms = f"{timestamp}.{ms:03d}"

            # 모듈명에서 마지막 부분만 추출 (클래스명)
            module_name = record.name
            if '.' in module_name:
                short_name = module_name.split('.')[-1]
            else:
                short_name = module_name

            # 파일명과 라인 번호
            filename = record.filename
            lineno = record.lineno
            location = f"[{short_name}:{lineno}]"

            # 최종 포맷: {시분초.ms} {LEVEL} [{short_name:line}] {logstring}
            return f"{time_with_ms} {record.levelname} {location} {record.getMessage()}"

    # 커스텀 로테이팅 핸들러
    class CustomRotatingHandler(logging.handlers.BaseRotatingHandler):
        """날짜와 크기 기반 로그 로테이션 핸들러"""

        def __init__(self, filename, maxBytes=200*1024*1024, backupCount=30, encoding='utf-8'):
            self.maxBytes = maxBytes
            self.backupCount = backupCount
            self.current_date = datetime.now().strftime('%Y%m%d')
            self.file_number = 1

            # 파일명 생성
            self.base_filename = filename
            self.current_filename = self._get_current_filename()

            super().__init__(self.current_filename, 'a', encoding=encoding)

        def _get_current_filename(self):
            """현재 로그 파일명 생성"""
            today = datetime.now().strftime('%Y%m%d')
            if today != self.current_date:
                self.current_date = today
                self.file_number = 1

            return f"logs/mud_engine-{self.current_date}-{self.file_number:02d}.log"

        def shouldRollover(self, record):
            """로테이션 필요 여부 확인"""
            # 날짜 변경 확인
            today = datetime.now().strftime('%Y%m%d')
            if today != self.current_date:
                return True

            # 파일 크기 확인
            if self.stream is None:
                self.stream = self._open()

            if self.maxBytes > 0:
                msg = "%s\n" % self.format(record)
                self.stream.seek(0, 2)  # EOF로 이동
                if self.stream.tell() + len(msg) >= self.maxBytes:
                    return True

            return False

        def doRollover(self):
            """로그 파일 로테이션 수행"""
            if self.stream:
                self.stream.close()
                self.stream = None

            # 현재 파일 압축
            import gzip
            import shutil

            current_file = self.current_filename
            if os.path.exists(current_file):
                compressed_file = f"{current_file}.gz"
                with open(current_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(current_file)

            # 새 파일명 생성
            today = datetime.now().strftime('%Y%m%d')
            if today != self.current_date:
                self.current_date = today
                self.file_number = 1
            else:
                self.file_number += 1

            self.current_filename = self._get_current_filename()
            self.baseFilename = self.current_filename

            # 새 스트림 열기
            if not self.delay:
                self.stream = self._open()

            # 오래된 로그 파일 정리
            self._cleanup_old_logs()

        def _cleanup_old_logs(self):
            """오래된 로그 파일 정리"""
            log_dir = os.path.dirname(self.current_filename)
            if not os.path.exists(log_dir):
                return

            # 로그 파일 목록 가져오기
            log_files = []
            for filename in os.listdir(log_dir):
                if filename.startswith('mud_engine-') and filename.endswith('.log.gz'):
                    filepath = os.path.join(log_dir, filename)
                    log_files.append((os.path.getctime(filepath), filepath))

            # 생성 시간 기준 정렬
            log_files.sort()

            # 백업 개수 초과 시 오래된 파일 삭제
            while len(log_files) > self.backupCount:
                _, old_file = log_files.pop(0)
                try:
                    os.remove(old_file)
                except OSError:
                    pass

    class ExcludeLoggerFilter(logging.Filter):
        def __init__(self, exclude_name):
            self.exclude_name = exclude_name

        def filter(self, record):
            # 로거 이름이 exclude_name과 같으면 필터링하여 True를 반환하지 않음
            if record.name == self.exclude_name:
                return False
            return True

    # 포맷터 생성
    formatter = MudEngineFormatter()

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(ExcludeLoggerFilter("aiosqlite"))

    # 파일 핸들러 (커스텀 로테이팅)
    file_handler = CustomRotatingHandler(
        filename='logs/mud_engine.log',
        maxBytes=200 * 1024 * 1024,  # 200MB
        backupCount=30
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(ExcludeLoggerFilter("aiosqlite"))

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


async def main():
    """메인 함수"""
    load_dotenv()
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("MUD Engine 시작 중...")
    print("🎮 Python MUD Engine v0.1.0")

    # 종료 이벤트 생성
    shutdown_event = asyncio.Event()

    # Signal 핸들러 설정
    def signal_handler(signum, frame):
        logger.info(f"Signal {signum} 수신됨. 서버 종료 절차 시작...")
        print(f"\n🛑 Signal {signum} 수신됨. 서버 종료 중...")
        raise KeyboardInterrupt()
        shutdown_event.set()

    # Windows와 Unix 모두 지원
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, signal_handler)

    telnet_server = None
    game_engine = None
    try:
        # 데이터베이스 초기화
        logger.info("데이터베이스 매니저 생성 중...")
        db_manager = await get_database_manager()
        logger.info("데이터베이스 매니저 생성 완료.")

        # 관리자 클래스 초기화
        logger.info("게임 관리자 클래스 초기화 중...")
        player_repo = PlayerRepository(db_manager)
        player_manager = PlayerManager(player_repo)
        logger.info("게임 관리자 클래스 초기화 완료.")

        # 세션 관리자 초기화
        logger.info("세션 관리자 초기화 중...")
        session_manager = SessionManager()
        logger.info("세션 관리자 초기화 완료.")

        # 게임 엔진 초기화 및 시작
        logger.info("게임 엔진 초기화 중...")
        game_engine = GameEngine(session_manager, player_manager, db_manager)
        await game_engine.start()
        logger.info("게임 엔진 시작 완료.")

        # Telnet 서버 초기화 및 시작
        telnet_host = os.getenv("TELNET_HOST", "0.0.0.0")
        telnet_port = int(os.getenv("TELNET_PORT", "4000"))
        telnet_server = TelnetServer(telnet_host, telnet_port, player_manager, db_manager)

        # 게임 엔진을 Telnet 서버에 연결
        telnet_server.game_engine = game_engine
        game_engine.telnet_server = telnet_server

        await telnet_server.start()

        print(f"📡 Telnet 서버가 telnet://{telnet_host}:{telnet_port} 에서 실행 중입니다.")
        print("Ctrl+C를 눌러 서버를 종료할 수 있습니다.")

        # 서버가 계속 실행되도록 유지 (shutdown_event 대기)
        try:
            await shutdown_event.wait()
        except KeyboardInterrupt:
            logger.info("Ctrl+C 감지됨. 서버 종료 절차 시작...")
            print("\n🛑 서버 종료 중...")

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt 감지됨. 서버 종료 절차 시작...")
        print("\n🛑 서버 종료 중...")
    except Exception as e:
        logger.error(f"초기화 또는 실행 중 오류 발생: {e}", exc_info=True)
        print(f"❌ 치명적인 오류 발생: {e}")
    finally:
        logger.info("MUD Engine 종료 절차 시작...")

        # Telnet 서버 종료
        if telnet_server:
            await telnet_server.stop()

        # 게임 엔진 종료
        if game_engine:
            await game_engine.stop()

        # 비동기 태스크 정리 대기
        await asyncio.sleep(0.5)

        await close_database_manager()
        logger.info("MUD Engine이 성공적으로 종료되었습니다.")
        print("👋 MUD Engine 종료.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass # main 함수의 finally 블록에서 종료 처리를 하므로 여기서는 pass
