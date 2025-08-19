"""
번역 관리 도구

대량의 번역 텍스트를 효율적으로 관리하기 위한 도구들
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

from .default_translations import get_default_translations, validate_default_translations
from .utils import TranslationFileManager

logger = logging.getLogger(__name__)


class TranslationManager:
    """번역 관리 도구 클래스"""

    def __init__(self, translations_dir: str = "data/translations"):
        """
        TranslationManager 초기화

        Args:
            translations_dir: 번역 파일 디렉토리
        """
        self.translations_dir = Path(translations_dir)
        self.file_manager = TranslationFileManager(str(self.translations_dir))

        logger.info(f"TranslationManager 초기화: {self.translations_dir}")

    def sync_default_translations_to_files(self) -> bool:
        """
        기본 번역을 파일로 동기화

        Returns:
            bool: 동기화 성공 여부
        """
        try:
            default_translations = get_default_translations()

            for locale, translations in default_translations.items():
                success = self.file_manager.create_translation_file(locale, translations)
                if not success:
                    logger.error(f"기본 번역 파일 생성 실패: {locale}")
                    return False

            logger.info("기본 번역을 파일로 동기화 완료")
            return True

        except Exception as e:
            logger.error(f"기본 번역 동기화 실패: {e}")
            return False

    def merge_translations_from_files(self) -> Dict[str, Dict[str, str]]:
        """
        모든 번역 파일을 병합하여 반환

        Returns:
            Dict[str, Dict[str, str]]: 병합된 번역 데이터
        """
        merged_translations = {}

        try:
            available_locales = self.file_manager.get_available_locales()

            for locale in available_locales:
                translations = self.file_manager.load_translation_file(locale)
                if translations:
                    merged_translations[locale] = translations

            logger.info(f"번역 파일 병합 완료: {len(merged_translations)}개 로케일")
            return merged_translations

        except Exception as e:
            logger.error(f"번역 파일 병합 실패: {e}")
            return {}

    def find_missing_translations(self) -> Dict[str, List[str]]:
        """
        누락된 번역 키 찾기

        Returns:
            Dict[str, List[str]]: 로케일별 누락된 키 목록
        """
        missing_translations = {}

        try:
            merged_translations = self.merge_translations_from_files()

            if not merged_translations:
                return missing_translations

            # 모든 키 수집
            all_keys = set()
            for translations in merged_translations.values():
                all_keys.update(translations.keys())

            # 각 로케일에서 누락된 키 찾기
            for locale, translations in merged_translations.items():
                locale_keys = set(translations.keys())
                missing = all_keys - locale_keys

                if missing:
                    missing_translations[locale] = sorted(list(missing))

            logger.info(f"누락된 번역 검사 완료: {len(missing_translations)}개 로케일에서 누락 발견")
            return missing_translations

        except Exception as e:
            logger.error(f"누락된 번역 검사 실패: {e}")
            return {}

    def find_unused_translations(self, used_keys: Set[str]) -> Dict[str, List[str]]:
        """
        사용되지 않는 번역 키 찾기

        Args:
            used_keys: 실제로 사용되는 키 집합

        Returns:
            Dict[str, List[str]]: 로케일별 사용되지 않는 키 목록
        """
        unused_translations = {}

        try:
            merged_translations = self.merge_translations_from_files()

            for locale, translations in merged_translations.items():
                locale_keys = set(translations.keys())
                unused = locale_keys - used_keys

                if unused:
                    unused_translations[locale] = sorted(list(unused))

            logger.info(f"사용되지 않는 번역 검사 완료: {len(unused_translations)}개 로케일에서 발견")
            return unused_translations

        except Exception as e:
            logger.error(f"사용되지 않는 번역 검사 실패: {e}")
            return {}

    def generate_translation_template(self, keys: List[str], target_locale: str) -> Dict[str, str]:
        """
        번역 템플릿 생성

        Args:
            keys: 번역할 키 목록
            target_locale: 대상 로케일

        Returns:
            Dict[str, str]: 번역 템플릿
        """
        template = {}

        for key in keys:
            template[key] = f"[TODO: {target_locale}] {key}"

        logger.info(f"번역 템플릿 생성: {len(keys)}개 키 ({target_locale})")
        return template

    def export_translations_to_csv(self, output_file: str) -> bool:
        """
        번역을 CSV 파일로 내보내기

        Args:
            output_file: 출력 파일 경로

        Returns:
            bool: 내보내기 성공 여부
        """
        try:
            import csv

            merged_translations = self.merge_translations_from_files()

            if not merged_translations:
                logger.warning("내보낼 번역 데이터가 없습니다")
                return False

            # 모든 키 수집
            all_keys = set()
            for translations in merged_translations.values():
                all_keys.update(translations.keys())

            all_keys = sorted(list(all_keys))
            locales = sorted(list(merged_translations.keys()))

            # CSV 파일 작성
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # 헤더 작성
                header = ['key'] + locales
                writer.writerow(header)

                # 데이터 작성
                for key in all_keys:
                    row = [key]
                    for locale in locales:
                        value = merged_translations[locale].get(key, '')
                        row.append(value)
                    writer.writerow(row)

            logger.info(f"번역 CSV 내보내기 완료: {output_file}")
            return True

        except Exception as e:
            logger.error(f"번역 CSV 내보내기 실패: {e}")
            return False

    def import_translations_from_csv(self, input_file: str) -> bool:
        """
        CSV 파일에서 번역 가져오기

        Args:
            input_file: 입력 파일 경로

        Returns:
            bool: 가져오기 성공 여부
        """
        try:
            import csv

            translations_by_locale = {}

            with open(input_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                # 헤더에서 로케일 추출
                locales = [col for col in reader.fieldnames if col != 'key']

                for locale in locales:
                    translations_by_locale[locale] = {}

                # 데이터 읽기
                for row in reader:
                    key = row['key']
                    for locale in locales:
                        value = row.get(locale, '').strip()
                        if value:  # 빈 값은 제외
                            translations_by_locale[locale][key] = value

            # 파일로 저장
            for locale, translations in translations_by_locale.items():
                if translations:  # 빈 번역은 제외
                    success = self.file_manager.create_translation_file(locale, translations)
                    if not success:
                        logger.error(f"번역 파일 저장 실패: {locale}")
                        return False

            logger.info(f"번역 CSV 가져오기 완료: {input_file}")
            return True

        except Exception as e:
            logger.error(f"번역 CSV 가져오기 실패: {e}")
            return False

    def generate_translation_report(self) -> Dict[str, Any]:
        """
        번역 상태 보고서 생성

        Returns:
            Dict[str, Any]: 번역 상태 보고서
        """
        report = {
            'timestamp': None,
            'total_locales': 0,
            'total_keys': 0,
            'locales': {},
            'missing_translations': {},
            'validation_errors': [],
            'file_stats': {}
        }

        try:
            from datetime import datetime
            report['timestamp'] = datetime.now().isoformat()

            # 기본 번역 유효성 검사
            validation = validate_default_translations()
            report['validation_errors'] = validation.get('errors', [])

            # 파일 기반 번역 분석
            merged_translations = self.merge_translations_from_files()
            report['total_locales'] = len(merged_translations)

            # 모든 키 수집
            all_keys = set()
            for translations in merged_translations.values():
                all_keys.update(translations.keys())

            report['total_keys'] = len(all_keys)

            # 로케일별 통계
            for locale, translations in merged_translations.items():
                report['locales'][locale] = {
                    'total_keys': len(translations),
                    'completion_rate': len(translations) / len(all_keys) * 100 if all_keys else 0
                }

            # 누락된 번역
            report['missing_translations'] = self.find_missing_translations()

            # 파일 통계
            for locale in merged_translations.keys():
                stats = self.file_manager.get_file_stats(locale)
                if stats:
                    report['file_stats'][locale] = {
                        'file_size': stats['file_size'],
                        'total_keys': stats['total_keys']
                    }

            logger.info("번역 상태 보고서 생성 완료")
            return report

        except Exception as e:
            logger.error(f"번역 상태 보고서 생성 실패: {e}")
            report['validation_errors'].append(f"보고서 생성 실패: {e}")
            return report

    def cleanup_unused_translations(self, used_keys: Set[str], dry_run: bool = True) -> Dict[str, List[str]]:
        """
        사용되지 않는 번역 정리

        Args:
            used_keys: 실제로 사용되는 키 집합
            dry_run: 실제 삭제하지 않고 시뮬레이션만 수행

        Returns:
            Dict[str, List[str]]: 정리된 키 목록
        """
        cleaned_keys = {}

        try:
            unused_translations = self.find_unused_translations(used_keys)

            if not dry_run:
                for locale, unused_keys in unused_translations.items():
                    for key in unused_keys:
                        success = self.file_manager.remove_translation_from_file(locale, key)
                        if success:
                            if locale not in cleaned_keys:
                                cleaned_keys[locale] = []
                            cleaned_keys[locale].append(key)

                logger.info(f"사용되지 않는 번역 정리 완료: {len(cleaned_keys)}개 로케일")
            else:
                cleaned_keys = unused_translations
                logger.info(f"사용되지 않는 번역 정리 시뮬레이션: {len(cleaned_keys)}개 로케일")

            return cleaned_keys

        except Exception as e:
            logger.error(f"사용되지 않는 번역 정리 실패: {e}")
            return {}