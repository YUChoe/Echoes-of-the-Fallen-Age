-- Village Militia (자경단원) 대화 스크립트
-- NPC ID: 2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.village_militia.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.village_militia.intro.choice.1", params = {}},
            [2] = {key = "npc.village_militia.intro.choice.2", params = {}},
            [3] = {key = "npc.village_militia.intro.choice.3", params = {}},
            [4] = {key = "npc.village_militia.intro.choice.4", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.village_militia.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.village_militia.c1.choice.2", params = {}},
                [3] = {key = "npc.village_militia.c1.choice.3", params = {}},
                [4] = {key = "npc.village_militia.c1.choice.4", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.village_militia.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.village_militia.c2.choice.1", params = {}},
                [3] = {key = "npc.village_militia.c2.choice.3", params = {}},
                [4] = {key = "npc.village_militia.c2.choice.4", params = {}}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    key = "npc.village_militia.c3.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.village_militia.c3.choice.1", params = {}},
                [2] = {key = "npc.village_militia.c3.choice.2", params = {}},
                [4] = {key = "npc.village_militia.c3.choice.4", params = {}}
            }
        }
    end

    return nil
end
