-- Former Merchant (전직 상인) 대화 스크립트
-- NPC ID: f6d0b1e2-3a4c-5d6e-7f8a-9b0c1d2e3f4a

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                key = "npc.former_merchant.intro.text.1",
                params = {player_name = player_name}
            }
        },
        choices = {
            [1] = {key = "npc.former_merchant.intro.choice.1", params = {}},
            [2] = {key = "npc.former_merchant.intro.choice.2", params = {}},
            [3] = {key = "npc.former_merchant.intro.choice.3", params = {}}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    key = "npc.former_merchant.c1.text.1",
                    params = {}
                }
            },
            choices = {
                [2] = {key = "npc.former_merchant.c1.choice.2", params = {}},
                [3] = {key = "npc.former_merchant.c1.choice.3", params = {}}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    key = "npc.former_merchant.c2.text.1",
                    params = {}
                }
            },
            choices = {
                [1] = {key = "npc.former_merchant.c2.choice.1", params = {}},
                [3] = {key = "npc.former_merchant.c2.choice.3", params = {}}
            }
        }
    end

    return nil
end
