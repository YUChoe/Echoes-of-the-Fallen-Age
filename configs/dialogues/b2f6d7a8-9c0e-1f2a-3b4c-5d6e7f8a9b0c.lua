-- Crypt Guard Monk (교회 지하 입구 경비 수도사) 대화 스크립트
-- NPC ID: b2f6d7a8-9c0e-1f2a-3b4c-5d6e7f8a9b0c

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Halt, " .. player_name .. ". This passage is sealed by order of the church. No one goes below. Turn back.",
                ko = "멈춰라, " .. player_name .. ". 이 통로는 교회의 명으로 봉인되었다. 아무도 아래로 내려갈 수 없다. 돌아가라."
            }
        },
        choices = {
            [1] = {en = "What lies beneath?", ko = "아래에 무엇이 있나요?"},
            [2] = {en = "Is it true the dead have risen?", ko = "죽은 자가 살아났다는 게 사실인가요?"},
            [3] = {en = "Understood. I will leave.", ko = "알겠습니다. 물러가겠습니다."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "The necropolis. Ancient burial chambers that have been here longer than anyone can remember. It is no place for the living. Strange sounds echo from below — scraping, shuffling. The iron door stays shut, and I intend to keep it that way.",
                    ko = "네크로폴리스다. 누구도 기억하지 못할 만큼 오래된 고대 매장실이지. 산 자가 갈 곳이 아니다. 아래에서 이상한 소리가 울려 퍼진다 — 긁는 소리, 끌리는 소리. 철문은 닫혀 있고, 나는 그 상태를 유지할 생각이다."
                }
            },
            choices = {
                [2] = {en = "Have the dead truly risen?", ko = "정말 죽은 자가 살아났나요?"},
                [3] = {en = "I will not press further.", ko = "더 이상 묻지 않겠습니다."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "I will not speak of rumours. What I will say is this: something moves down there that should not. Whether it is the dead walking or rats the size of dogs, it matters little. The result is the same — you go down, you do not come back. Now leave me to my watch.",
                    ko = "소문에 대해서는 말하지 않겠다. 내가 말할 수 있는 건 이것뿐이다: 저 아래에서 있어서는 안 될 무언가가 움직인다. 죽은 자가 걸어 다니는 것이든 개만 한 쥐든, 별 차이 없다. 결과는 같다 — 내려가면, 돌아오지 못한다. 이제 경비를 서게 놔둬라."
                }
            },
            choices = {
                [1] = {en = "What is the necropolis?", ko = "네크로폴리스가 뭔가요?"},
                [3] = {en = "Very well. Stay vigilant.", ko = "알겠습니다. 경계를 늦추지 마세요."}
            }
        }
    end

    return nil
end
