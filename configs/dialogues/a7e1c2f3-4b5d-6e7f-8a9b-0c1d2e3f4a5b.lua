-- Royal Adviser (왕의 조언자) 대화 스크립트
-- NPC ID: a7e1c2f3-4b5d-6e7f-8a9b-0c1d2e3f4a5b

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.royal_adviser.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.royal_adviser.intro.choice.1", params = {}},
            [2] = {key = "npc.royal_adviser.intro.choice.2", params = {}},
            [3] = {key = "npc.royal_adviser.intro.choice.3", params = {}},
            [4] = {key = "npc.royal_adviser.intro.choice.4", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.royal_adviser.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.royal_adviser.c1.choice.2", params = {}},
                [3] = {key = "npc.royal_adviser.c1.choice.3", params = {}},
                [4] = {key = "npc.royal_adviser.c1.choice.4", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.royal_adviser.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.royal_adviser.c2.choice.1", params = {}},
                [3] = {key = "npc.royal_adviser.c2.choice.3", params = {}},
                [4] = {key = "npc.royal_adviser.c2.choice.4", params = {}}
            }
        }
    end

    if choice_number == 3 then
        return {
            text = {
                {
                    key = "npc.royal_adviser.c3.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.royal_adviser.c3.choice.1", params = {}},
                [2] = {key = "npc.royal_adviser.c3.choice.2", params = {}},
                [4] = {key = "npc.royal_adviser.c3.choice.4", params = {}}
            }
        }
    end

    return nil
end
