-- Knight Lieutenant (기사단 부관) 대화 스크립트
-- NPC ID: c7a1e2b3-4d5f-6a7b-8c9d-0e1f2a3b4c5d

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.knight_lieutenant.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.knight_lieutenant.intro.choice.1", params = {}},
            [2] = {key = "npc.knight_lieutenant.intro.choice.2", params = {}},
            [3] = {key = "npc.knight_lieutenant.intro.choice.3", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.knight_lieutenant.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.knight_lieutenant.c1.choice.2", params = {}},
                [3] = {key = "npc.knight_lieutenant.c1.choice.3", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.knight_lieutenant.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.knight_lieutenant.c2.choice.1", params = {}},
                [3] = {key = "npc.knight_lieutenant.c2.choice.3", params = {}}
            }
        }
    end

    return nil
end
