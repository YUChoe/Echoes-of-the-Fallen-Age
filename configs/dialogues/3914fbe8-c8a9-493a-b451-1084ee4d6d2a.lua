-- Brother Marcus (예배당 수도승) 대화 스크립트
-- NPC ID: 3914fbe8-c8a9-493a-b451-1084ee4d6d2a

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Peace be with you, " .. player_name .. ". I am Brother Marcus. This chapel is my charge — a quiet place of Alva, the sun god, within these fortress walls. You are welcome here.",
                ko = "평화가 함께하길, " .. player_name .. ". 나는 마르쿠스 수사입니다. 이 예배당은 내가 돌보는 곳이지요 — 요새 성벽 안에 있는 태양신 알바의 조용한 공간입니다. 환영합니다."
            }
        },
        choices = {
            [1] = {en = "Tell me about this chapel.", ko = "이 예배당에 대해 알려주세요."},
            [2] = {en = "What is the faith of Alva?", ko = "알바 신앙은 어떤 것인가요?"},
            [3] = {en = "What happened to the people who lived here before?", ko = "이전에 여기 살던 사람들은 어떻게 됐나요?"},
            [4] = {en = "May Alva's light guide you.", ko = "알바의 빛이 인도하시길."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "This chapel has been here longer than anyone can remember — a place of worship from the days when folk still gathered to honour Alva beneath the open sky. Before the remnants of the army arrived, it was just myself and a couple of homeless folk who had taken shelter within these walls. A monk and two lost souls, keeping the faith alive in silence. Now the fortress is full of people, and the chapel serves a greater purpose.",
                    ko = "이 예배당은 누구도 기억하지 못할 만큼 오래전부터 여기 있었습니다 — 사람들이 아직 열린 하늘 아래 모여 알바를 기리던 시절의 예배 장소이지요. 패잔병들이 들어오기 전에는 저와 이 성벽 안에 몸을 의탁한 노숙자 두어 명뿐이었습니다. 수도승 하나와 길 잃은 영혼 둘이 침묵 속에 신앙을 지키고 있었지요. 이제 요새는 사람들로 가득하고, 예배당은 더 큰 목적을 위해 쓰이고 있습니다."
                }
            },
            choices = {
                [2] = {en = "What is the faith of Alva?", ko = "알바 신앙은 어떤 것인가요?"},
                [3] = {en = "What became of the homeless folk?", ko = "노숙자들은 어떻게 됐나요?"},
                [4] = {en = "Thank you, Brother.", ko = "감사합니다, 수사님."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "Alva is the sun god — the gentle light of dawn, not the scorching heat of midday. The name comes from an old word meaning 'white' or 'bright'. Over the centuries, the faith settled into everyday life; there are no sabbaths or grand gatherings any longer. I chose to live apart from the world to study the god in solitude — in a quiet place like this, away from the bustle. That is the way of those who wish to understand Alva more deeply. We advise, we reflect, and we keep the old knowledge alive.",
                    ko = "알바는 태양신입니다 — 한낮의 뜨거운 열기가 아니라, 새벽녘의 온화한 빛이지요. 그 이름은 '희다' 또는 '밝다'라는 뜻의 고어에서 유래했습니다. 수백 년에 걸쳐 신앙은 일상 속에 자리 잡았고, 안식일이나 큰 모임 같은 것은 더 이상 남아 있지 않습니다. 저는 일상과 떨어져 홀로 신을 공부하는 삶을 택했습니다 — 이런 한적한 곳에서, 세상의 번잡함을 벗어나. 알바를 더 깊이 이해하고자 하는 이들의 방식이지요. 우리는 조언하고, 성찰하고, 옛 지식을 살려 둡니다."
                }
            },
            choices = {
                [1] = {en = "Tell me about this chapel.", ko = "이 예배당에 대해 알려주세요."},
                [3] = {en = "The homeless folk who were here...", ko = "여기 있던 노숙자들은..."},
                [4] = {en = "A noble calling. Farewell.", ko = "고귀한 소명이군요. 안녕히."}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    en = "*sighs quietly* That is a question I ask myself. When the soldiers arrived, everything changed so quickly. The two who sheltered here... they simply vanished one day. I do not know whether they left of their own will or were driven out by the commotion. I pray to Alva that they found safety somewhere. But in times like these, prayers are often all we have.",
                    ko = "*조용히 한숨을 쉬며* 저도 스스로에게 묻는 질문입니다. 병사들이 들어왔을 때, 모든 것이 너무 빨리 변했지요. 여기 몸을 의탁하던 두 사람은... 어느 날 그냥 사라졌습니다. 스스로 떠난 건지 소란에 밀려난 건지 알 수 없습니다. 어딘가에서 안전을 찾았기를 알바에게 기도합니다. 하지만 이런 시대에, 기도가 우리가 가진 전부인 경우가 많지요."
                }
            },
            choices = {
                [1] = {en = "Tell me about this chapel.", ko = "이 예배당에 대해 알려주세요."},
                [2] = {en = "What is the faith of Alva?", ko = "알바 신앙은 어떤 것인가요?"},
                [4] = {en = "I hope they are safe. Farewell.", ko = "무사하길 바랍니다. 안녕히."}
            }
        }
    end

    return nil
end
