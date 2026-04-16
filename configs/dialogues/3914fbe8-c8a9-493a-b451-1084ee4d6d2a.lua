-- Veteran Guard 대화 스크립트
-- NPC ID: 3914fbe8-c8a9-493a-b451-1084ee4d6d2a

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Halt! I haven't seen your face before, " .. player_name .. ". State your business.",
                ko = "멈춰라! " .. player_name .. ", 처음 보는 얼굴이군. 용건을 말하라."
            }
        },
        choices = {
            [1] = {en = "Who are you?", ko = "누구신가요?"}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "I am a veteran guard of this town. I've been protecting these walls for over twenty years. If you need anything, speak to the merchants in the square.",
                    ko = "나는 이 마을의 베테랑 경비병이다. 20년 넘게 이 성벽을 지켜왔지. 필요한 게 있으면 광장의 상인들에게 말하라."
                }
            }
        }
    end
    return nil
end
