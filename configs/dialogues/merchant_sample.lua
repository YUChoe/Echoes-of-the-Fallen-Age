-- Town Merchant 교환 NPC 대화 스크립트
-- 선택지 번호 규칙:
--   1 = Buy, 2 = Sell
--   101~199 = 구매 아이템 (인덱스 = 번호 - 100)
--   201~299 = 판매 아이템 (인덱스 = 번호 - 200)

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    local npc_name = ctx.npc.name
    local locale = ctx.session.locale
    local npc_display = npc_name[locale] or npc_name.en or "Merchant"

    return {
        text = {
            {
                en = "Welcome, " .. player_name .. "! I'm " .. npc_display .. ". Browse my wares or sell me something.",
                ko = "어서 오세요, " .. player_name .. "님! 저는 " .. npc_display .. "입니다. 물건을 구경하시거나 팔 것이 있으면 말씀하세요."
            }
        },
        choices = {
            [1] = {en = "Buy", ko = "구매"},
            [2] = {en = "Sell", ko = "판매"}
        }
    }
end

function on_choice(choice_number, ctx)
    -- 메인 메뉴
    if choice_number == 1 then return show_buy_menu(ctx) end
    if choice_number == 2 then return show_sell_menu(ctx) end
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
        local price = 0
        if item.properties and item.properties.base_value then
            price = item.properties.base_value
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
    local buy_margin = 0.5
    if ctx.npc.properties and ctx.npc.properties.exchange_config then
        buy_margin = ctx.npc.properties.exchange_config.buy_margin or 0.5
    end
    local player_inv = ctx.player.inventory
    if not player_inv then return items end
    local i = 1
    while player_inv[i] do
        local item = player_inv[i]
        local base_value = 0
        if item.properties and item.properties.base_value then
            base_value = item.properties.base_value
        end
        local sell_price = math.floor(base_value * buy_margin)
        if sell_price > 0 then
            items[#items + 1] = {obj = item, price = sell_price}
        end
        i = i + 1
    end
    return items
end

function show_buy_menu(ctx)
    local locale = ctx.session.locale
    local buyable = get_buyable_items(ctx)
    local choices = {}

    for idx, entry in ipairs(buyable) do
        local item = entry.obj
        local price = entry.price
        local item_name = item.name[locale] or item.name.en or "Unknown"
        local mark = item.is_equipped and " [E]" or ""
        choices[100 + idx] = {
            en = item_name .. mark .. " (" .. price .. " silver, " .. string.format("%.1f", item.weight) .. "kg)",
            ko = item_name .. mark .. " (" .. price .. " 실버, " .. string.format("%.1f", item.weight) .. "kg)"
        }
    end

    choices[1] = {en = "Back", ko = "돌아가기"}

    local silver = ctx.player.silver or 0
    return {
        text = {{
            en = "Here's what I have. You have " .. silver .. " silver.",
            ko = "제가 가진 물건입니다. " .. silver .. " 실버를 가지고 계시네요."
        }},
        choices = choices
    }
end

function show_sell_menu(ctx)
    local locale = ctx.session.locale
    local sellable = get_sellable_items(ctx)
    local choices = {}

    for idx, entry in ipairs(sellable) do
        local item = entry.obj
        local price = entry.price
        local item_name = item.name[locale] or item.name.en or "Unknown"
        local mark = item.is_equipped and " [E]" or ""
        choices[200 + idx] = {
            en = item_name .. mark .. " (" .. price .. " silver)",
            ko = item_name .. mark .. " (" .. price .. " 실버)"
        }
    end

    choices[2] = {en = "Back", ko = "돌아가기"}

    local npc_silver = ctx.npc.silver or 0
    return {
        text = {{
            en = "What would you like to sell? I have " .. npc_silver .. " silver.",
            ko = "무엇을 파시겠어요? 제가 " .. npc_silver .. " 실버를 가지고 있습니다."
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
    local locale = ctx.session.locale
    local item_name = item.name[locale] or item.name.en or "Unknown"

    local result = exchange.buy_from_npc(ctx.player.id, ctx.npc.id, item.id, price)

    if result and result.success then
        return {
            text = {{
                en = "You bought " .. item_name .. " for " .. price .. " silver. A fine choice!",
                ko = item_name .. "을(를) " .. price .. " 실버에 구매했습니다. 좋은 선택이에요!"
            }},
            choices = {
                [1] = {en = "Buy more", ko = "더 구매"},
                [2] = {en = "Sell", ko = "판매"}
            }
        }
    end

    local error_code = result and result.error_code or ""
    if error_code == "insufficient_silver" then
        return {
            text = {{
                en = "You don't have enough silver for that.",
                ko = "실버가 부족합니다."
            }},
            choices = {[1] = {en = "Buy", ko = "구매"}, [2] = {en = "Sell", ko = "판매"}}
        }
    elseif error_code == "weight_exceeded" then
        return {
            text = {{
                en = "You can't carry any more. You're already weighed down.",
                ko = "더 이상 들 수 없습니다. 이미 짐이 너무 무겁습니다."
            }},
            choices = {[1] = {en = "Buy", ko = "구매"}, [2] = {en = "Sell", ko = "판매"}}
        }
    else
        return {
            text = {{
                en = "Sorry, that didn't work out. Try something else.",
                ko = "죄송합니다, 거래가 성사되지 않았습니다."
            }},
            choices = {[1] = {en = "Buy", ko = "구매"}, [2] = {en = "Sell", ko = "판매"}}
        }
    end
end

function handle_sell(item_idx, ctx)
    local sellable = get_sellable_items(ctx)
    local entry = sellable[item_idx]
    if not entry then return show_sell_menu(ctx) end

    local item = entry.obj
    local price = entry.price
    local locale = ctx.session.locale
    local item_name = item.name[locale] or item.name.en or "Unknown"

    local result = exchange.sell_to_npc(ctx.player.id, ctx.npc.id, item.id, price)

    if result and result.success then
        return {
            text = {{
                en = "You sold " .. item_name .. " for " .. price .. " silver. Pleasure doing business!",
                ko = item_name .. "을(를) " .. price .. " 실버에 판매했습니다. 좋은 거래였어요!"
            }},
            choices = {
                [1] = {en = "Buy", ko = "구매"},
                [2] = {en = "Sell more", ko = "더 판매"}
            }
        }
    end

    local error_code = result and result.error_code or ""
    if error_code == "npc_insufficient_silver" then
        return {
            text = {{
                en = "I'm afraid I don't have enough silver to buy that from you.",
                ko = "죄송합니다, 그것을 살 만큼 실버가 충분하지 않습니다."
            }},
            choices = {[1] = {en = "Buy", ko = "구매"}, [2] = {en = "Sell", ko = "판매"}}
        }
    else
        return {
            text = {{
                en = "Sorry, that didn't work out. Try something else.",
                ko = "죄송합니다, 거래가 성사되지 않았습니다."
            }},
            choices = {[1] = {en = "Buy", ko = "구매"}, [2] = {en = "Sell", ko = "판매"}}
        }
    end
end
