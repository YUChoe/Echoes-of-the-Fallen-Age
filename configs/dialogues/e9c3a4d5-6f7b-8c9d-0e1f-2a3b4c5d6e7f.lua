-- Drunken Refugee (술에 취한 난민) 대화 스크립트
-- NPC ID: e9c3a4d5-6f7b-8c9d-0e1f-2a3b4c5d6e7f

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.drunken_refugee.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.drunken_refugee.intro.choice.1", params = {}},
            [2] = {key = "npc.drunken_refugee.intro.choice.2", params = {}},
            [3] = {key = "npc.drunken_refugee.intro.choice.3", params = {}},
            [4] = {key = "npc.drunken_refugee.intro.choice.4", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.drunken_refugee.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.drunken_refugee.c1.choice.2", params = {}},
                [3] = {key = "npc.drunken_refugee.c1.choice.3", params = {}},
                [4] = {key = "npc.drunken_refugee.c1.choice.4", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.drunken_refugee.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.drunken_refugee.c2.choice.1", params = {}},
                [3] = {key = "npc.drunken_refugee.c2.choice.3", params = {}},
                [4] = {key = "npc.drunken_refugee.c2.choice.4", params = {}}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    key = "npc.drunken_refugee.c3.text.1",
                    params = {}
                }
            },
            choices = {
                [31] = {key = "npc.drunken_refugee.c3.choice.31", params = {}},
                [32] = {key = "npc.drunken_refugee.c3.choice.32", params = {}},
                [4] = {key = "npc.drunken_refugee.c3.choice.4", params = {}}
            }
        }
    end

    if choice_number == 31 then
        return {
            text = {
                {
                    key = "npc.drunken_refugee.c31.text.1",
                    params = {}
                }
            },
            choices = {
                [32] = {key = "npc.drunken_refugee.c31.choice.32", params = {}},
                [1] = {key = "npc.drunken_refugee.c31.choice.1", params = {}},
                [4] = {key = "npc.drunken_refugee.c31.choice.4", params = {}}
            }
        }
    end

    if choice_number == 32 then
        return {
            text = {
                {
                    key = "npc.drunken_refugee.c32.text.1",
                    params = {}
                }
            },
            choices = {
                [31] = {key = "npc.drunken_refugee.c32.choice.31", params = {}},
                [1] = {key = "npc.drunken_refugee.c32.choice.1", params = {}},
                [4] = {key = "npc.drunken_refugee.c32.choice.4", params = {}}
            }
        }
    end

    return nil
end
