-- Drunken Refugee (술에 취한 난민) 대화 스크립트
-- NPC ID: e9c3a4d5-6f7b-8c9d-0e1f-2a3b4c5d6e7f

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "*hic* ...Who're you? " .. player_name .. "? Doesn't matter... nothing matters any more. Sit down if you want, I don't care...",
                ko = "*딸꾹* ...누구야? " .. player_name .. "? 상관없어... 이제 아무것도 상관없다고. 앉고 싶으면 앉아, 난 신경 안 써..."
            }
        },
        choices = {
            [1] = {en = "What happened to you?", ko = "무슨 일이 있었나요?"},
            [2] = {en = "I heard rumours about a great sorcerer.", ko = "대마법사에 대한 소문을 들었습니다."},
            [3] = {en = "Have you heard any other rumours?", ko = "다른 소문을 들은 게 있나요?"},
            [4] = {en = "Take care of yourself.", ko = "몸 조심하세요."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "The expedition... the third one. I went with them, you know. We were going to find this so-called sorcerer and put an end to it all. *hic* ...We found nothing. Just a blinding light — bright, enormous — and then everyone was screaming. I barely made it back. My family... I don't even know if they're still alive.",
                    ko = "원정이야... 세 번째. 나도 같이 갔었어. 소위 마법사란 놈을 찾아서 모든 걸 끝내려고 했지. *딸꾹* ...아무것도 못 찾았어. 그냥 눈부신 빛 — 밝고, 거대한 — 그리고 모두가 비명을 질렀어. 겨우 돌아왔다. 가족은... 살아 있는지조차 모르겠어."
                }
            },
            choices = {
                [2] = {en = "Tell me about this sorcerer.", ko = "그 마법사에 대해 말해주세요."},
                [3] = {en = "Any other rumours?", ko = "다른 소문은요?"},
                [4] = {en = "I am sorry. Take care.", ko = "유감입니다. 몸 조심하세요."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "Sorcerer? *laughs bitterly* Nobody's ever seen him. Nobody can even explain what happened properly. They say he appeared about a hundred years ago and everything went wrong after that — forests grew wild, creatures came out of nowhere. But sorcery? In this world? Nobody believes in such nonsense. It was just... a light. A terrible, blinding light. That's all anyone remembers.",
                    ko = "마법사? *씁쓸하게 웃으며* 아무도 본 적 없어. 무슨 일이 있었는지 제대로 설명하는 사람도 없고. 백여 년 전에 나타났다고 하고 그 뒤로 모든 게 엉망이 됐다지 — 숲은 미쳐 자라고, 괴물들이 어디선가 나타나고. 하지만 마법이라고? 이 세상에서? 아무도 그런 헛소리를 믿지 않아. 그냥... 빛이었어. 끔찍하고 눈부신 빛. 그게 다야."
                }
            },
            choices = {
                [1] = {en = "What happened on the expedition?", ko = "원정에서 무슨 일이 있었나요?"},
                [3] = {en = "Any other rumours?", ko = "다른 소문은요?"},
                [4] = {en = "I hope you find your family.", ko = "가족을 찾길 바랍니다."}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    en = "*hic* Rumours? Oh, there's plenty of those going round... which sort?",
                    ko = "*딸꾹* 소문? 아, 그런 건 넘쳐나지... 어떤 종류?"
                }
            },
            choices = {
                [31] = {en = "Is the king truly alive?", ko = "왕이 정말 살아 있나요?"},
                [32] = {en = "What about the blinding light?", ko = "그 눈부신 빛은 뭐였나요?"},
                [4] = {en = "Never mind. Rest well.", ko = "됐어요. 푹 쉬세요."}
            }
        }
    end

    if choice_number == 31 then
        return {
            text = {
                {
                    en = "*lowers voice* The king? *hic* ...I'll tell you what I think. I think the king's dead. Been dead for a while, maybe. The advisers — they're the ones running things now. You ever notice how nobody actually sees him? Always 'the king is resting' or 'the king is in council'. Council with whom, I ask? Dead men don't hold council. *hic* ...But what do I know. I'm just a drunk.",
                    ko = "*목소리를 낮추며* 왕? *딸꾹* ...내 생각을 말해줄까. 왕은 죽었어. 꽤 오래전에, 아마. 대신들이 — 지금 실제로 일을 돌리는 건 그 사람들이야. 아무도 왕을 직접 본 적 없다는 거 눈치챘어? 항상 '왕이 쉬고 계신다'거나 '왕이 회의 중이시다'라고만 하지. 누구랑 회의를 한다는 거야? 죽은 사람은 회의를 하지 않아. *딸꾹* ...하지만 내가 뭘 알겠어. 난 그냥 술주정뱅이야."
                }
            },
            choices = {
                [32] = {en = "What about the blinding light?", ko = "그 눈부신 빛은 뭐였나요?"},
                [1] = {en = "Tell me about the expedition.", ko = "원정에 대해 말해주세요."},
                [4] = {en = "Interesting. Take care.", ko = "흥미롭군요. 몸 조심하세요."}
            }
        }
    end

    if choice_number == 32 then
        return {
            text = {
                {
                    en = "*stares into his cup* The light... *hic* ...everyone talks about it like it was some weapon. But I was there, you know. And when that light hit us... it didn't feel like an attack. It felt... warm. Clean. Like the first light of dawn, if dawn could kill you. Some of the old folk in the chapel — they whisper that it was Alva. The sun god himself, shining down on us. Whether to protect or to punish, nobody can say. *hic* ...Makes you think, doesn't it?",
                    ko = "*잔을 들여다보며* 그 빛... *딸꾹* ...다들 무기였다는 듯이 말하지. 하지만 나는 거기 있었어. 그 빛이 우리를 덮쳤을 때... 공격 같은 느낌이 아니었어. 그건... 따뜻했어. 깨끗했고. 새벽의 첫 빛 같았어, 새벽빛이 사람을 죽일 수 있다면 말이야. 예배당의 늙은이들 중에 — 그게 알바였다고 속삭이는 사람들이 있어. 태양신 자신이 우리에게 빛을 비추었다고. 보호하려 한 건지 벌하려 한 건지, 아무도 말할 수 없지. *딸꾹* ...생각하게 만들지, 안 그래?"
                }
            },
            choices = {
                [31] = {en = "Is the king truly alive?", ko = "왕이 정말 살아 있나요?"},
                [1] = {en = "Tell me about the expedition.", ko = "원정에 대해 말해주세요."},
                [4] = {en = "It does. Farewell.", ko = "그러게요. 안녕히."}
            }
        }
    end

    return nil
end
