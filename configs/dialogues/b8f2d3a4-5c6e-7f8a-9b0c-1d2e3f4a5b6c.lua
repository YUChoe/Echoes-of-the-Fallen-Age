-- Royal Guard (왕실 경비병) 대화 스크립트
-- NPC ID: b8f2d3a4-5c6e-7f8a-9b0c-1d2e3f4a5b6c

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.royal_guard.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.royal_guard.intro.choice.1", params = {}},
            [2] = {key = "npc.royal_guard.intro.choice.2", params = {}},
            [3] = {key = "npc.royal_guard.intro.choice.3", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.royal_guard.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.royal_guard.c1.choice.2", params = {}},
                [3] = {key = "npc.royal_guard.c1.choice.3", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.royal_guard.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.royal_guard.c2.choice.1", params = {}},
                [3] = {key = "npc.royal_guard.c2.choice.3", params = {}}
            }
        }
    end

    return nil
end
