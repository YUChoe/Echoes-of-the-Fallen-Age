# 규칙
- `sqlite3` 가 설치 되어 있지 않으니 python 을 이용할 것
- 예제:
```
source mud_engine_env/Scripts/activate && python -c "
import sqlite3
conn = sqlite3.connect('data/mud_engine.db')
cursor = conn.cursor()
cursor.execute('SELECT username, is_admin FROM players WHERE username=?', ('pp',))
result = cursor.fetchone()
print(f'Player pp: {result}')
conn.close()
"
```
