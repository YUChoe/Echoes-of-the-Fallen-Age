-- Wandering Bard (떠돌이 음유시인) 대화 스크립트
-- NPC ID: f0d4b5e6-7a8c-9d0e-1f2a-3b4c5d6e7f8a

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Ah, a fresh face. " .. player_name .. ", is it? Pull up a chair. I have stories, if you have the stomach for them. Not the cheerful sort, mind you.",
                ko = "아, 새로운 얼굴이군. " .. player_name .. "이라고? 의자를 끌어당겨. 이야기가 있다네, 들을 배짱이 있다면. 유쾌한 종류는 아니지만."
            }
        },
        choices = {
            [1] = {en = "Tell me about the Golden Age.", ko = "황금의 시대에 대해 들려주세요."},
            [2] = {en = "What happened to the empire?", ko = "제국에 무슨 일이 있었나요?"},
            [3] = {en = "Have you heard any rumours?", ko = "소문을 들은 게 있나요?"},
            [4] = {en = "Perhaps another time.", ko = "다음에 듣겠습니다."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "The Golden Age... when the empire of Karnas stretched across the continent. Gods and men walked closer then, or so the old songs say. Machines of wondrous craft, prosperity beyond measure. But balance is a fickle thing. It all came crashing down — gods, men, and everything in between.",
                    ko = "황금의 시대라... 카르나스 제국이 대륙을 가로질러 뻗어 있던 때지. 신과 인간이 더 가까이 걸었다고, 옛 노래들은 그렇게 전하네. 경이로운 기계들, 헤아릴 수 없는 번영. 하지만 균형이란 변덕스러운 것이야. 모든 것이 무너져 내렸지 — 신도, 인간도, 그 사이의 모든 것도."
                }
            },
            choices = {
                [2] = {en = "And then what happened?", ko = "그 다음엔 어떻게 됐나요?"},
                [3] = {en = "Any rumours floating about?", ko = "떠도는 소문은 없나요?"},
                [4] = {en = "Thank you for the tale.", ko = "이야기 감사합니다."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "The empire burned. Then, about a hundred years ago, someone they call the Great Sorcerer appeared — though no one has ever laid eyes on him. After that, the forests grew thick and hostile, and creatures from old tales began crawling out. Goblins, orcs, beasts that attack on sight. The world changed, and not for the better. Now we huddle here in Greyhaven, the last refuge of the living.",
                    ko = "제국은 불탔지. 그리고 약 백여 년 전, 대마법사라 불리는 자가 나타났다네 — 물론 아무도 직접 본 적은 없지만. 그 뒤로 숲은 울창하고 적대적으로 변했고, 옛 이야기 속 괴물들이 기어 나오기 시작했어. 고블린, 오크, 보이는 대로 공격하는 짐승들. 세상이 변했고, 좋은 쪽은 아니야. 이제 우리는 산 자들의 마지막 피난처인 잿빛 항구에 모여 있다네."
                }
            },
            choices = {
                [1] = {en = "Tell me about the Golden Age.", ko = "황금의 시대에 대해 들려주세요."},
                [3] = {en = "Any rumours floating about?", ko = "떠도는 소문은 없나요?"},
                [4] = {en = "A grim tale indeed.", ko = "참으로 암울한 이야기군요."}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    en = "Rumours? A bard always has an ear to the ground. Which sort interests you?",
                    ko = "소문? 음유시인은 언제나 귀를 열어두고 있지. 어떤 종류가 궁금한가?"
                }
            },
            choices = {
                [31] = {en = "Tell me about Alva, the sun god.", ko = "태양신 알바에 대해 알려주세요."},
                [32] = {en = "I heard the harvests have been failing.", ko = "농사가 계속 실패하고 있다고 들었습니다."},
                [33] = {en = "Is it true the Great Sorcerer came from the future?", ko = "대마법사가 미래에서 왔다는 게 사실인가요?"},
                [4] = {en = "Never mind. Farewell.", ko = "됐습니다. 안녕히."}
            }
        }
    end

    if choice_number == 31 then
        return {
            text = {
                {
                    en = "Alva — the sun god. The name means 'white' or 'bright' in the old tongue. Not the blinding glare of noon, mind you, but the gentle glow of first light. Folk used to gather at stone altars on the plains to leave offerings. These days the faith has faded into habit — no grand rites, just quiet customs woven into daily life. There is still a chapel inside the fortress, tended by a monk who chose solitude over the bustle of the world.",
                    ko = "알바 — 태양신이지. 그 이름은 고어로 '희다' 또는 '밝다'라는 뜻이야. 한낮의 눈부신 빛이 아니라, 첫 빛의 온화한 빛을 말하는 거지. 사람들은 평야의 돌 제단에 모여 제물을 바치곤 했어. 요즘은 신앙이 습관처럼 희미해졌지 — 거창한 의식은 없고, 그저 일상에 스며든 조용한 관습뿐이야. 요새 안에 아직 예배당이 있는데, 세상의 번잡함 대신 고독을 택한 수도승이 돌보고 있다네."
                }
            },
            choices = {
                [32] = {en = "What about the failing harvests?", ko = "농사 실패에 대해서는요?"},
                [33] = {en = "And the Great Sorcerer?", ko = "대마법사는요?"},
                [4] = {en = "Interesting. Thank you.", ko = "흥미롭군요. 감사합니다."}
            }
        }
    end

    if choice_number == 32 then
        return {
            text = {
                {
                    en = "Aye, the crops wither and the livestock bear no young. It has been this way for years now — ever since the war against the Great Sorcerer began, some say. Whether it is a curse or simply rotten luck, the result is the same: empty bellies and growing despair. The farmers blame the sorcerer. The priests say nothing. And the rest of us just try to get by.",
                    ko = "그래, 작물은 시들고 가축은 새끼를 낳지 않아. 몇 년째 이런 상태야 — 대마법사와의 전쟁이 시작된 이후부터라고 하는 사람들도 있지. 저주인지 그냥 운이 나쁜 건지, 결과는 같아: 빈 배와 커져가는 절망. 농부들은 마법사를 탓하고, 사제들은 아무 말도 않고, 나머지 우리는 그냥 버텨나갈 뿐이야."
                }
            },
            choices = {
                [31] = {en = "Tell me about Alva.", ko = "알바에 대해 알려주세요."},
                [33] = {en = "And the Great Sorcerer?", ko = "대마법사는요?"},
                [4] = {en = "Dark times indeed.", ko = "정말 암울한 시대군요."}
            }
        }
    end

    if choice_number == 33 then
        return {
            text = {
                {
                    en = "Ha! That is the wildest tale of the lot. Some folk whisper that the Great Sorcerer is not from our time at all — that he came from the future, bringing knowledge and ruin in equal measure. Nobody believes in sorcery, of course, but the things that have happened since his appearance... forests swallowing roads, creatures crawling from nowhere, the dead refusing to stay dead. If he is not a sorcerer, then what is he? A good question with no good answer.",
                    ko = "하! 그건 소문 중에서도 가장 황당한 이야기지. 대마법사가 우리 시대 사람이 아니라 — 미래에서 왔다고 속삭이는 사람들이 있어. 지식과 파멸을 동시에 가져왔다나. 물론 아무도 마법 같은 건 믿지 않지만, 그가 나타난 이후 벌어진 일들은... 숲이 길을 삼키고, 괴물들이 어디선가 기어 나오고, 죽은 자들이 죽은 채로 있지 않으려 하고. 마법사가 아니라면 대체 뭐란 말인가? 좋은 답이 없는 좋은 질문이야."
                }
            },
            choices = {
                [31] = {en = "Tell me about Alva.", ko = "알바에 대해 알려주세요."},
                [32] = {en = "What about the failing harvests?", ko = "농사 실패에 대해서는요?"},
                [4] = {en = "A mystery indeed. Farewell.", ko = "정말 수수께끼로군요. 안녕히."}
            }
        }
    end

    return nil
end
