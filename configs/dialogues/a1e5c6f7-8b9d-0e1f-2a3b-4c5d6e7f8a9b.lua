-- Priest (사제) 대화 스크립트
-- NPC ID: a1e5c6f7-8b9d-0e1f-2a3b-4c5d6e7f8a9b

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Blessings of Alva upon you, " .. player_name .. ". This humble chapel is dedicated to the sun god — the gentle light of dawn. Few remember the old ways, but we tend the faith still.",
                ko = "알바의 축복이 함께하길, " .. player_name .. ". 이 소박한 예배당은 태양신에게 바쳐진 곳입니다 — 새벽녘의 온화한 빛이지요. 옛 방식을 기억하는 이는 적지만, 우리는 여전히 신앙을 돌보고 있습니다."
            }
        },
        choices = {
            [1] = {en = "Who is Alva?", ko = "알바는 누구인가요?"},
            [2] = {en = "Tell me about this chapel.", ko = "이 예배당에 대해 알려주세요."},
            [3] = {en = "Where can one make an offering?", ko = "제물은 어디에 바칠 수 있나요?"},
            [4] = {en = "May Alva watch over you.", ko = "알바가 지켜주시길."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "Alva is the sun god of Karnas. The name comes from an old word meaning 'white' or 'bright' — not the searing heat of midday, but the soft, clean light of dawn. Over the centuries, the faith settled into everyday life like a quiet habit. There are no sabbaths or grand gatherings any longer; Alva's teachings simply guide how folk live, day by day.",
                    ko = "알바는 카르나스의 태양신입니다. 그 이름은 '희다', '밝다'라는 뜻의 고어에서 유래했지요 — 한낮의 뜨거운 열기가 아니라, 새벽녘의 부드럽고 깨끗한 빛을 뜻합니다. 수백 년에 걸쳐 신앙은 조용한 습관처럼 일상 속에 자리 잡았습니다. 안식일이나 큰 모임 같은 것은 더 이상 남아 있지 않고, 알바의 가르침은 그저 사람들이 하루하루를 살아가는 방식을 이끌어 줄 뿐입니다."
                }
            },
            choices = {
                [2] = {en = "Tell me about this chapel.", ko = "이 예배당에 대해 알려주세요."},
                [3] = {en = "Where can one make an offering?", ko = "제물은 어디에 바칠 수 있나요?"},
                [4] = {en = "Thank you, Father.", ko = "감사합니다, 신부님."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "This chapel has stood within the fortress walls for longer than anyone can recall. Before the remnants of the army arrived, it was a quiet place — just one monk studying the faith in solitude, and a couple of homeless folk who had taken shelter here. Now it serves a greater purpose, though I sometimes wonder what became of those who once called it home.",
                    ko = "이 예배당은 누구도 기억하지 못할 만큼 오래전부터 요새 성벽 안에 서 있었습니다. 패잔병들이 들어오기 전에는 조용한 곳이었지요 — 홀로 신앙을 공부하는 수도승 한 명과, 이곳에 몸을 의탁한 노숙자 두어 명뿐이었습니다. 이제는 더 큰 목적을 위해 쓰이고 있지만, 가끔 예전에 이곳을 집이라 부르던 이들이 어떻게 되었는지 궁금해지곤 합니다."
                }
            },
            choices = {
                [1] = {en = "Who is Alva?", ko = "알바는 누구인가요?"},
                [3] = {en = "Where can one make an offering?", ko = "제물은 어디에 바칠 수 있나요?"},
                [4] = {en = "I shall remember that.", ko = "기억하겠습니다."}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    en = "Out on the dry plains, you may find stone altars — flat platforms of fitted stone, about thirty centimetres thick, with a small table at the centre for placing offerings. They were built in the old days when folk still gathered to honour Alva beneath the open sky. Some say the altars still carry a trace of the dawn light, even at dusk.",
                    ko = "마른 평야에 나가면 돌 제단을 찾을 수 있을 겁니다 — 약 30센티미터 두께로 짜 맞춰진 돌바닥 위에, 가운데 제물을 올려두는 작은 상이 있지요. 사람들이 아직 열린 하늘 아래 모여 알바를 기렸던 옛날에 지어진 것입니다. 어떤 이들은 그 제단이 해질녘에도 새벽빛의 흔적을 간직하고 있다고 말합니다."
                }
            },
            choices = {
                [1] = {en = "Who is Alva?", ko = "알바는 누구인가요?"},
                [2] = {en = "Tell me about this chapel.", ko = "이 예배당에 대해 알려주세요."},
                [4] = {en = "I shall seek one out.", ko = "찾아보겠습니다."}
            }
        }
    end

    return nil
end
