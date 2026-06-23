# Silver Coin 현황 보고서

조회일: 2026-04-29 (최종 업데이트)

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

## 가격 시스템 (2026-04-29 추가)

아이템 가격은 `item_prices` DB 테이블에서 `template_id` 기반으로 중앙 관리된다.
`game_objects.properties`에 가격 필드를 저장하지 않고, `PriceResolver`가 DB를 조회하여 가격을 산출한다.

```sql
CREATE TABLE item_prices (
    template_id TEXT PRIMARY KEY,
    buy_price INTEGER DEFAULT 0,   -- NPC 구매가 (플레이어가 NPC에게서 살 때)
    sell_price INTEGER DEFAULT 0   -- NPC 판매가 (플레이어가 NPC에게 팔 때)
);
```

- `PriceResolver.get_buy_price(template_id, price_modifier)` — DB 조회 + 동적 가격 조정
- `PriceResolver.get_sell_price(template_id, price_modifier)` — DB 조회 + 동적 가격 조정
- `item_prices`에 레코드가 없는 아이템은 거래 불가 (가격 0 반환)
- Lua 스크립트에서 `exchange.get_buy_price(item_id)` / `exchange.get_sell_price(item_id)`로 조회 가능
- 인벤토리 조회 시 각 아이템에 `buy_price`/`sell_price` 필드 자동 포함

### 초기 가격 데이터 (27개 거래 가능 아이템)

| template_id | buy_price | sell_price |
|-------------|-----------|------------|
| health_potion | 20 | 7 |
| stamina_potion | 16 | 5 |
| bread | 4 | 1 |
| club | 15 | 5 |
| guard_sword | 50 | 12 |
| guard_heavy_sword | 100 | 25 |
| guard_halberd | 80 | 20 |
| guard_spear | 60 | 15 |
| rusty_dagger | 8 | 2 |
| guide_walking_stick | 10 | 3 |
| rope | 10 | 3 |
| torch | 7 | 2 |
| backpack | 25 | 8 |
| saddle | 50 | 15 |
| leather_bridle | 30 | 10 |
| horse_brush | 12 | 4 |
| horseshoe | 8 | 3 |
| oats | 6 | 2 |
| hay_bale | 5 | 2 |
| oak_branch | 3 | 1 |
| forest_mushroom | 2 | 1 |
| wild_berries | 1 | 0 |
| smooth_stone | 1 | 0 |
| wildflower_crown | 3 | 1 |
| empty_bottle | 2 | 1 |
| merchant_journal | 20 | 8 |
| forgotten_scripture | 15 | 5 |
