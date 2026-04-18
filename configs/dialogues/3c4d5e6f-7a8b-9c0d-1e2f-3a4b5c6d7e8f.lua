-- Junkyard Drifter (쓰레기장 떠돌이) 대화 스크립트
-- NPC ID: 3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "*looks up from a pile of rubbish* Eh? " .. player_name .. "? Don't mind me, just picking through what folk have thrown away. You'd be surprised what turns up in a heap of broken furniture and old scraps.",
                ko = "*쓰레기 더미에서 고개를 들며* 응? " .. player_name .. "? 신경 쓰지 마, 사람들이 버린 것들 좀 뒤지고 있을 뿐이야. 부서진 가구랑 낡은 잡동사니 더미에서 뭐가 나오는지 알면 놀랄 걸."
            }
        },
        choices = {
            [1] = {en = "Find anything useful?", ko = "쓸만한 거 찾았나요?"},
            [2] = {en = "I noticed animals around here.", ko = "주변에 동물들이 보이던데요."},
            [3] = {en = "Know anything about the area north of here?", ko = "여기 북쪽에 대해 아는 게 있나요?"},
            [4] = {en = "Good luck with your search.", ko = "잘 찾길 바랍니다."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "Bits and bobs. A bent nail here, a scrap of cloth there. Folk tossed out all sorts when they moved into the fortress — old furniture, broken roof tiles, things they couldn't carry. It hasn't been long enough for the rot to set in proper, so there's still decent pickings if you know where to look. Not glamorous work, but it keeps me going.",
                    ko = "이것저것. 여기서 구부러진 못, 저기서 천 조각. 사람들이 요새로 들어오면서 온갖 걸 버렸거든 — 낡은 가구, 깨진 지붕 기와, 들고 갈 수 없는 것들. 아직 제대로 썩을 만큼 시간이 지나지 않아서, 어디를 봐야 하는지 알면 괜찮은 것들이 있어. 멋진 일은 아니지만, 이걸로 버티고 있지."
                }
            },
            choices = {
                [2] = {en = "What about the animals?", ko = "동물들은요?"},
                [3] = {en = "Anything north of here?", ko = "여기 북쪽에 뭐가 있나요?"},
                [4] = {en = "I see. Take care.", ko = "그렇군요. 몸 조심하세요."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "Aye, they come for the scraps. Foxes, rats, the odd stray dog. Folk throw their food waste here too, so the animals have learnt there's easy pickings. They're not dangerous — just hungry, like the rest of us. I don't bother them and they don't bother me. We've got an understanding, you might say.",
                    ko = "그래, 먹을 것 때문에 오는 거야. 여우, 쥐, 가끔 떠돌이 개도. 사람들이 음식물 쓰레기도 여기 버리니까, 동물들이 쉽게 먹을 게 있다는 걸 알게 된 거지. 위험하진 않아 — 그냥 배고픈 거야, 우리 나머지와 마찬가지로. 나는 그놈들을 건드리지 않고 그놈들도 나를 건드리지 않아. 서로 이해가 된 거라고 할 수 있지."
                }
            },
            choices = {
                [1] = {en = "Found anything useful?", ko = "쓸만한 거 찾았나요?"},
                [3] = {en = "What about the cliffs to the north?", ko = "북쪽 절벽에 대해서는요?"},
                [4] = {en = "A peaceful arrangement. Farewell.", ko = "평화로운 합의군요. 안녕히."}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    en = "*glances around and lowers voice* North of here, there's a cliff face — drops straight down to the sea. Most folk don't bother going that way. But I've noticed something: between the rocks, there's a gap. Narrow, mind you, but deep enough that you can't see the end of it. I haven't gone in myself — I'm no fool — but something about it... the air that comes out of it feels different. Colder. Older. Make of that what you will.",
                    ko = "*주위를 둘러보고 목소리를 낮추며* 여기 북쪽에 절벽이 있어 — 바다까지 곧장 떨어지는. 대부분 사람들은 그쪽으로 가지 않지. 하지만 내가 눈치챈 게 있어: 바위 사이에 틈이 있거든. 좁긴 하지만, 끝이 안 보일 만큼 깊어. 직접 들어가 보진 않았어 — 바보는 아니니까 — 하지만 뭔가... 거기서 나오는 공기가 달라. 더 차갑고. 더 오래된 느낌이야. 알아서 판단해."
                }
            },
            choices = {
                [1] = {en = "Found anything useful in the junk?", ko = "쓰레기에서 쓸만한 거 찾았나요?"},
                [2] = {en = "What about the animals?", ko = "동물들은요?"},
                [4] = {en = "I will keep that in mind. Farewell.", ko = "기억해 두겠습니다. 안녕히."}
            }
        }
    end

    return nil
end
