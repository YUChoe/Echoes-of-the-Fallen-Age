-- Gate Warden (성문 관리인) 대화 스크립트
-- NPC ID: c3a7e8b9-0d1f-2a3b-4c5d-6e7f8a9b0c1d

function get_dialogue(ctx)
    local player_name = ctx.player.display_name
    return {
        text = {
            {
                en = "Another one passing through, eh? " .. player_name .. ", mind yourself out there. The western road is not what it used to be.",
                ko = "또 지나가는 사람인가? " .. player_name .. ", 밖에서 조심하게. 서쪽 길은 예전 같지 않다."
            }
        },
        choices = {
            [1] = {en = "What is happening beyond the walls?", ko = "성벽 밖에서 무슨 일이 벌어지고 있나요?"},
            [2] = {en = "Tell me about the relocation order.", ko = "이주 명령에 대해 알려주세요."},
            [3] = {en = "I will be careful.", ko = "조심하겠습니다."}
        }
    }
end

function on_choice(choice_number, ctx)
    if choice_number == 1 then
        return {
            text = {
                {
                    en = "Creatures roam the plains — goblins, wild beasts, things that weren't there a generation ago. The villages beyond the gate have been ordered to empty out. Folk are meant to move further from the walls so we can maintain a clear line of sight. Not everyone is happy about it, as you might imagine.",
                    ko = "괴물들이 평야를 돌아다닌다 — 고블린, 야생 짐승, 한 세대 전에는 없던 것들. 성문 너머 마을들은 비우라는 명령을 받았다. 사람들은 성벽에서 더 멀리 이동해야 한다, 시야를 확보하기 위해서. 모두가 기꺼워하는 건 아니지, 짐작하겠지만."
                }
            },
            choices = {
                [2] = {en = "About the relocation order...", ko = "이주 명령에 대해서..."},
                [3] = {en = "Thank you for the warning.", ko = "경고 감사합니다."}
            }
        }
    end

    if choice_number == 2 then
        return {
            text = {
                {
                    en = "Orders from the castle. Clear the settlements near the walls for defensive purposes. I enforce it because it is my duty, but I know full well what it means for those folk. They lose their homes, their crops, everything. And they blame us — rightly so, perhaps. But if the creatures breach the walls, none of it will matter.",
                    ko = "성에서 내려온 명령이다. 방어를 위해 성벽 근처 정착지를 비우라는 거지. 임무니까 시행하지만, 그 사람들에게 무엇을 의미하는지 잘 안다. 집도, 농작물도, 모든 걸 잃는 거야. 그리고 우리를 탓하지 — 어쩌면 당연하겠지. 하지만 괴물들이 성벽을 뚫으면, 그 어떤 것도 의미가 없어진다."
                }
            },
            choices = {
                [1] = {en = "What creatures are out there?", ko = "밖에 어떤 괴물들이 있나요?"},
                [3] = {en = "A difficult position.", ko = "어려운 처지군요."}
            }
        }
    end

    return nil
end
