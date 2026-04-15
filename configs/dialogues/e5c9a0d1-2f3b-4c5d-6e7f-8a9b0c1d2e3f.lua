-- Disgruntled Farmer (불만 가득한 농부) 대화 스크립트
-- NPC ID: e5c9a0d1-2f3b-4c5d-6e7f-8a9b0c1d2e3f

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "What do you want, " .. player_name .. "? Come to gawk at us like the rest of them behind those walls?",
                ko = "뭘 원하는 거야, " .. player_name .. "? 성벽 뒤에 있는 놈들처럼 우리를 구경하러 온 거야?"
            }
        },
        choices = {
            [1] = {en = "Why are you so angry?", ko = "왜 그렇게 화가 나 있나요?"},
            [2] = {en = "What happened to your farm?", ko = "농장에 무슨 일이 있었나요?"},
            [3] = {en = "I meant no offence.", ko = "기분 나쁘게 하려는 건 아니었습니다."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "Angry? I have every right to be! They ordered us to leave our land — our homes, our fields — so their precious walls have a clear view. And what do we get? Nothing. Not a single coin, not a scrap of food. Meanwhile, those lot inside eat and sleep safe and sound. They do not care about us. Never have.",
                    ko = "화가 나냐고? 당연히 화가 나지! 우리 땅을 떠나라고 명령했어 — 집도, 밭도 — 그 소중한 성벽의 시야를 확보하겠다고. 그래서 우리가 뭘 받았냐? 아무것도. 동전 한 닢, 음식 한 조각도 없어. 그 사이 안에 있는 놈들은 편히 먹고 자고. 우리 따위 신경도 안 써. 한 번도 안 그랬어."
                }
            },
            choices = {
                [2] = {en = "Your crops...", ko = "농작물은..."},
                [3] = {en = "I understand your frustration.", ko = "분노를 이해합니다."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "Trampled. Half by the creatures that come out at night, half by the knights who marched through without a care. Three generations my family worked that soil. Now it is ruined, and I am told to move further away as if the land means nothing. If this is their idea of protection, I want no part of it.",
                    ko = "짓밟혔어. 반은 밤에 나타나는 괴물들한테, 반은 아무렇지도 않게 행군한 기사들한테. 삼 대에 걸쳐 우리 가족이 일군 땅이야. 이제 망가졌고, 땅이 아무 의미도 없다는 듯이 더 멀리 이동하라고 해. 이게 그들이 말하는 보호라면, 난 그딴 거 필요 없어."
                }
            },
            choices = {
                [1] = {en = "About the relocation order...", ko = "이주 명령에 대해서..."},
                [3] = {en = "I am sorry for your loss.", ko = "유감입니다."}
            }
        }
    end

    return nil
end
