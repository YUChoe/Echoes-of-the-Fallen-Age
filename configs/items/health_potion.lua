-- 체력 물약 아이템 Lua 콜백 스크립트
-- on_use(ctx): 사용 시 번역 키와 치환 파라미터 반환, 아이템 소모
--
-- 서버는 문장을 만들지 않는다. 아이템 이름은 언어별 dict 그대로 params 에
-- 실리고 클라이언트가 현재 locale 을 고른다.

function on_use(ctx)
    return {
        message = {
            key = "obj.health_potion.use",
            params = {player = ctx.player.display_name, item = ctx.item.name}
        },
        consume = true,
    }
end
