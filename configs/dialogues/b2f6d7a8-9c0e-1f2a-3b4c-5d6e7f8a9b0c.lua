-- Necropolis Monk (네크로폴리스 수도승) 대화 스크립트
-- NPC ID: b2f6d7a8-9c0e-1f2a-3b4c-5d6e7f8a9b0c
-- 침묵하는 수도승: 말 대신 제스처와 서술형 텍스트로만 소통

function get_dialogue(ctx)
    return {
        text = {
            {
                key = "npc.necropolis_monk.intro.text.1",
                params = {}
            }
        },
        choices = {}
    }
end

function on_choice(choice_number, ctx)
    return nil
end
