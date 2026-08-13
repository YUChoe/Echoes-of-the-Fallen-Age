-- Fisherman (어부) 대화 스크립트
-- NPC ID: c9a3e4b5-6d7f-8a9b-0c1d-2e3f4a5b6c7d

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.fisherman.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.fisherman.intro.choice.1", params = {}},
            [2] = {key = "npc.fisherman.intro.choice.2", params = {}},
            [3] = {key = "npc.fisherman.intro.choice.3", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.fisherman.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.fisherman.c1.choice.2", params = {}},
                [3] = {key = "npc.fisherman.c1.choice.3", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.fisherman.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.fisherman.c2.choice.1", params = {}},
                [3] = {key = "npc.fisherman.c2.choice.3", params = {}}
            }
        }
    end

    return nil
end
