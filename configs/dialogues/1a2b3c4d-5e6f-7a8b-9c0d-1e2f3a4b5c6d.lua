-- Village Tavern Keeper (마을 술집 주인) 대화 스크립트
-- NPC ID: 1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Another stranger. " .. player_name .. ", is it? Well, you're welcome to a drink, but don't expect a warm smile. We've had enough trouble from the castle folk without adding more.",
                ko = "또 낯선 사람이군. " .. player_name .. "이라고? 뭐, 한 잔 하고 싶으면 해. 하지만 환한 미소는 기대하지 마. 성 안 사람들 때문에 골치가 이만저만이 아니거든."
            }
        },
        choices = {
            [1] = {en = "What trouble do you mean?", ko = "무슨 골치거리인가요?"},
            [2] = {en = "Tell me about this village.", ko = "이 마을에 대해 알려주세요."},
            [3] = {en = "I heard the harvests have been failing.", ko = "농사가 계속 실패하고 있다고 들었습니다."},
            [4] = {en = "I will leave you be.", ko = "그만 가보겠습니다."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "The relocation order, that's what. The Ash Knights decided our village is too close to the fortress walls, so we've been told to pack up and move further out. Further out — where the creatures roam and the roads are barely safe. Easy for them to say from behind their stone walls, isn't it? Nobody here is happy about it. Nobody.",
                    ko = "이주 명령이야, 그게 문제지. 잿빛 기사단이 우리 마을이 요새 성벽에 너무 가깝다고 판단해서, 짐 싸서 더 먼 곳으로 이주하라는 명령을 내렸어. 더 먼 곳 — 괴물들이 돌아다니고 길도 안전하지 않은 곳으로. 돌벽 뒤에 숨어서 말하기는 쉽지, 안 그래? 여기 아무도 그 명령에 만족하는 사람 없어. 아무도."
                }
            },
            choices = {
                [2] = {en = "Tell me about this village.", ko = "이 마을에 대해 알려주세요."},
                [3] = {en = "What about the harvests?", ko = "농사는 어떤가요?"},
                [4] = {en = "I see. Take care.", ko = "그렇군요. 몸 조심하세요."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "It's a small place — no proper name, even. But it was ours. We've got this tavern, a stable, and a militia that keeps watch. There's a public notice board by the road, too. While the castle sat empty, this village was the heart of everything round here. Now they want us gone. Typical.",
                    ko = "작은 곳이야 — 제대로 된 이름도 없어. 하지만 우리 마을이었지. 이 술집이 있고, 마구간이 있고, 경비를 서는 자경단이 있어. 길가에 공공 게시판도 있고. 성이 비어 있는 동안, 이 마을이 이 근방의 중심이었다고. 이제 와서 우리보고 나가라니. 전형적이야."
                }
            },
            choices = {
                [1] = {en = "What about the relocation order?", ko = "이주 명령은 어떻게 된 건가요?"},
                [3] = {en = "How are the harvests?", ko = "농사는 어떤가요?"},
                [4] = {en = "Thank you for telling me.", ko = "알려줘서 감사합니다."}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    en = "Failing? That's putting it mildly. The crops wither before they ripen, and the livestock won't breed. It's been years now — ever since they started that fool war against the so-called sorcerer. Some say it's a curse. I say it's just our rotten luck piling up. Either way, bellies are empty and tempers are short.",
                    ko = "실패? 그건 순하게 말한 거야. 작물은 익기도 전에 시들고, 가축은 새끼를 낳지 않아. 몇 년째 이래 — 소위 마법사란 놈한테 바보 같은 전쟁을 시작한 이후로. 저주라고 하는 사람도 있어. 난 그냥 우리 불운이 쌓인 거라고 봐. 어쨌든 배는 비고 성질은 날카로워지고 있지."
                }
            },
            choices = {
                [1] = {en = "What about the relocation order?", ko = "이주 명령은 어떻게 된 건가요?"},
                [2] = {en = "Tell me about this village.", ko = "이 마을에 대해 알려주세요."},
                [4] = {en = "Hard times. Farewell.", ko = "힘든 시절이군요. 안녕히."}
            }
        }
    end

    return nil
end
