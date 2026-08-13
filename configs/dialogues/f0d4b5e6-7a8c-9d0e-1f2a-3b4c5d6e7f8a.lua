-- Wandering Bard (떠돌이 음유시인) 대화 스크립트
-- NPC ID: f0d4b5e6-7a8c-9d0e-1f2a-3b4c5d6e7f8a

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.wandering_bard.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.wandering_bard.intro.choice.1", params = {}},
            [2] = {key = "npc.wandering_bard.intro.choice.2", params = {}},
            [3] = {key = "npc.wandering_bard.intro.choice.3", params = {}},
            [4] = {key = "npc.wandering_bard.intro.choice.4", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.wandering_bard.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.wandering_bard.c1.choice.2", params = {}},
                [3] = {key = "npc.wandering_bard.c1.choice.3", params = {}},
                [4] = {key = "npc.wandering_bard.c1.choice.4", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.wandering_bard.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.wandering_bard.c2.choice.1", params = {}},
                [3] = {key = "npc.wandering_bard.c2.choice.3", params = {}},
                [4] = {key = "npc.wandering_bard.c2.choice.4", params = {}}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    key = "npc.wandering_bard.c3.text.1",
                    params = {}
                }
            },
            choices = {
                [31] = {key = "npc.wandering_bard.c3.choice.31", params = {}},
                [32] = {key = "npc.wandering_bard.c3.choice.32", params = {}},
                [33] = {key = "npc.wandering_bard.c3.choice.33", params = {}},
                [4] = {key = "npc.wandering_bard.c3.choice.4", params = {}}
            }
        }
    end

    if choice_number == 31 then
        return {
            text = {
                {
                    key = "npc.wandering_bard.c31.text.1",
                    params = {}
                }
            },
            choices = {
                [32] = {key = "npc.wandering_bard.c31.choice.32", params = {}},
                [33] = {key = "npc.wandering_bard.c31.choice.33", params = {}},
                [4] = {key = "npc.wandering_bard.c31.choice.4", params = {}}
            }
        }
    end

    if choice_number == 32 then
        return {
            text = {
                {
                    key = "npc.wandering_bard.c32.text.1",
                    params = {}
                }
            },
            choices = {
                [31] = {key = "npc.wandering_bard.c32.choice.31", params = {}},
                [33] = {key = "npc.wandering_bard.c32.choice.33", params = {}},
                [4] = {key = "npc.wandering_bard.c32.choice.4", params = {}}
            }
        }
    end

    if choice_number == 33 then
        return {
            text = {
                {
                    key = "npc.wandering_bard.c33.text.1",
                    params = {}
                }
            },
            choices = {
                [31] = {key = "npc.wandering_bard.c33.choice.31", params = {}},
                [32] = {key = "npc.wandering_bard.c33.choice.32", params = {}},
                [4] = {key = "npc.wandering_bard.c33.choice.4", params = {}}
            }
        }
    end

    return nil
end
