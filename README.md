## Rasch modelini hisoblash (FastAPI + R/ltm)

Ushbu loyiha Python (FastAPI) va R (ltm paketi) yordamida 1PL Rasch modelini (MMLE) hisoblaydi. Backend foydalanuvchi javoblar matritsasini qabul qiladi, vaqtinchalik CSV ga saqlaydi, Rscript orqali `ltm::rasch()` ni chaqiradi va `factor.scores()` yordamida EAP person skorlari va item parametrlarini JSON formatida qaytaradi.

### Talablar
- R (Rscript) o'rnatilgan bo'lishi kerak
- R paketlari: `ltm`, `jsonlite`
- Python 3.10+

### O'rnatish
1) R paketlarini o'rnating (R konsolda):
```r
install.packages(c("ltm", "jsonlite"))
```

2) Python muhitini tayyorlang:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Serverni ishga tushirish
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API foydalanish
- Endpoint: `POST /calculate`
- Kiritma JSON (misol):
```json
{
  "responses": [
    [1, 0, 1, 1, 0],
    [1, 1, 1, 1, 0],
    [0, 0, 1, 0, 0]
  ]
}
```
- Natija JSON (misol tuzilma):
```json
{
  "items": [
    {"item_id": "Item1", "difficulty": 0.123},
    {"item_id": "Item2", "difficulty": -0.456}
  ],
  "persons": [
    {"person_index": 1, "eap": -0.234, "se": 0.567},
    {"person_index": 2, "eap": 0.123, "se": 0.432}
  ],
  "fit": {"logLik": -123.45, "AIC": 300.12, "BIC": 310.33, "n_obs": 3, "n_items": 5}
}
```

### Tezkor sinovlar
- R skriptni to'g'ridan-to'g'ri ishga tushirish:
```bash
Rscript app/r/rasch_calc.R tests/sample_matrix.csv
```

- API orqali sinash (server ishga tushgan bo'lsa):
```bash
curl -s -X POST http://localhost:8000/calculate \
  -H 'Content-Type: application/json' \
  -d @tests/sample_request.json | jq '.'
```

### Tuzilma
- `app/main.py` — FastAPI ilovasi, `/calculate` endpoint
- `app/core/r_runner.py` — Rscript ishga tushirish yordamchisi
- `app/schemas.py` — Pydantic sxemalari
- `app/r/rasch_calc.R` — Rasch (ltm) va EAP hisob-kitobi, JSON chiqish
- `tests/` — namunaviy ma'lumotlar

### Eslatma
- Matritsa 0/1 qiymatlardan (yoki `null` — yetishmayotgan) iborat bo'lishi kerak. Qatorlar shaxslar, ustunlar itemlar.
- `ltm::factor.scores()` noyob javob andozalari bo'yicha natija qaytaradi; skript per-shaxs tartibini saqlash uchun skorlarga mos yozuvlarni kengaytiradi.
- Xatolar yuz bersa, backend 4xx/5xx bilan qisqa xabar qaytaradi.
