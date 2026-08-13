-- Gate Warden (성문 관리인) 대화 스크립트
-- NPC ID: c3a7e8b9-0d1f-2a3b-4c5d-6e7f8a9b0c1d

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.gate_warden.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.gate_warden.intro.choice.1", params = {}},
            [2] = {key = "npc.gate_warden.intro.choice.2", params = {}},
            [3] = {key = "npc.gate_warden.intro.choice.3", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.gate_warden.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.gate_warden.c1.choice.2", params = {}},
                [3] = {key = "npc.gate_warden.c1.choice.3", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.gate_warden.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.gate_warden.c2.choice.1", params = {}},
                [3] = {key = "npc.gate_warden.c2.choice.3", params = {}}
            }
        }
    end

    return nil
end
