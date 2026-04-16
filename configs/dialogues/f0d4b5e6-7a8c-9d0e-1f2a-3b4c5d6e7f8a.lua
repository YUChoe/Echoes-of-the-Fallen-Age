-- Wandering Bard (떠돌이 음유시인) 대화 스크립트
-- NPC ID: f0d4b5e6-7a8c-9d0e-1f2a-3b4c5d6e7f8a

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Ah, a fresh face. " .. player_name .. ", is it? Pull up a chair. I have stories, if you have the stomach for them. Not the cheerful sort, mind you.",
                ko = "아, 새로운 얼굴이군. " .. player_name .. "이라고? 의자를 끌어당겨. 이야기가 있다네, 들을 배짱이 있다면. 유쾌한 종류는 아니지만."
            }
        },
        choices = {
            [1] = {en = "Tell me about the Golden Age.", ko = "황금의 시대에 대해 들려주세요."},
            [2] = {en = "What happened to the empire?", ko = "제국에 무슨 일이 있었나요?"},
            [3] = {en = "Perhaps another time.", ko = "다음에 듣겠습니다."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "The Golden Age... when the empire of Karnas stretched across the continent. Gods and men walked closer then, or so the old songs say. Machines of wondrous craft, prosperity beyond measure. But balance is a fickle thing. It all came crashing down — gods, men, and everything in between.",
                    ko = "황금의 시대라... 카르나스 제국이 대륙을 가로질러 뻗어 있던 때지. 신과 인간이 더 가까이 걸었다고, 옛 노래들은 그렇게 전하네. 경이로운 기계들, 헤아릴 수 없는 번영. 하지만 균형이란 변덕스러운 것이야. 모든 것이 무너져 내렸지 — 신도, 인간도, 그 사이의 모든 것도."
                }
            },
            choices = {
                [2] = {en = "And then what happened?", ko = "그 다음엔 어떻게 됐나요?"},
                [3] = {en = "Thank you for the tale.", ko = "이야기 감사합니다."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "The empire burned. Then, about a hundred years ago, someone they call the Great Sorcerer appeared — though no one has ever laid eyes on him. After that, the forests grew thick and hostile, and creatures from old tales began crawling out. Goblins, orcs, beasts that attack on sight. The world changed, and not for the better. Now we huddle here in Greyhaven, the last refuge of the living.",
                    ko = "제국은 불탔지. 그리고 약 백여 년 전, 대마법사라 불리는 자가 나타났다네 — 물론 아무도 직접 본 적은 없지만. 그 뒤로 숲은 울창하고 적대적으로 변했고, 옛 이야기 속 괴물들이 기어 나오기 시작했어. 고블린, 오크, 보이는 대로 공격하는 짐승들. 세상이 변했고, 좋은 쪽은 아니야. 이제 우리는 산 자들의 마지막 피난처인 잿빛 항구에 모여 있다네."
                }
            },
            choices = {
                [1] = {en = "Tell me about the Golden Age.", ko = "황금의 시대에 대해 들려주세요."},
                [3] = {en = "A grim tale indeed.", ko = "참으로 암울한 이야기군요."}
            }
        }
    end

    return nil
end
