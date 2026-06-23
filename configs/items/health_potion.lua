-- 체력 물약 아이템 Lua 콜백 스크립트
-- on_use(ctx): 사용 시 다국어 메시지 반환, 아이템 소모

function on_use(ctx)
    local player = ctx.player
    local item = ctx.item

    return {
        message = {
            en = player.display_name .. " drinks the " .. item.name.en .. ". A warm feeling spreads through your body.",
            ko = player.display_name .. "이(가) " .. item.name.ko .. "을(를) 마셨습니다. 따뜻한 기운이 온몸에 퍼집니다.",
        },
        consume = true,
    }
end
