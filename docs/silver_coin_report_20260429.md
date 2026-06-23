# Silver Coin 현황 보고서

조회일: 2026-04-29

## 요약

| 항목 | 값 |
|------|-----|
| 게임 전체 Silver Coin 총량 | 800개 |
| NPC 보유 | 800개 |
| 플레이어 보유 | 0개 |

## NPC별 보유 현황

| NPC | quantity | max_stack | 비고 |
|-----|----------|-----------|------|
| Town Merchant | 500 | 9999 | 거래 NPC |
| Smuggler | 300 | 9999 | 거래 NPC |

## 데이터 구조

Silver Coin은 `game_objects` 테이블에 저장되며, 수량은 `properties.quantity` 필드로 관리된다.

```json
{
  "template_id": "silver_coin",
  "is_template": false,
  "category": "currency",
  "base_value": 1,
  "quantity": 500
}
```

- `max_stack`: 9999 (한 스택 최대 수량)
- `CurrencyManager`가 `properties.quantity`를 기준으로 잔액 조회/지급/차감 처리
- quantity가 0이 되면 해당 game_object 삭제
- max_stack 초과 시 추가 스택 생성
