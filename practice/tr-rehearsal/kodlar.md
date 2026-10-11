# close_call kodları

Her arama tam olarak bir `close_call` ile kapanır. `outcome` ve gerekiyorsa `reason`:

| outcome | reason | Ne zaman |
|---|---|---|
| `promise` | yok | en az bir söz kaydedildi |
| `paid` | yok | kural 39 |
| `transferred` | `restructuring`, `human`, `support` | kural 41, 42, 32 |
| `no_promise` | `refused`, `hardship`, `dispute`, `service_error` | kural 31 ve 45, 32, 40, 37 |
| `not_verified` | `failed`, `declined` | kural 14, 15 |
| `not_reached` | `callback`, `no_callback`, `wrong_number`, `deceased`, `unclear` | kural 6, 7, 8, 9, 3 |

Kaydedilmiş bir sözden sonra bir aktarma olursa o aktarmanın sebebiyle `transferred` olarak kapatın.
