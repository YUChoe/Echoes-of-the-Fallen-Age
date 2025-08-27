# SQLite 사용 규칙

## 기본 규칙
- `sqlite3` 가 설치되어 있지 않으니 python을 이용할 것

## 사용 예제
```python
import sqlite3
conn = sqlite3.connect('data/mud_engine.db')
cursor = conn.cursor()
cursor.execute('SELECT username, is_admin FROM players WHERE username=?', ('pp',))
result = cursor.fetchone()
print(f'Player pp: {result}')
conn.close()
```
