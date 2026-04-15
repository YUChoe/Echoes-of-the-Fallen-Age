-- Knight Recruiter (기사단 모병관) 대화 스크립트
-- NPC ID: d8b2f3c4-5e6a-7b8c-9d0e-1f2a3b4c5d6e

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "You there, " .. player_name .. "! You look like someone who can handle themselves. Ever thought about joining the Ash Knights?",
                ko = "이봐, " .. player_name .. "! 제법 자신을 지킬 줄 아는 사람처럼 보이는군. 잿빛 기사단에 입단할 생각은 없나?"
            }
        },
        choices = {
            [1] = {en = "What does joining the Ash Knights entail?", ko = "잿빛 기사단에 입단하면 어떻게 되나요?"},
            [2] = {en = "What is the situation beyond the walls?", ko = "성벽 밖 상황은 어떤가요?"},
            [3] = {en = "Not interested.", ko = "관심 없습니다."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "We stand for justice in a world gone mad. Mind you, justice here means keeping order — and order sometimes demands a firm hand. But without us, these people would have nothing. Think on it.",
                    ko = "우리는 미쳐버린 세상에서 정의를 지킨다. 물론, 여기서 정의란 질서를 유지하는 것이고 — 질서는 때로 강경한 손길을 요구하지. 하지만 우리가 없으면 이 사람들에겐 아무것도 남지 않아. 생각해 보게."
                }
            },
            choices = {
                [2] = {en = "What about beyond the walls?", ko = "성벽 밖은 어떤가요?"},
                [3] = {en = "I will think about it.", ko = "생각해 보겠습니다."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "Beyond the walls? Creatures roam freely — goblins, beasts, worse things. The folk out there have been ordered to relocate, but most of them resent us for it. Inside, we have our own troubles with goblins nesting in the brush. Nowhere is truly safe.",
                    ko = "성벽 밖이라고? 괴물들이 자유롭게 돌아다닌다 — 고블린, 짐승, 더 나쁜 것들도. 밖의 사람들에게 이주 명령을 내렸지만 대부분 우리를 원망하고 있지. 안에서도 수풀에 고블린이 둥지를 틀어서 문제야. 어디도 진정으로 안전하지 않다."
                }
            },
            choices = {
                [1] = {en = "Tell me about joining.", ko = "입단에 대해 알려주세요."},
                [3] = {en = "I see. Farewell.", ko = "알겠습니다. 안녕히."}
            }
        }
    end

    return nil
end
