-- Fisherman (어부) 대화 스크립트
-- NPC ID: c9a3e4b5-6d7f-8a9b-0c1d-2e3f4a5b6c7d

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Aye, " .. player_name .. ". Come to watch the sea, have you? Not much else to do round here. The fish still bite, at least — that is more than most can say about their livelihoods.",
                ko = "그래, " .. player_name .. ". 바다 구경하러 왔나? 여기서 할 수 있는 게 별로 없지. 물고기는 아직 물긴 해 — 대부분의 사람들 생계보다는 나은 편이야."
            }
        },
        choices = {
            [1] = {en = "Tell me about the harbour.", ko = "항구에 대해 알려주세요."},
            [2] = {en = "What is to the north and south?", ko = "북쪽과 남쪽에는 뭐가 있나요?"},
            [3] = {en = "Good fishing to you.", ko = "좋은 낚시 되세요."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "Harbour is a generous word for it. There is a narrow gap in the northern cliffs where you can squeeze a small boat through to a tiny landing. That is our harbour. It is enough for fishing, but you will not be sailing any galleons out of here. The cliffs keep us safe from the sea, at least.",
                    ko = "항구라고 하기엔 좀 거창하지. 북쪽 절벽에 좁은 틈이 있어서 작은 배를 밀어 넣으면 조그만 선착장이 나와. 그게 우리 항구야. 낚시하기엔 충분하지만, 여기서 대형 범선을 띄울 생각은 마. 절벽이 바다로부터는 지켜주니까, 그건 다행이지."
                }
            },
            choices = {
                [2] = {en = "And to the south?", ko = "남쪽은요?"},
                [3] = {en = "Thank you for the information.", ko = "정보 감사합니다."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "North is all cliffs — sheer rock face dropping straight into the sea. Nobody gets in or out that way, which suits us fine. To the south, the walls are half-crumbled and there is a low cliff below. A stream runs out from the castle grounds and flows to the sea through there. Used to be a proper jetty once, but it is nothing but ruins now. I would not wander too far south if I were you.",
                    ko = "북쪽은 전부 절벽이야 — 깎아지른 바위가 바다로 곧장 떨어지지. 그쪽으로는 아무도 드나들 수 없어, 우리한텐 오히려 좋지. 남쪽은 성벽이 반쯤 무너져 있고 아래로 낮은 절벽이 있어. 성 안에서 나온 샘물이 그쪽으로 흘러 바다로 들어가지. 한때 제대로 된 잔교가 있었는데, 이제는 폐허뿐이야. 내가 너라면 남쪽으로 너무 멀리 가지 않겠어."
                }
            },
            choices = {
                [1] = {en = "Tell me about the harbour.", ko = "항구에 대해 알려주세요."},
                [3] = {en = "I will keep that in mind.", ko = "명심하겠습니다."}
            }
        }
    end

    return nil
end
