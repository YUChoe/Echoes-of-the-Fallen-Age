-- Refugee (난민) 대화 스크립트
-- NPC ID: d4b8f9c0-1e2a-3b4c-5d6e-7f8a9b0c1d2e

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Please... " .. player_name .. ", is it? Have you come from inside the walls? Do you know if they are letting anyone else in?",
                ko = "제발... " .. player_name .. "이라고요? 성벽 안에서 오신 건가요? 다른 사람들도 들여보내 주는지 아시나요?"
            }
        },
        choices = {
            [1] = {en = "What happened to you?", ko = "무슨 일이 있었나요?"},
            [2] = {en = "Are you looking for someone?", ko = "누군가를 찾고 있나요?"},
            [3] = {en = "I am sorry, I do not know.", ko = "죄송합니다, 모르겠습니다."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "We fled when the creatures came. Our village was overrun in a single night. I got separated from my husband and children in the chaos. I have been waiting here by the gate for days, hoping they might turn up. The guards will not let me inside — they say the walls are at capacity. But out here... out here there is nothing.",
                    ko = "괴물들이 왔을 때 도망쳤어요. 마을이 하룻밤 만에 짓밟혔습니다. 혼란 속에서 남편과 아이들과 헤어졌어요. 며칠째 성문 앞에서 기다리고 있어요, 혹시 나타날까 해서. 경비병들은 안으로 들여보내 주지 않아요 — 성벽 안이 꽉 찼다고. 하지만 여기 밖에는... 밖에는 아무것도 없어요."
                }
            },
            choices = {
                [2] = {en = "Your family...", ko = "가족분들이..."},
                [3] = {en = "I hope they are safe.", ko = "무사하길 바랍니다."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "My husband. My two children. We were running together, but the road was dark and the creatures were everywhere. I told them to keep running towards the port... I do not know if they made it. Every day I watch the road, hoping to see them. Every day, nothing.",
                    ko = "남편이요. 두 아이도. 함께 달리고 있었는데, 길은 어둡고 괴물들이 사방에 있었어요. 항구 쪽으로 계속 달리라고 했는데... 도착했는지 모르겠어요. 매일 길을 바라보며 그들이 보이길 바라요. 매일, 아무도 안 와요."
                }
            },
            choices = {
                [1] = {en = "How did you end up here?", ko = "어떻게 여기까지 오셨나요?"},
                [3] = {en = "Do not lose hope.", ko = "희망을 잃지 마세요."}
            }
        }
    end

    return nil
end
