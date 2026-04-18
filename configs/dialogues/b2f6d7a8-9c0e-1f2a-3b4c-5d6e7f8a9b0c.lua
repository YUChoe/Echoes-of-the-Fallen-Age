-- Necropolis Monk (네크로폴리스 수도승) 대화 스크립트
-- NPC ID: b2f6d7a8-9c0e-1f2a-3b4c-5d6e7f8a9b0c
-- 침묵하는 수도승: 말 대신 제스처와 서술형 텍스트로만 소통

function get_dialogue(ctx)
    return {
        text = {
            {
                en = "The gaunt monk stands motionless before the entrance to the necropolis. His hollow eyes settle on you for a long moment, then he raises one bony hand and gestures slowly — a sweeping arc from the darkness below towards the faint light above. It is the only guidance he offers: a silent reminder that those who have risen from death must find their way back to the living.",
                ko = "수척한 수도승이 네크로폴리스 입구 앞에 미동도 없이 서 있다. 텅 빈 눈이 한참 동안 당신에게 머문 뒤, 앙상한 손 하나를 들어 천천히 제스처를 취한다 — 아래의 어둠에서 위의 희미한 빛을 향해 크게 호를 그리는 동작이다. 그것이 그가 제공하는 유일한 안내이다: 죽음에서 일어난 자는 산 자들의 세계로 돌아가야 한다는 침묵의 일깨움."
            }
        },
        choices = {}
    }
end

function on_choice(choice_number, ctx)
    return nil
end
