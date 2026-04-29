-- Royal Adviser (왕의 조언자) 대화 스크립트
-- NPC ID: a7e1c2f3-4b5d-6e7f-8a9b-0c1d2e3f4a5b

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Ah, " .. player_name .. ". You have found your way to the castle. I am the king's adviser — what remains of the court, at any rate. Speak, but choose your words with care.",
                ko = "아, " .. player_name .. ". 성까지 찾아왔군. 나는 왕의 조언자다 — 남아 있는 궁정이라고 할 수 있는 것의. 말해 보게, 하지만 말을 가려서 하게."
            }
        },
        choices = {
            [1] = {en = "What is the political situation?", ko = "정치 상황은 어떤가요?"},
            [2] = {en = "I heard the heir is missing.", ko = "왕위 계승자가 행방불명이라고 들었습니다."},
            [3] = {en = "How is the king's health?", ko = "왕의 건강은 어떤가요?"},
            [4] = {en = "I shall not take more of your time.", ko = "더 이상 시간을 빼앗지 않겠습니다."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "Delicate. That is the kindest word for it. The king rules, but his authority wanes with each passing day. The last expedition cost us dearly — not just in lives, but in the line of succession itself. There are those who would exploit the uncertainty. I do what I can to hold things together, but I am only one man.",
                    ko = "미묘하다. 가장 부드럽게 표현하면 그렇지. 왕이 다스리고 있지만, 권위는 날이 갈수록 약해지고 있다. 마지막 원정은 큰 대가를 치렀어 — 목숨뿐만 아니라, 왕위 계승 자체에도. 이 불확실성을 이용하려는 자들이 있다. 상황을 유지하려고 할 수 있는 건 하고 있지만, 나는 한 사람일 뿐이야."
                }
            },
            choices = {
                [2] = {en = "The missing heir...", ko = "행방불명된 계승자..."},
                [3] = {en = "And the king himself?", ko = "왕 본인은요?"},
                [4] = {en = "I understand. Farewell.", ko = "이해합니다. 안녕히."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "...You are well informed. Yes. The king's brother and his son both vanished during the third expedition. Whether they fell in battle or were lost in the chaos, no one can say. Without a clear successor, the vultures circle. I would advise you not to speak of this too freely. There are ears in every corridor.",
                    ko = "...소식이 빠르군. 그래. 왕의 동생과 아들 모두 세 번째 원정 중에 사라졌다. 전투에서 쓰러졌는지 혼란 속에서 길을 잃었는지, 아무도 말할 수 없어. 명확한 후계자가 없으니, 독수리들이 맴돌고 있지. 이 이야기를 너무 자유롭게 하지 않는 게 좋을 거야. 모든 복도에 귀가 있으니."
                }
            },
            choices = {
                [1] = {en = "How is the king managing?", ko = "왕은 어떻게 대처하고 있나요?"},
                [3] = {en = "Is the king well?", ko = "왕은 건강한가요?"},
                [4] = {en = "I shall be discreet.", ko = "조심하겠습니다."}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    en = "*pauses, choosing words carefully* The king... rests. He has been resting for some time now. The burdens of rule weigh heavily upon him, as you might imagine. I attend to matters in his stead when he is... indisposed. That is all I can say on the matter. I trust you understand the delicacy of the situation.",
                    ko = "*잠시 멈추고 말을 고르며* 왕은... 쉬고 계시다. 꽤 오랫동안 쉬고 계시지. 통치의 짐이 무겁게 짓누르고 있다네, 짐작하겠지만. 왕이... 자리를 비울 때는 내가 대신 일을 처리하고 있다. 이 문제에 대해서는 그 이상 말할 수 없네. 상황의 민감함을 이해하리라 믿네."
                }
            },
            choices = {
                [1] = {en = "What is the political situation?", ko = "정치 상황은 어떤가요?"},
                [2] = {en = "And the missing heir?", ko = "행방불명된 계승자는요?"},
                [4] = {en = "I understand. I shall say no more.", ko = "이해합니다. 더 이상 묻지 않겠습니다."}
            }
        }
    end

    return nil
end
