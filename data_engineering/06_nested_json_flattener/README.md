課題6：複雑なネストJSONの「フラット化（Flatten）」
生のJSONデータは階層が深く（ネストして）おり、リストの中に辞書があり、その中にまたリストがある…という状態です。これをデータウェアハウス（SQL）で扱いやすい「平坦な（表形式の）辞書」に変換するアルゴリズムです。

テーマ: 再帰関数（Recursive Function）を使ったJSONのパース。

学ぶべきこと: 実務で頻出する「半構造化データのテーブル化」。再帰処理を用いた美しいコードの書き方。

### before
```json

{
  "user_id": "usr_7749",
  "status": "active",
 "info": {
    "name": "Hiroshi Tanaka",
    " contact": {
      "email": "hiro@example.com",
      "sns": { "github": "hiro_dev", "slack_id": "U123" }
    }
  },
  "rag_history": [
    { "session_id": "sess_001", "meta": { "tokens": 45, "model": "gpt-4" } },
    { "session_id": "sess_002", "meta": { "tokens": 62, "model": "claude-3" } }
  ],
  "preferences": {
    "theme": "dark",
    "settings": { "notifications": { "email": true, "push": { "alert": true } } }
  }
}


```


### after

```python

{
    "user_id": "usr_7749",
    "status": "active",
    "info.name": "Hiroshi Tanaka",
    "info.contact.email": "hiro@example.com",
    "info.contact.sns.github": "hiro_dev",
    "info.contact.sns.slack_id": "U123",
    "rag_history.0.session_id": "sess_001",
    "rag_history.0.meta.tokens": 45,
    "rag_history.0.meta.model": "gpt-4",
    "rag_history.1.session_id": "sess_002",
    "rag_history.1.meta.tokens": 62,
    "rag_history.1.meta.model": "claude-3",
    "preferences.theme": "dark",
    "preferences.settings.notifications.email": True,
    "preferences.settings.notifications.push.alert": True
}


```

