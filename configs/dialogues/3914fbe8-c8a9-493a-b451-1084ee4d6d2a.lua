-- Brother Marcus (예배당 수도승) 대화 스크립트
-- NPC ID: 3914fbe8-c8a9-493a-b451-1084ee4d6d2a

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.brother_marcus.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.brother_marcus.intro.choice.1", params = {}},
            [2] = {key = "npc.brother_marcus.intro.choice.2", params = {}},
            [3] = {key = "npc.brother_marcus.intro.choice.3", params = {}},
            [4] = {key = "npc.brother_marcus.intro.choice.4", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.brother_marcus.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.brother_marcus.c1.choice.2", params = {}},
                [3] = {key = "npc.brother_marcus.c1.choice.3", params = {}},
                [4] = {key = "npc.brother_marcus.c1.choice.4", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.brother_marcus.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.brother_marcus.c2.choice.1", params = {}},
                [3] = {key = "npc.brother_marcus.c2.choice.3", params = {}},
                [4] = {key = "npc.brother_marcus.c2.choice.4", params = {}}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    key = "npc.brother_marcus.c3.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.brother_marcus.c3.choice.1", params = {}},
                [2] = {key = "npc.brother_marcus.c3.choice.2", params = {}},
                [4] = {key = "npc.brother_marcus.c3.choice.4", params = {}}
            }
        }
    end

    return nil
end
