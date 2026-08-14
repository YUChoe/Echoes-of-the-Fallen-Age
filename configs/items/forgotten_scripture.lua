-- 잊혀진 경전 아이템 Lua 콜백 스크립트
-- on_read(ctx): 읽기 시 번역 키와 치환 파라미터 반환
--
-- 서버는 문장을 만들지 않는다. 문장은 클라이언트 번역 파일에 있다.

function on_read(ctx)
    return {
        message = {
            key = "obj.forgotten_scripture.read",
            params = {player = ctx.player.display_name}
        },
    }
end
