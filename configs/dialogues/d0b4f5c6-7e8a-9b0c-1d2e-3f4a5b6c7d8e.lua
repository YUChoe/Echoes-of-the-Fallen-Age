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
                en = "Psst... " .. player_name .. ". Over here. You look like someone who knows the value of discretion. I have goods that are hard to come by — for the right price, naturally.",
                ko = "쉿... " .. player_name .. ". 이쪽이야. 입이 무거운 사람처럼 보이는군. 구하기 힘든 물건들이 있어 — 물론, 적절한 대가를 치른다면."
            }
        },
        choices = {
            [1] = {en = "Show me what you have.", ko = "뭐가 있는지 보여줘."},
            [2] = {en = "I have something to sell.", ko = "팔 물건이 있어."},
            [3] = {en = "Not interested.", ko = "관심 없어."}
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
            en = "Take a look... but keep your voice down. You have " .. silver .. " silver.",
            ko = "한번 봐... 근데 목소리 낮춰. " .. silver .. " 실버를 가지고 있군."
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
            en = "Got something for me? I have " .. npc_silver .. " silver to spend.",
            ko = "나한테 줄 게 있어? " .. npc_silver .. " 실버까지 쓸 수 있어."
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
                en = "Pleasure doing business. " .. item_name .. " for " .. price .. " silver. Keep it hidden, eh?",
                ko = "좋은 거래야. " .. item_name .. ", " .. price .. " 실버. 숨겨서 가져가, 알겠지?"
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
                en = "You are short on silver, friend. Come back when your pockets are heavier.",
                ko = "은이 부족하군, 친구. 주머니가 두둑해지면 다시 와."
            }},
            choices = {[1] = {en = "Buy", ko = "구매"}, [2] = {en = "Sell", ko = "판매"}}
        }
    elseif error_code == "weight_exceeded" then
        return {
            text = {{
                en = "You can barely stand as it is. Lighten your load first.",
                ko = "지금도 겨우 서 있잖아. 짐부터 줄여."
            }},
            choices = {[1] = {en = "Buy", ko = "구매"}, [2] = {en = "Sell", ko = "판매"}}
        }
    else
        return {
            text = {{
                en = "Something went wrong. Let us try again.",
                ko = "뭔가 잘못됐어. 다시 해보자."
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
                en = "I will take that " .. item_name .. " off your hands. " .. price .. " silver, as agreed.",
                ko = item_name .. "을(를) 받지. " .. price .. " 실버, 약속대로."
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
                en = "I am a bit light on silver myself right now. Try something cheaper.",
                ko = "나도 지금 은이 좀 부족해. 더 싼 걸로 해봐."
            }},
            choices = {[1] = {en = "Buy", ko = "구매"}, [2] = {en = "Sell", ko = "판매"}}
        }
    else
        return {
            text = {{
                en = "That did not work out. Let us try something else.",
                ko = "안 됐어. 다른 걸 해보자."
            }},
            choices = {[1] = {en = "Buy", ko = "구매"}, [2] = {en = "Sell", ko = "판매"}}
        }
    end
end
