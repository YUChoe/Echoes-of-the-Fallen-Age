-- Royal Guard (왕실 경비병) 대화 스크립트
-- NPC ID: b8f2d3a4-5c6e-7f8a-9b0c-1d2e3f4a5b6c

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Hold. " .. player_name .. ", this is the entrance to the castle. State your purpose or move along.",
                ko = "멈춰라. " .. player_name .. ", 여기는 성 입구다. 용건을 밝히거나 물러가라."
            }
        },
        choices = {
            [1] = {en = "I wish to enter the castle.", ko = "성에 들어가고 싶습니다."},
            [2] = {en = "Who do you protect?", ko = "누구를 지키고 있나요?"},
            [3] = {en = "I will be on my way.", ko = "가던 길을 가겠습니다."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "Not without proper authority. The castle is restricted to the king's court and those with express permission. I do not make the rules, but I enforce them. If you have business with the adviser, you will need to obtain clearance first.",
                    ko = "적절한 권한 없이는 안 된다. 성은 왕의 궁정과 명시적 허가를 받은 자만 출입할 수 있다. 규칙을 만든 건 내가 아니지만, 시행하는 건 나다. 조언자와 볼일이 있다면, 먼저 허가를 받아야 한다."
                }
            },
            choices = {
                [2] = {en = "Who is inside?", ko = "안에 누가 있나요?"},
                [3] = {en = "Understood.", ko = "알겠습니다."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "The king and what remains of his court. That is all you need to know. My duty is to ensure no one passes without authorisation. These are troubled times, and the castle must remain secure. I will not discuss this further.",
                    ko = "왕과 남아 있는 궁정 사람들이다. 그것만 알면 된다. 내 임무는 허가 없이 아무도 지나가지 못하게 하는 것이다. 어려운 시기이고, 성은 안전하게 유지되어야 한다. 더 이상 이야기하지 않겠다."
                }
            },
            choices = {
                [1] = {en = "Can I enter?", ko = "들어갈 수 있나요?"},
                [3] = {en = "Very well. Farewell.", ko = "알겠습니다. 안녕히."}
            }
        }
    end

    return nil
end
