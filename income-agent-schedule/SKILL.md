---
name: income-agent-schedule
description: >
  Token-efficient scheduling rules for Income Agent. Use BEFORE any earn-money
  session to decide whether to run hunt-lite.py (free), Grok propose/deliver
  (paid tokens), or skip. Triggers: расписание, автономно, токены, schedule,
  hunt-lite, когда вызывать Grok, income-agent-schedule, /income-agent-schedule.
---

# Income Agent Schedule — экономия токенов

Работает вместе с `income-agent` и `scripts/hunt-lite.py`.

## Золотое правило

| Действие | Инструмент | Токены |
|----------|------------|--------|
| Поиск лидов | `hunt-lite.py` | **0** |
| Дайджест в Telegram | n8n + `hunt-lite.py --telegram` | **0** |
| Отклики топ-3 | Grok `/income-agent propose` | **да** |
| Выполнение заказа | Grok `/income-agent deliver` | **да** |
| Подпись счёта | Оператор | **0** |

**Grok не делает hunt.** Только читает `references/leads-candidates.json`.

## Расписание (МСК)

| Когда | Что | Кто |
|-------|-----|-----|
| Пн–Пт 09:00 | `hunt-lite.py --min-score 8 --telegram` | n8n (cron) |
| Пн–Пт 09:15 | Оператор читает Telegram | вы |
| Если есть лиды ≥8 | `/income-agent propose 1,2,3` | Grok **1 запрос** |
| После «да» | Вставить отклик на FL.ru | вы, 2 мин |
| Заказ принят | `/income-agent deliver` | Grok |
| Пт 18:00 | `/income-agent report` | Grok **1 запрос** |

**Бюджет:** 2–5 сессий Grok в неделю, не 24/7.

## Когда вызывать Grok

Вызывать **только если**:
1. В `leads-candidates.json` есть лид с `score ≥ 8`, или
2. Оператор написал номер лида / «propose», или
3. Заказ в статусе `won` / `in_progress` → deliver, или
4. Пятница → report.

**Не вызывать Grok если:**
- hunt-lite вернул 0 лидов ≥ порога;
- оператор не ответил «да» на отклик;
- задача — только «проверь FL.ru» (→ hunt-lite).

## Команды hunt-lite (без LLM)

```bash
# Ручной запуск
python3 ~/.grok/skills/income-agent/scripts/hunt-lite.py --min-score 8

# С Telegram (нужны env в .env)
~/.grok/skills/income-agent/scripts/run-hunt-digest.sh

# JSON для Grok
python3 ~/.grok/skills/income-agent/scripts/hunt-lite.py --min-score 8 --json
```

Результат: `~/.grok/skills/income-agent/references/leads-candidates.json`

## Сессия Grok propose (шаблон)

1. Прочитать `leads-candidates.json` (не WebSearch).
2. Взять топ-3 по score.
3. Шаблоны из `income-agent/references/templates.md`.
4. Спросить: «Отправляем? (да / правки / пропустить)».

Максимум **3 отклика** за сессию.

## n8n

Workflow: `~/n8n-azimut/workflows/income-agent-morning-digest.json`

Импорт:
```bash
cd ~/n8n-azimut && ./import-income-digest.sh
```

Переменные (файл `~/.grok/skills/income-agent/.env`):
- `INCOME_AGENT_TG_BOT_TOKEN` — токен @BotFather
- `INCOME_AGENT_TG_CHAT_ID` — ваш chat_id (@userinfobot)

## После отправки отклика

```bash
python3 ~/.grok/skills/income-agent/scripts/hunt-lite.py --mark-seen --min-score 8
```
(добавляет ID в `leads-seen.json`, чтобы не дублировать дайджест)

## Лимиты (жёстко)

- hunt: 1 раз в день автоматически + по запросу
- propose: ≤3 лида / сессия
- deliver: 1 заказ / сессия
- report: 1 раз / неделя