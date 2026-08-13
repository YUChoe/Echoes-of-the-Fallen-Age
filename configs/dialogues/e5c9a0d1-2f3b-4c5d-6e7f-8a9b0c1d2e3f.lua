-- Disgruntled Farmer (불만 가득한 농부) 대화 스크립트
-- NPC ID: e5c9a0d1-2f3b-4c5d-6e7f-8a9b0c1d2e3f

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.disgruntled_farmer.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.disgruntled_farmer.intro.choice.1", params = {}},
            [2] = {key = "npc.disgruntled_farmer.intro.choice.2", params = {}},
            [3] = {key = "npc.disgruntled_farmer.intro.choice.3", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.disgruntled_farmer.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.disgruntled_farmer.c1.choice.2", params = {}},
                [3] = {key = "npc.disgruntled_farmer.c1.choice.3", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.disgruntled_farmer.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.disgruntled_farmer.c2.choice.1", params = {}},
                [3] = {key = "npc.disgruntled_farmer.c2.choice.3", params = {}}
            }
        }
    end

    return nil
end
