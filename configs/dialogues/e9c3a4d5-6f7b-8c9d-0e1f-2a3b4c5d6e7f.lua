-- Drunken Refugee (술에 취한 난민) 대화 스크립트
-- NPC ID: e9c3a4d5-6f7b-8c9d-0e1f-2a3b4c5d6e7f

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "*hic* ...Who're you? " .. player_name .. "? Doesn't matter... nothing matters any more. Sit down if you want, I don't care...",
                ko = "*딸꾹* ...누구야? " .. player_name .. "? 상관없어... 이제 아무것도 상관없다고. 앉고 싶으면 앉아, 난 신경 안 써..."
            }
        },
        choices = {
            [1] = {en = "What happened to you?", ko = "무슨 일이 있었나요?"},
            [2] = {en = "I heard rumours about a great sorcerer.", ko = "대마법사에 대한 소문을 들었습니다."},
            [3] = {en = "Take care of yourself.", ko = "몸 조심하세요."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "The expedition... the third one. I went with them, you know. We were going to find this so-called sorcerer and put an end to it all. *hic* ...We found nothing. Just a blinding light — bright, enormous — and then everyone was screaming. I barely made it back. My family... I don't even know if they're still alive.",
                    ko = "원정이야... 세 번째. 나도 같이 갔었어. 소위 마법사란 놈을 찾아서 모든 걸 끝내려고 했지. *딸꾹* ...아무것도 못 찾았어. 그냥 눈부신 빛 — 밝고, 거대한 — 그리고 모두가 비명을 질렀어. 겨우 돌아왔다. 가족은... 살아 있는지조차 모르겠어."
                }
            },
            choices = {
                [2] = {en = "Tell me about this sorcerer.", ko = "그 마법사에 대해 말해주세요."},
                [3] = {en = "I am sorry. Take care.", ko = "유감입니다. 몸 조심하세요."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "Sorcerer? *laughs bitterly* Nobody's ever seen him. Nobody can even explain what happened properly. They say he appeared about a hundred years ago and everything went wrong after that — forests grew wild, creatures came out of nowhere. But sorcery? In this world? Nobody believes in such nonsense. It was just... a light. A terrible, blinding light. That's all anyone remembers.",
                    ko = "마법사? *씁쓸하게 웃으며* 아무도 본 적 없어. 무슨 일이 있었는지 제대로 설명하는 사람도 없고. 백여 년 전에 나타났다고 하고 그 뒤로 모든 게 엉망이 됐다지 — 숲은 미쳐 자라고, 괴물들이 어디선가 나타나고. 하지만 마법이라고? 이 세상에서? 아무도 그런 헛소리를 믿지 않아. 그냥... 빛이었어. 끔찍하고 눈부신 빛. 그게 다야."
                }
            },
            choices = {
                [1] = {en = "What happened on the expedition?", ko = "원정에서 무슨 일이 있었나요?"},
                [3] = {en = "I hope you find your family.", ko = "가족을 찾길 바랍니다."}
            }
        }
    end

    return nil
end
