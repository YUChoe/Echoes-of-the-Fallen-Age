-- Village Militia (자경단원) 대화 스크립트
-- NPC ID: 2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Hold there, " .. player_name .. ". I'm with the village militia. If you're heading beyond the village, keep your wits about you. It's not safe out there.",
                ko = "거기 서, " .. player_name .. ". 나는 마을 자경단이야. 마을 밖으로 나갈 생각이면, 정신 바짝 차려. 밖은 안전하지 않아."
            }
        },
        choices = {
            [1] = {en = "What threats are out there?", ko = "밖에 어떤 위협이 있나요?"},
            [2] = {en = "Tell me about the militia.", ko = "자경단에 대해 알려주세요."},
            [3] = {en = "I heard about a relocation order.", ko = "이주 명령에 대해 들었습니다."},
            [4] = {en = "I will be careful. Farewell.", ko = "조심하겠습니다. 안녕히."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "Creatures — goblins, mostly, but worse things too. They've been creeping closer to the village for months. Beyond the walls, the forests are thick and hostile. Beasts that used to flee from folk now attack on sight. We do what we can to keep the road clear, but we're stretched thin. If you venture out, don't go alone.",
                    ko = "괴물들이야 — 대부분 고블린이지만, 더 나쁜 것들도 있어. 몇 달째 마을 가까이 기어오고 있지. 성벽 밖으로 나가면 숲은 울창하고 적대적이야. 예전에는 사람을 보면 도망치던 짐승들이 이제는 보이는 대로 공격해. 길을 안전하게 유지하려고 할 수 있는 건 하고 있지만, 인원이 부족해. 밖에 나갈 거면, 혼자 가지 마."
                }
            },
            choices = {
                [2] = {en = "Tell me about the militia.", ko = "자경단에 대해 알려주세요."},
                [3] = {en = "What about the relocation order?", ko = "이주 명령은요?"},
                [4] = {en = "I will keep that in mind.", ko = "명심하겠습니다."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "We're just villagers who picked up spears, really. No proper training, no fancy armour. But someone has to stand between the creatures and the folk who live here. The Ash Knights have their fortress and their orders — we have our village and our stubbornness. That's about the sum of it.",
                    ko = "우리는 그냥 창을 든 마을 사람들이야, 솔직히. 제대로 된 훈련도 없고, 멋진 갑옷도 없어. 하지만 누군가는 괴물들과 여기 사는 사람들 사이에 서야 하잖아. 잿빛 기사단에는 요새와 명령이 있고 — 우리에게는 마을과 고집이 있지. 대충 그런 거야."
                }
            },
            choices = {
                [1] = {en = "What threats are out there?", ko = "밖에 어떤 위협이 있나요?"},
                [3] = {en = "What about the relocation order?", ko = "이주 명령은요?"},
                [4] = {en = "You have my respect. Farewell.", ko = "존경합니다. 안녕히."}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    en = "*spits on the ground* The relocation order. Aye, the castle wants us to clear out — says the village is too close to the walls and they need the space for defence. Defence! As if we haven't been defending this land with our own hands while they sat behind their gates. Move further out, they say. Into the wilds, where the creatures are thicker than the trees. Nobody here trusts the castle folk. Not any more.",
                    ko = "*땅에 침을 뱉으며* 이주 명령. 그래, 성에서 우리보고 비우라고 해 — 마을이 성벽에 너무 가까워서 방어를 위해 공간이 필요하다나. 방어! 성 안에서 문 닫고 앉아 있는 동안 우리가 맨손으로 이 땅을 지켜왔는데. 더 먼 곳으로 이주하라고, 괴물이 나무보다 많은 황야로. 여기 아무도 성 안 사람들을 믿지 않아. 더 이상은."
                }
            },
            choices = {
                [1] = {en = "What threats are beyond the village?", ko = "마을 밖에 어떤 위협이 있나요?"},
                [2] = {en = "Tell me about the militia.", ko = "자경단에 대해 알려주세요."},
                [4] = {en = "I understand your frustration.", ko = "분노를 이해합니다."}
            }
        }
    end

    return nil
end
