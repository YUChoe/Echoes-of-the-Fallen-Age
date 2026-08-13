-- Smuggler (밀수업자) 거래 대화 스크립트
-- NPC ID: d0b4f5c6-7e8a-9b0c-1d2e-3f4a5b6c7d8e
-- 선택지 번호 규칙:
--   1~99 = 메뉴 탐색
--   101~199 = 구매 아이템 (인덱스 = 번호 - 100)
--   201~299 = 판매 아이템 (인덱스 = 번호 - 200)

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.smuggler.intro",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.smuggler.choice.show_goods", params = {}},
            [2] = {key = "npc.smuggler.choice.have_to_sell", params = {}},
            [3] = {key = "npc.smuggler.choice.not_interested", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    -- 메인 메뉴
    if choice_number == 1 then return show_buy_menu(ctx) end
    if choice_number == 2 then return show_sell_menu(ctx) end
    if choice_number == 3 then return nil end
    -- 구매 아이템 선택 (101~199)
    if choice_number >= 101 and choice_number <= 199 then
        return handle_buy(choice_number - 100, ctx)
    end
    -- 판매 아이템 선택 (201~299)
    if choice_number >= 201 and choice_number <= 299 then
        return handle_sell(choice_number - 200, ctx)
    end
    return nil
end

function get_buyable_items(ctx)
    local items = {}
    local npc_inv = ctx.npc.inventory
    if not npc_inv then return items end
    local i = 1
    while npc_inv[i] do
        local item = npc_inv[i]
        -- item_prices DB 테이블에서 buy_price 조회 (인벤토리 필드 또는 API 호출)
        local price = item.buy_price or 0
        if price <= 0 then
            price = exchange.get_buy_price(item.id) or 0
        end
        if price > 0 then
            items[#items + 1] = {obj = item, price = price}
        end
        i = i + 1
    end
    return items
end

function get_sellable_items(ctx)
    local items = {}
    local player_inv = ctx.player.inventory
    if not player_inv then return items end
    local i = 1
    while player_inv[i] do
        local item = player_inv[i]
        -- item_prices DB 테이블에서 sell_price 조회 (인벤토리 필드 또는 API 호출)
        local sell_price = item.sell_price or 0
        if sell_price <= 0 then
            sell_price = exchange.get_sell_price(item.id) or 0
        end
        if sell_price > 0 then
            items[#items + 1] = {obj = item, price = sell_price}
        end
        i = i + 1
    end
    return items
end

function show_buy_menu(ctx)
    local buyable = get_buyable_items(ctx)
    local choices = {}

    for idx, entry in ipairs(buyable) do
        local item = entry.obj
        local price = entry.price
        local mark = item.is_equipped and " [E]" or ""
        choices[100 + idx] = {
            key = "npc.smuggler.item_buy",
            params = {item = item.name, mark = mark, price = price, weight = string.format("%.1f", item.weight)}
        }
    end

    choices[1] = {key = "npc.smuggler.choice.back", params = {}}

    local silver = ctx.player.silver or 0
    return {
        text = {{
            key = "npc.smuggler.buy_menu",
            params = {}
        }},
        choices = choices
    }
end

function show_sell_menu(ctx)
    local sellable = get_sellable_items(ctx)
    local choices = {}

    for idx, entry in ipairs(sellable) do
        local item = entry.obj
        local price = entry.price
        local mark = item.is_equipped and " [E]" or ""
        choices[200 + idx] = {
            key = "npc.smuggler.item_sell",
            params = {item = item.name, mark = mark, price = price}
        }
    end

    choices[2] = {key = "npc.smuggler.choice.back", params = {}}

    local npc_silver = ctx.npc.silver or 0
    return {
        text = {{
            key = "npc.smuggler.sell_menu",
            params = {}
        }},
        choices = choices
    }
end

function handle_buy(item_idx, ctx)
    local buyable = get_buyable_items(ctx)
    local entry = buyable[item_idx]
    if not entry then return show_buy_menu(ctx) end

    local item = entry.obj
    local price = entry.price

    local result = exchange.buy_from_npc(ctx.player.id, ctx.npc.id, item.id, price)

    if result and result.success then
        return {
            text = {{
                key = "npc.smuggler.buy_done",
                params = {item = item.name, price = price}
            }},
            choices = {
                [1] = {key = "npc.smuggler.choice.buy_more", params = {}},
                [2] = {key = "npc.smuggler.choice.sell", params = {}}
            }
        }
    end

    local error_code = result and result.error_code or ""
    if error_code == "insufficient_silver" then
        return {
            text = {{
                key = "npc.smuggler.no_silver",
                params = {}
            }},
            choices = {[1] = {key = "npc.smuggler.choice.buy", params = {}}, [2] = {key = "npc.smuggler.choice.sell", params = {}}}
        }
    elseif error_code == "weight_exceeded" then
        return {
            text = {{
                key = "npc.smuggler.too_heavy",
                params = {}
            }},
            choices = {[1] = {key = "npc.smuggler.choice.buy", params = {}}, [2] = {key = "npc.smuggler.choice.sell", params = {}}}
        }
    else
        return {
            text = {{
                key = "npc.smuggler.buy_failed",
                params = {}
            }},
            choices = {[1] = {key = "npc.smuggler.choice.buy", params = {}}, [2] = {key = "npc.smuggler.choice.sell", params = {}}}
        }
    end
end

function handle_sell(item_idx, ctx)
    local sellable = get_sellable_items(ctx)
    local entry = sellable[item_idx]
    if not entry then return show_sell_menu(ctx) end

    local item = entry.obj
    local price = entry.price

    local result = exchange.sell_to_npc(ctx.player.id, ctx.npc.id, item.id, price)

    if result and result.success then
        return {
            text = {{
                key = "npc.smuggler.sell_done",
                params = {item = item.name, price = price}
            }},
            choices = {
                [1] = {key = "npc.smuggler.choice.buy", params = {}},
                [2] = {key = "npc.smuggler.choice.sell_more", params = {}}
            }
        }
    end

    local error_code = result and result.error_code or ""
    if error_code == "npc_insufficient_silver" then
        return {
            text = {{
                key = "npc.smuggler.npc_no_silver",
                params = {}
            }},
            choices = {[1] = {key = "npc.smuggler.choice.buy", params = {}}, [2] = {key = "npc.smuggler.choice.sell", params = {}}}
        }
    elseif error_code == "item_not_owned" then
        return {
            text = {{
                key = "npc.smuggler.item_gone",
                params = {}
            }},
            choices = {[1] = {key = "npc.smuggler.choice.buy", params = {}}, [2] = {key = "npc.smuggler.choice.sell", params = {}}}
        }
    else
        return {
            text = {{
                key = "npc.smuggler.sell_failed",
                params = {}
            }},
            choices = {[1] = {key = "npc.smuggler.choice.buy", params = {}}, [2] = {key = "npc.smuggler.choice.sell", params = {}}}
        }
    end
end
