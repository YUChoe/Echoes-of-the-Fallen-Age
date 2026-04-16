-- Former Merchant (전직 상인) 대화 스크립트
-- NPC ID: f6d0b1e2-3a4c-5d6e-7f8a-9b0c1d2e3f4a

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Hm? Oh, " .. player_name .. ". Forgive me, I was lost in thought. I used to be a merchant, you know. Had a fine cart, good stock. That feels like another lifetime now.",
                ko = "흠? 아, " .. player_name .. ". 미안, 생각에 빠져 있었어. 나도 한때 상인이었다네. 좋은 수레에, 괜찮은 물건들. 이제는 전생 같은 이야기지."
            }
        },
        choices = {
            [1] = {en = "What happened to your trade?", ko = "장사는 어떻게 된 건가요?"},
            [2] = {en = "How did merchants become bandits?", ko = "상인들이 어떻게 도적이 됐나요?"},
            [3] = {en = "Times are hard for everyone.", ko = "모두에게 힘든 시절이군요."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "Plundered. Three times on the same road. First it was goblins — they took everything and smashed what they could not carry. Then bandits, who were once merchants themselves. The third time, I did not even bother rebuilding the cart. What is the point? The roads belong to the creatures now.",
                    ko = "약탈당했지. 같은 길에서 세 번이나. 처음엔 고블린이었어 — 모든 걸 가져가고 못 가져가는 건 부쉈지. 그다음엔 도적들, 한때 상인이었던 자들이야. 세 번째엔 수레를 다시 만들 생각도 안 했어. 무슨 소용이야? 이제 길은 괴물들 차지야."
                }
            },
            choices = {
                [2] = {en = "Merchants turned bandits?", ko = "상인이 도적으로?"},
                [3] = {en = "A bitter tale.", ko = "씁쓸한 이야기군요."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "When you lose everything — your goods, your livelihood, your hope — what is left? Some folk turned to stealing just to survive. I do not blame them, not really. The raids never stopped, the knights could not protect the roads, and honest trade became impossible. Society crumbled, one broken cart at a time. I was lucky enough to make it here. Others were not.",
                    ko = "모든 걸 잃으면 — 물건도, 생계도, 희망도 — 뭐가 남겠나? 어떤 이들은 살아남으려고 도둑질을 시작했어. 탓하지 않아, 진심으로. 습격은 멈추지 않았고, 기사들은 길을 지키지 못했고, 정직한 거래는 불가능해졌지. 사회가 무너졌어, 부서진 수레 하나씩. 나는 운 좋게 여기까지 왔지. 다른 이들은 그러지 못했고."
                }
            },
            choices = {
                [1] = {en = "Tell me about the raids.", ko = "습격에 대해 알려주세요."},
                [3] = {en = "I hope things improve.", ko = "상황이 나아지길 바랍니다."}
            }
        }
    end

    return nil
end
