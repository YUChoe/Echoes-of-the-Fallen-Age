-- Refugee (난민) 대화 스크립트
-- NPC ID: d4b8f9c0-1e2a-3b4c-5d6e-7f8a9b0c1d2e

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.refugee.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.refugee.intro.choice.1", params = {}},
            [2] = {key = "npc.refugee.intro.choice.2", params = {}},
            [3] = {key = "npc.refugee.intro.choice.3", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.refugee.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.refugee.c1.choice.2", params = {}},
                [3] = {key = "npc.refugee.c1.choice.3", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.refugee.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.refugee.c2.choice.1", params = {}},
                [3] = {key = "npc.refugee.c2.choice.3", params = {}}
            }
        }
    end

    return nil
end
