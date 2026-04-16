-- Knight Lieutenant (기사단 부관) 대화 스크립트
-- NPC ID: c7a1e2b3-4d5f-6a7b-8c9d-0e1f2a3b4c5d

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "At ease, " .. player_name .. ". I am the lieutenant of the Ash Knights stationed here. What brings you to our post?",
                ko = "편히 서라, " .. player_name .. ". 나는 이곳에 주둔 중인 잿빛 기사단의 부관이다. 무슨 용건인가?"
            }
        },
        choices = {
            [1] = {en = "Tell me about the Ash Knights.", ko = "잿빛 기사단에 대해 알려주세요."},
            [2] = {en = "What is the goblin threat?", ko = "고블린 위협이란 무엇인가요?"},
            [3] = {en = "Farewell.", ko = "안녕히 계세요."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "We are the last knightly order standing after the empire fell. We uphold justice — though some might say our methods are harsh. Without discipline, there would be nothing left but chaos.",
                    ko = "우리는 제국이 무너진 뒤 남은 유일한 기사단이다. 정의를 수호하지만 — 어떤 이들은 우리의 방식이 가혹하다고 하지. 규율이 없으면 혼란만 남을 뿐이다."
                }
            },
            choices = {
                [2] = {en = "What about the goblins?", ko = "고블린은 어떤가요?"},
                [3] = {en = "Farewell.", ko = "안녕히 계세요."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "Goblins have nested in the brush within our own walls. Small, wretched creatures — not terribly dangerous alone, but they breed like vermin. We are mustering folk to clear them out before they become a proper menace.",
                    ko = "고블린들이 성벽 안 수풀에 둥지를 틀었다. 작고 비참한 놈들이지 — 혼자서는 크게 위험하지 않지만 해충처럼 번식한다. 본격적인 위협이 되기 전에 소탕하려고 사람들을 모으고 있다."
                }
            },
            choices = {
                [1] = {en = "Tell me about the Ash Knights.", ko = "잿빛 기사단에 대해 알려주세요."},
                [3] = {en = "Farewell.", ko = "안녕히 계세요."}
            }
        }
    end

    return nil
end
