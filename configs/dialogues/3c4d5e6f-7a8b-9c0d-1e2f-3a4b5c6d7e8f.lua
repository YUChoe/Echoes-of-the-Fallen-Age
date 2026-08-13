-- Junkyard Drifter (쓰레기장 떠돌이) 대화 스크립트
-- NPC ID: 3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.junkyard_drifter.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.junkyard_drifter.intro.choice.1", params = {}},
            [2] = {key = "npc.junkyard_drifter.intro.choice.2", params = {}},
            [3] = {key = "npc.junkyard_drifter.intro.choice.3", params = {}},
            [4] = {key = "npc.junkyard_drifter.intro.choice.4", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.junkyard_drifter.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.junkyard_drifter.c1.choice.2", params = {}},
                [3] = {key = "npc.junkyard_drifter.c1.choice.3", params = {}},
                [4] = {key = "npc.junkyard_drifter.c1.choice.4", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.junkyard_drifter.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.junkyard_drifter.c2.choice.1", params = {}},
                [3] = {key = "npc.junkyard_drifter.c2.choice.3", params = {}},
                [4] = {key = "npc.junkyard_drifter.c2.choice.4", params = {}}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    key = "npc.junkyard_drifter.c3.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.junkyard_drifter.c3.choice.1", params = {}},
                [2] = {key = "npc.junkyard_drifter.c3.choice.2", params = {}},
                [4] = {key = "npc.junkyard_drifter.c3.choice.4", params = {}}
            }
        }
    end

    return nil
end
