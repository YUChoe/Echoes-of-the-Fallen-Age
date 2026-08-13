-- Knight Recruiter (기사단 모병관) 대화 스크립트
-- NPC ID: d8b2f3c4-5e6a-7b8c-9d0e-1f2a3b4c5d6e

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.knight_recruiter.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.knight_recruiter.intro.choice.1", params = {}},
            [2] = {key = "npc.knight_recruiter.intro.choice.2", params = {}},
            [3] = {key = "npc.knight_recruiter.intro.choice.3", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.knight_recruiter.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.knight_recruiter.c1.choice.2", params = {}},
                [3] = {key = "npc.knight_recruiter.c1.choice.3", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.knight_recruiter.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.knight_recruiter.c2.choice.1", params = {}},
                [3] = {key = "npc.knight_recruiter.c2.choice.3", params = {}}
            }
        }
    end

    return nil
end
