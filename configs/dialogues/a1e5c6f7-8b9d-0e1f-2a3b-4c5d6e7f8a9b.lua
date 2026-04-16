-- Priest (사제) 대화 스크립트
-- NPC ID: a1e5c6f7-8b9d-0e1f-2a3b-4c5d6e7f8a9b

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Blessings upon you, " .. player_name .. ". This humble shrine is all that remains of our faith. The gods have been silent for a very long time, but we tend their memory still.",
                ko = "축복이 함께하길, " .. player_name .. ". 이 초라한 제단이 우리 신앙에 남은 전부입니다. 신들은 아주 오랫동안 침묵하고 있지만, 우리는 여전히 그 기억을 돌보고 있습니다."
            }
        },
        choices = {
            [1] = {en = "Who are the forgotten gods?", ko = "잊혀진 신들은 누구인가요?"},
            [2] = {en = "I have heard about the necropolis beneath the church.", ko = "교회 아래 네크로폴리스에 대해 들었습니다."},
            [3] = {en = "May the gods watch over you.", ko = "신들이 지켜주시길."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "Their names are fading from memory. Once, they were worshipped across the empire — gods of harvest, of war, of the sea. Now only a handful of us remember the old rites. Whether they still listen... I cannot say. But faith costs nothing, and in times like these, it is all some of us have left.",
                    ko = "그 이름들은 기억에서 사라져 가고 있습니다. 한때 제국 전역에서 숭배받았지요 — 수확의 신, 전쟁의 신, 바다의 신. 이제 옛 의식을 기억하는 이는 손에 꼽습니다. 그들이 아직 듣고 있는지는... 말할 수 없습니다. 하지만 신앙에는 대가가 없고, 이런 시대에 그것이 우리에게 남은 전부이기도 합니다."
                }
            },
            choices = {
                [2] = {en = "What about the necropolis?", ko = "네크로폴리스는요?"},
                [3] = {en = "Thank you, Father.", ko = "감사합니다, 신부님."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "Beneath this church lies a place of the dead — ancient catacombs that stretch deeper than anyone has dared to map. There are... rumours. Sounds from below. Brother Aldric guards the entrance and turns away all who approach. I would urge you to heed his warning. Whatever stirs down there, it is not meant for the living.",
                    ko = "이 교회 아래에는 죽은 자들의 장소가 있습니다 — 누구도 감히 지도를 그리지 못할 만큼 깊이 뻗은 고대 지하묘지입니다. 소문이... 있습니다. 아래에서 들려오는 소리들. 알드릭 수사가 입구를 지키며 다가오는 모든 이를 돌려보냅니다. 그의 경고에 귀 기울이시길 권합니다. 저 아래에서 꿈틀거리는 것이 무엇이든, 산 자를 위한 것이 아닙니다."
                }
            },
            choices = {
                [1] = {en = "Tell me about the forgotten gods.", ko = "잊혀진 신들에 대해 알려주세요."},
                [3] = {en = "I shall be careful.", ko = "조심하겠습니다."}
            }
        }
    end

    return nil
end
