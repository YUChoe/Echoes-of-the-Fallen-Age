-- Priest (사제) 대화 스크립트
-- NPC ID: a1e5c6f7-8b9d-0e1f-2a3b-4c5d6e7f8a9b

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.priest.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.priest.intro.choice.1", params = {}},
            [2] = {key = "npc.priest.intro.choice.2", params = {}},
            [3] = {key = "npc.priest.intro.choice.3", params = {}},
            [4] = {key = "npc.priest.intro.choice.4", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.priest.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.priest.c1.choice.2", params = {}},
                [3] = {key = "npc.priest.c1.choice.3", params = {}},
                [4] = {key = "npc.priest.c1.choice.4", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.priest.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.priest.c2.choice.1", params = {}},
                [3] = {key = "npc.priest.c2.choice.3", params = {}},
                [4] = {key = "npc.priest.c2.choice.4", params = {}}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    key = "npc.priest.c3.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.priest.c3.choice.1", params = {}},
                [2] = {key = "npc.priest.c3.choice.2", params = {}},
                [4] = {key = "npc.priest.c3.choice.4", params = {}}
            }
        }
    end

    return nil
end
