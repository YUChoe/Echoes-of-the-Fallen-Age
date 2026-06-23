-- 잊혀진 경전 아이템 Lua 콜백 스크립트
-- on_read(ctx): 읽기 시 다국어 메시지 반환

function on_read(ctx)
    local player = ctx.player

    return {
        message = {
            en = "As " .. player.display_name .. " reads the ancient scripture, a faint golden light emanates from the text...",
            ko = player.display_name .. "이(가) 고대 경전을 읽자, 희미한 금빛이 글자에서 흘러나옵니다...",
        },
    }
end
